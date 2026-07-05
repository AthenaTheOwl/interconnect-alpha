"""Brier-score backtest of the Kaplan-Meier probability-of-COD forecast.

The forecast under test is the per-group (per-fuel) KM probability that a project
reaches commercial operation within ``horizon`` days of entering the queue,
``p_hat = 1 - S_group(horizon)``. It is scored against the naive baseline every
survival model has to beat: the overall base rate of COD-by-horizon, the same
number for every project.

Honest labelling: this is an **in-sample** backtest. The same cohort is used to
fit the KM curves and to score them, so the reported edge measures whether
conditioning on fuel type improves the forecast over a single base-rate guess --
not out-of-sample generalisation. The fixture cohort is too small to hold out a
credible earlier fold; when a real LBNL/PJM cohort is ingested this module can be
run on a held-out split and relabelled.

Pure standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .kaplan_meier import kaplan_meier


@dataclass(frozen=True)
class Subject:
    """One cohort member reduced to what the backtest needs."""

    duration: float  # days from queue entry to COD or to censoring
    event: int       # 1 = reached COD, 0 = right-censored
    group: str       # stratum key (fuel)


@dataclass(frozen=True)
class BrierResult:
    horizon_days: int
    brier_score: float
    naive_brier_score: float
    base_rate: float
    n_scored: int
    sample: str  # "in-sample" or "held-out"


def brier_score(preds: Sequence[float], outcomes: Sequence[int]) -> float:
    """Mean squared error of probabilistic forecasts against 0/1 outcomes."""
    if len(preds) != len(outcomes):
        raise ValueError("preds and outcomes must have equal length")
    if not preds:
        raise ValueError("cannot score an empty forecast set")
    return sum((float(p) - float(o)) ** 2 for p, o in zip(preds, outcomes)) / len(preds)


def base_rate(outcomes: Sequence[int]) -> float:
    """Overall event rate -- the naive constant forecast."""
    if not outcomes:
        raise ValueError("cannot take the base rate of an empty set")
    return sum(float(o) for o in outcomes) / len(outcomes)


def _outcome_observed(subject: Subject, horizon: float) -> bool:
    """Is the COD-by-horizon outcome determined for this subject?

    Known if the project reached COD (we then know whether that happened by the
    horizon) or if it was followed at least ``horizon`` days without the event. A
    project censored *before* the horizon has an undetermined outcome and is
    dropped from that horizon's score.
    """
    if subject.event == 1:
        return True
    return subject.duration >= horizon


def _observed_outcome(subject: Subject, horizon: float) -> int:
    return 1 if (subject.event == 1 and subject.duration <= horizon) else 0


def group_survival_at(subjects: Sequence[Subject], horizon: float) -> dict[str, float]:
    """Fit a per-group KM curve and return S_group(horizon) for each group."""
    groups = sorted({s.group for s in subjects})
    out: dict[str, float] = {}
    for g in groups:
        durations = [s.duration for s in subjects if s.group == g]
        events = [s.event for s in subjects if s.group == g]
        curve = kaplan_meier(durations, events)
        out[g] = curve.survival_at(horizon)
    return out


def backtest(
    subjects: Sequence[Subject],
    horizon: int,
    *,
    sample: str = "in-sample",
) -> BrierResult:
    """Brier score of the per-group KM COD forecast vs the naive base rate.

    Only subjects whose COD-by-horizon outcome is observed are scored. The model
    forecast for each is ``1 - S_group(horizon)`` from the per-fuel KM fit; the
    naive forecast is the base rate of the observed outcomes.
    """
    scored = [s for s in subjects if _outcome_observed(s, horizon)]
    if not scored:
        raise ValueError(f"no subjects have an observed outcome at horizon {horizon}")

    group_survival = group_survival_at(subjects, horizon)
    outcomes = [_observed_outcome(s, horizon) for s in scored]
    model_preds = [1.0 - group_survival[s.group] for s in scored]
    rate = base_rate(outcomes)
    naive_preds = [rate] * len(scored)

    return BrierResult(
        horizon_days=int(horizon),
        brier_score=brier_score(model_preds, outcomes),
        naive_brier_score=brier_score(naive_preds, outcomes),
        base_rate=rate,
        n_scored=len(scored),
        sample=sample,
    )
