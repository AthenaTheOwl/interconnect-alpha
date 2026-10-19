"""Right-censored Kaplan-Meier survival estimator.

Pure standard library (``math`` only) so the survival math has no third-party
dependency and is trivial to audit. The event of interest is a project reaching
commercial operation (COD); a project still in the queue at the report date is
right-censored.

Definitions used throughout:

- ``durations[i]``  -- days from queue entry to the event or to censoring.
- ``events[i]``     -- 1 if the project reached COD (event observed), else 0
  (right-censored: still active, or withdrawn without energizing).

The estimator computes the product-limit survival function ``S(t)`` together with
the Greenwood variance and a linear 95% confidence band ``S +/- z*sqrt(Var)``
clipped to ``[0, 1]``. ``survival_prob`` in the shipped artifact is ``S(t)`` -- the
probability a project has *not* reached COD by horizon ``t`` -- so the probability
of reaching COD by ``t`` is its complement ``1 - S(t)``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

Z_95 = 1.959963984540054  # two-sided 95% normal quantile


@dataclass(frozen=True)
class KMPoint:
    """One step of the product-limit estimator, at a distinct event time."""

    time: float
    n_risk: int
    n_event: int
    survival: float
    greenwood_sum: float  # cumulative sum d/(n*(n-d)) up to and including this time
    variance: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class KMCurve:
    """A fitted Kaplan-Meier curve plus the sample it was fit on."""

    points: tuple[KMPoint, ...]
    n_total: int
    n_events: int
    z: float

    # -- survival function (right-continuous step function) --------------------

    def survival_at(self, t: float) -> float:
        """S(t): survival after all event times <= t. S(t)=1 before the first."""
        s = 1.0
        for p in self.points:
            if p.time <= t:
                s = p.survival
            else:
                break
        return s

    def greenwood_at(self, t: float) -> float:
        """Cumulative Greenwood sum up to and including event times <= t."""
        g = 0.0
        for p in self.points:
            if p.time <= t:
                g = p.greenwood_sum
            else:
                break
        return g

    def ci_at(self, t: float) -> tuple[float, float]:
        """Linear Greenwood 95% band for S(t)."""
        s = self.survival_at(t)
        g = self.greenwood_at(t)
        return _linear_band(s, g, self.z)

    def conditional_survival(self, age: float, horizon: float) -> tuple[float, float, float]:
        """Conditional survival S(age+horizon)/S(age) with a Greenwood band.

        The probability a project already in the queue ``age`` days without
        energizing remains un-energized for ``horizon`` more days. Variance uses
        the Greenwood increments over the interval ``(age, age+horizon]`` only,
        which is the standard left-truncated conditional-KM result. Returned as
        ``(survival, ci_low, ci_high)``.
        """
        s_age = self.survival_at(age)
        if s_age <= 0.0:
            return (0.0, 0.0, 0.0)
        s_cond = self.survival_at(age + horizon) / s_age
        g_cond = max(0.0, self.greenwood_at(age + horizon) - self.greenwood_at(age))
        lo, hi = _linear_band(s_cond, g_cond, self.z)
        return (s_cond, lo, hi)


def _linear_band(survival: float, greenwood_sum: float, z: float) -> tuple[float, float]:
    variance = survival * survival * greenwood_sum
    half = z * math.sqrt(variance) if variance > 0.0 else 0.0
    lo = max(0.0, survival - half)
    hi = min(1.0, survival + half)
    return (lo, hi)


def kaplan_meier(
    durations: Sequence[float],
    events: Sequence[int],
    *,
    z: float = Z_95,
) -> KMCurve:
    """Fit a right-censored Kaplan-Meier curve.

    ``durations`` and ``events`` are parallel sequences. Ties are handled: at a
    distinct event time the number at risk counts every subject whose duration is
    ``>= t`` (subjects censored exactly at ``t`` are treated as at risk at ``t``),
    and the number of events counts subjects with ``duration == t`` and event 1.
    """
    if len(durations) != len(events):
        raise ValueError("durations and events must have equal length")
    if not math.isfinite(z) or z <= 0:
        raise ValueError("z must be finite and positive")
    try:
        numeric_durations = [float(d) for d in durations]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("durations must be finite and non-negative") from exc
    if any(not math.isfinite(d) or d < 0 for d in numeric_durations):
        raise ValueError("durations must be finite and non-negative")
    if any(e not in (0, 1) for e in events):
        raise ValueError("events must contain only 0 or 1")
    n_total = len(durations)
    if n_total == 0:
        return KMCurve(points=(), n_total=0, n_events=0, z=z)

    pairs = sorted(zip(numeric_durations, (int(e) for e in events)))
    event_times = sorted({d for d, e in pairs if e == 1})

    points: list[KMPoint] = []
    survival = 1.0
    greenwood = 0.0
    for t in event_times:
        n_risk = sum(1 for d, _ in pairs if d >= t)
        n_event = sum(1 for d, e in pairs if e == 1 and d == t)
        survival *= (n_risk - n_event) / n_risk
        denom = n_risk * (n_risk - n_event)
        if denom > 0:
            greenwood += n_event / denom
        # when n_risk == n_event the survival hits 0 and the Greenwood term is
        # left undefined by convention; we skip it so variance stays finite.
        variance = survival * survival * greenwood
        lo, hi = _linear_band(survival, greenwood, z)
        points.append(
            KMPoint(
                time=t,
                n_risk=n_risk,
                n_event=n_event,
                survival=survival,
                greenwood_sum=greenwood,
                variance=variance,
                ci_low=lo,
                ci_high=hi,
            )
        )

    n_events = sum(1 for _, e in pairs if e == 1)
    return KMCurve(points=tuple(points), n_total=n_total, n_events=n_events, z=z)
