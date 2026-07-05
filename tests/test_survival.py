"""Tests for the real Kaplan-Meier / Brier survival machinery.

Covers: a hand-computed KM curve (exact survival + Greenwood band), Brier sanity
values, and proof that the committed artifacts are *computed* from the cohort
(they match a fresh recomputation and they move when the input moves) rather than
hand-typed literals.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

from interconnect_alpha.brier_backtest import Subject, backtest, base_rate, brier_score
from interconnect_alpha.kaplan_meier import kaplan_meier

ROOT = Path(__file__).resolve().parent.parent


def _load_build_artifacts():
    spec = importlib.util.spec_from_file_location(
        "build_artifacts", ROOT / "scripts" / "build_artifacts.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_artifacts"] = module
    spec.loader.exec_module(module)
    return module


ba = _load_build_artifacts()


# ---------------------------------------------------------------------------
# Kaplan-Meier: hand-computed reference
# ---------------------------------------------------------------------------
# Sample (duration, event): (2,1) (3,1) (4,0) (5,1) (6,0).
# t=2: n=5 d=1 -> S=4/5=0.80
# t=3: n=4 d=1 -> S=0.80*3/4=0.60
# t=5: n=2 d=1 -> S=0.60*1/2=0.30
# Greenwood sum at t=5: 1/(5*4)+1/(4*3)+1/(2*1) = 0.05+0.08333+0.5 = 0.63333
# Var(S(5)) = 0.30^2 * 0.63333 = 0.057; linear 95% band 0.30 +/- 1.96*sqrt(0.057)
# = 0.30 +/- 0.468 -> [0 (clipped), 0.768].


def test_km_survival_matches_hand_computation():
    curve = kaplan_meier([2, 3, 4, 5, 6], [1, 1, 0, 1, 0])
    assert [p.time for p in curve.points] == [2.0, 3.0, 5.0]
    assert [round(p.survival, 6) for p in curve.points] == [0.8, 0.6, 0.3]
    assert curve.points[-1].greenwood_sum == pytest.approx(0.633333, abs=1e-5)
    # step function: flat between event times, 1.0 before the first event.
    assert curve.survival_at(0) == 1.0
    assert curve.survival_at(1) == 1.0
    assert curve.survival_at(4) == pytest.approx(0.6)
    assert curve.survival_at(1000) == pytest.approx(0.3)


def test_km_greenwood_confidence_band():
    curve = kaplan_meier([2, 3, 4, 5, 6], [1, 1, 0, 1, 0])
    lo, hi = curve.ci_at(5)
    assert lo == 0.0  # 0.30 - 0.468 clipped to 0
    assert hi == pytest.approx(0.768, abs=1e-3)


def test_km_conditional_survival_is_a_ratio():
    curve = kaplan_meier([2, 3, 4, 5, 6], [1, 1, 0, 1, 0])
    # Conditional on surviving to age 2, probability of surviving 3 more days:
    # S(5)/S(2) = 0.30/0.80 = 0.375.
    surv, lo, hi = curve.conditional_survival(2, 3)
    assert surv == pytest.approx(0.375)
    assert 0.0 <= lo <= surv <= hi <= 1.0


def test_km_all_events_drives_survival_to_zero_without_error():
    curve = kaplan_meier([1, 2, 3], [1, 1, 1])
    assert curve.survival_at(3) == 0.0
    assert curve.ci_at(3) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Brier score sanity
# ---------------------------------------------------------------------------


def test_brier_perfect_forecast_is_zero():
    assert brier_score([1.0, 0.0, 1.0, 0.0], [1, 0, 1, 0]) == 0.0


def test_brier_base_rate_forecast_known_value():
    # Constant 0.5 forecast against a balanced 0/1 set -> mean squared error 0.25.
    assert base_rate([1, 1, 0, 0]) == 0.5
    assert brier_score([0.5, 0.5, 0.5, 0.5], [1, 1, 0, 0]) == 0.25


def test_backtest_beats_naive_when_groups_are_informative():
    # 'fast' always energizes by day 150; 'slow' never energizes within the window.
    subjects = [Subject(150.0, 1, "fast") for _ in range(5)]
    subjects += [Subject(400.0, 0, "slow") for _ in range(5)]
    result = backtest(subjects, horizon=300)
    # Per-group KM predicts fast=1.0, slow=0.0 -> perfect; naive base rate 0.5.
    assert result.brier_score == pytest.approx(0.0)
    assert result.naive_brier_score == pytest.approx(0.25)
    assert result.brier_score < result.naive_brier_score
    assert result.sample == "in-sample"


def test_backtest_excludes_undetermined_outcomes():
    # A subject censored before the horizon has an unknown outcome -> not scored.
    subjects = [
        Subject(150.0, 1, "g"),   # event by horizon -> scored, obs=1
        Subject(500.0, 0, "g"),   # followed past horizon -> scored, obs=0
        Subject(50.0, 0, "g"),    # censored before horizon -> excluded
    ]
    result = backtest(subjects, horizon=300)
    assert result.n_scored == 2


# ---------------------------------------------------------------------------
# The committed artifacts are computed, not literals
# ---------------------------------------------------------------------------


def _survival_row(rows: pd.DataFrame, pid: str, horizon: int) -> float:
    m = rows[(rows["project_id"] == pid) & (rows["days_to_event"] == horizon)]
    return float(m["survival_prob"].iloc[0])


def test_committed_survival_matches_fresh_recomputation():
    # Recompute the survival rows straight from the committed cohort parquet and
    # assert they equal what is checked in. If anyone hand-edits the survival
    # numbers, this fails.
    cohort = pd.read_parquet(ROOT / "data/pjm_queue_cohort_2018_2023.parquet")
    subjects = ba.cohort_to_subjects(cohort.to_dict("records"))
    recomputed = ba.build_survival_rows(subjects)

    committed = pd.read_parquet(ROOT / "data/survival_distributions.parquet")
    merged = committed.merge(
        recomputed, on=["project_id", "days_to_event"], suffixes=("_c", "_r")
    )
    assert len(merged) == len(committed) == 8
    for col in ("survival_prob", "confidence_low", "confidence_high"):
        for c, r in zip(merged[f"{col}_c"], merged[f"{col}_r"]):
            assert c == pytest.approx(r, abs=1e-4)


def test_survival_rows_move_when_the_cohort_moves():
    # Same fuels present in both runs, but 'gas' gets extra early events in the
    # second run -> its survival at 730 must fall while 'wind' is untouched.
    base = [
        Subject(200.0, 1, "gas"), Subject(900.0, 0, "gas"),
        Subject(600.0, 1, "solar"), Subject(900.0, 0, "solar"),
        Subject(900.0, 1, "battery"), Subject(900.0, 0, "battery"),
        Subject(1500.0, 1, "wind"), Subject(1200.0, 0, "wind"),
    ]
    moved = base + [Subject(300.0, 1, "gas") for _ in range(6)]

    rows_base = ba.build_survival_rows(base)
    rows_moved = ba.build_survival_rows(moved)

    gas_base = _survival_row(rows_base, "PJM-ALPHA-003", 730)
    gas_moved = _survival_row(rows_moved, "PJM-ALPHA-003", 730)
    assert gas_moved < gas_base  # more early gas COD -> lower survival

    wind_base = _survival_row(rows_base, "PJM-ALPHA-004", 730)
    wind_moved = _survival_row(rows_moved, "PJM-ALPHA-004", 730)
    assert wind_base == wind_moved  # untouched fuel is unchanged


def test_committed_survival_is_not_the_old_literals():
    # The retired hand-typed table had solar(730)=0.41 and battery(730)=0.52.
    committed = pd.read_parquet(ROOT / "data/survival_distributions.parquet")
    assert _survival_row(committed, "PJM-ALPHA-001", 730) != 0.41
    assert _survival_row(committed, "PJM-ALPHA-002", 730) != 0.52
    # Ranking the product depends on: gas clears faster than wind.
    gas = _survival_row(committed, "PJM-ALPHA-003", 730)
    wind = _survival_row(committed, "PJM-ALPHA-004", 730)
    assert (1 - gas) > (1 - wind)
