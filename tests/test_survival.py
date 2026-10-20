"""Tests for the real Kaplan-Meier / Brier survival machinery.

Covers: a hand-computed KM curve (exact survival + Greenwood band), Brier sanity
values, and proof that the committed artifacts are *computed* from the cohort
(they match a fresh recomputation and they move when the input moves) rather than
hand-typed literals.
"""

from __future__ import annotations

import importlib.util
import math
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


def test_km_conditional_survival_past_last_event_is_unsupported():
    curve = kaplan_meier([2, 3, 4, 5, 6], [1, 1, 0, 1, 0])
    assert curve.last_event_time == 5.0
    assert curve.supports_conditional(4.9)
    # At or past the last event (t=5) the curve is flat for lack of events: a
    # project that old gets no number, not S(age+h)/S(age) = 1.
    assert not curve.supports_conditional(5)
    assert not curve.supports_conditional(6)
    assert all(math.isnan(v) for v in curve.conditional_survival(5, 3))
    assert all(math.isnan(v) for v in curve.conditional_survival(6, 1))
    # Once every subject has had the event, S(age)=0: unsupported, not 0/0.
    all_events = kaplan_meier([1, 2, 3], [1, 1, 1])
    assert all(math.isnan(v) for v in all_events.conditional_survival(3, 1))
    # No events at all: nothing to condition on.
    assert not kaplan_meier([4, 5], [0, 0]).supports_conditional(0)


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
# Cohort: withdrawal keeps its own date
# ---------------------------------------------------------------------------


def test_generator_keeps_announced_cod_on_withdrawn_rows():
    rows = ba.generate_cohort()
    withdrawn = [r for r in rows if r["status"] == "withdrawn"]
    assert withdrawn
    for r in withdrawn:
        # the exit date sits in its own column, after queue entry and no later
        # than the announced COD the developer filed
        assert r["queue_date"] < r["withdrawal_date"] <= r["announced_cod"]
    # announced_cod is not overwritten with the exit date
    assert any(r["withdrawal_date"] < r["announced_cod"] for r in withdrawn)
    assert all(r["withdrawal_date"] == "" for r in rows if r["status"] != "withdrawn")


def test_withdrawn_subject_is_censored_at_its_withdrawal_date():
    row = {
        "project_id": "PJM-WI-900", "zone": "RTO", "fuel": "wind",
        "queue_date": "2020-01-01", "announced_cod": "2024-01-01", "actual_cod": "",
        "withdrawal_date": "2021-01-01", "status": "withdrawn", "capacity_mw": 50.0,
    }
    [subject] = ba.cohort_to_subjects([row])
    assert subject.event == 0
    assert subject.duration == 366.0  # 2020 is a leap year; announced_cod plays no part


def test_committed_cohort_has_withdrawal_dates():
    cohort = pd.read_parquet(ROOT / "data/pjm_queue_cohort_2018_2023.parquet")
    withdrawn = cohort[cohort["status"] == "withdrawn"]
    assert len(withdrawn) > 0
    assert (withdrawn["withdrawal_date"] != "").all()
    assert (withdrawn["withdrawal_date"] != withdrawn["announced_cod"]).any()
    assert (cohort.loc[cohort["status"] != "withdrawn", "withdrawal_date"] == "").all()


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
    assert list(merged["basis_c"]) == list(merged["basis_r"])
    assert list(merged["queue_age_days_c"]) == list(merged["queue_age_days_r"])
    for col in ("survival_prob", "confidence_low", "confidence_high"):
        for c, r in zip(merged[f"{col}_c"], merged[f"{col}_r"]):
            assert c == pytest.approx(r, abs=1e-4, nan_ok=True)


def test_survival_rows_move_when_the_cohort_moves():
    # Same fuels present in both runs, but 'gas' gets extra early events in the
    # second run -> its survival at 730 must fall while 'wind' is untouched.
    base = [
        Subject(200.0, 1, "gas"), Subject(900.0, 0, "gas"),
        Subject(600.0, 1, "solar"), Subject(900.0, 0, "solar"),
        Subject(900.0, 1, "battery"), Subject(900.0, 0, "battery"),
        Subject(500.0, 1, "wind"), Subject(1200.0, 0, "wind"),
    ]
    moved = base + [Subject(300.0, 1, "gas") for _ in range(6)]
    # Score every display project as active and 31 days into the queue at the
    # as-of date, so the gas and wind rows read a 730-day window holding a COD.
    projects = [
        dict(p, queue_date="2026-07-01", actual_cod="", status="active")
        for p in ba.DISPLAY_PROJECTS
    ]

    rows_base = ba.build_survival_rows(base, projects)
    rows_moved = ba.build_survival_rows(moved, projects)

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
    # Ranking the product depends on: the gas curve clears faster than wind.
    cohort = pd.read_parquet(ROOT / "data/pjm_queue_cohort_2018_2023.parquet")
    curves = ba.fit_fuel_curves(ba.cohort_to_subjects(cohort.to_dict("records")))
    assert curves["gas"].survival_at(730) < curves["wind"].survival_at(730)


def test_online_project_counts_as_built():
    # PJM-ALPHA-003 reached COD on 2026-05-30, before the 2026-08-01 as-of date.
    # It is built: survival 0 with no band at every horizon, whatever the gas
    # curve says.
    subjects = [Subject(200.0, 1, "gas"), Subject(5000.0, 0, "gas")]
    subjects += [Subject(900.0, 1, f) for f in ("solar", "battery", "wind")]
    rows = ba.build_survival_rows(subjects)
    online = rows[rows["project_id"] == "PJM-ALPHA-003"]
    assert len(online) == len(ba.DISPLAY_HORIZONS)
    assert set(online["basis"]) == {"observed_cod"}
    assert (online["survival_prob"] == 0.0).all()
    assert (online["confidence_low"] == 0.0).all()
    assert (online["confidence_high"] == 0.0).all()


def test_active_project_reads_the_curve_conditional_on_time_waited():
    # Events at 100..1000 days; a project 300 days into the queue at the as-of
    # date is scored on S(300 + h) / S(300), not on S(h) from queue entry.
    subjects = [Subject(float(d), 1, "solar") for d in range(100, 1001, 100)]
    subjects += [Subject(1200.0, 0, "solar")]
    project = dict(ba.DISPLAY_PROJECTS[0], queue_date="2025-10-05")  # 300 days before as-of
    curve = ba.fit_fuel_curves(subjects)["solar"]
    basis, age, surv, lo, hi = ba.project_estimate(project, curve, 365)
    assert (basis, age) == ("conditional_km", 300)
    assert (surv, lo, hi) == curve.conditional_survival(300, 365)
    assert surv == pytest.approx(curve.survival_at(665) / curve.survival_at(300))
    assert surv != pytest.approx(curve.survival_at(365))


def test_project_past_the_last_observed_cod_gets_no_estimate():
    # The last solar COD is at day 900; a project 2,000 days in has nothing to
    # condition on, so it gets basis flat_tail and NaN, not a 0% COD chance.
    subjects = [Subject(float(d), 1, "solar") for d in (300, 600, 900)]
    subjects += [Subject(2500.0, 0, "solar")]
    project = dict(ba.DISPLAY_PROJECTS[0], queue_date="2021-02-07")  # 2,001 days before as-of
    curve = ba.fit_fuel_curves(subjects)["solar"]
    basis, age, surv, lo, hi = ba.project_estimate(project, curve, 730)
    assert (basis, age) == ("flat_tail", 2001)
    assert all(math.isnan(v) for v in (surv, lo, hi))


def test_flat_stretch_or_zero_width_band_gets_no_estimate():
    # The committed gas curve has CODs up to day 729, then a single one at day
    # 2766 with one subject at risk. A gas project aged 1,000-2,035 days has no
    # COD in its 730-day window (the curve is flat there for lack of data); one
    # aged 2,036-2,765 days rests on that lone subject, survival 0 with a 0-0
    # band. Neither is a supported estimate.
    cohort = pd.read_parquet(ROOT / "data/pjm_queue_cohort_2018_2023.parquet")
    curve = ba.fit_fuel_curves(ba.cohort_to_subjects(cohort.to_dict("records")))["gas"]
    for age in (1000, 1500, 2000, 2036, 2500, 2765):
        assert curve.supports_conditional(age)
        assert not curve.supports_window(age, 730)
        assert all(math.isnan(v) for v in curve.conditional_survival(age, 730))
    assert curve.supports_window(600, 730)
    gas = dict(ba.DISPLAY_PROJECTS[2], actual_cod="", status="active")
    for queue_date in ("2022-06-01", "2019-12-01"):  # ages 1,522 and 2,435
        rows = ba.build_survival_rows(
            ba.cohort_to_subjects(cohort.to_dict("records")),
            [dict(gas, project_id="PJM-GAS-X", queue_date=queue_date)],
        )
        assert set(rows["basis"]) == {"flat_tail"}
        assert rows["survival_prob"].isna().all()


def test_committed_rows_condition_on_time_waited():
    committed = pd.read_parquet(ROOT / "data/survival_distributions.parquet")
    by_pid = {pid: grp for pid, grp in committed.groupby("project_id")}
    assert set(by_pid["PJM-ALPHA-003"]["basis"]) == {"observed_cod"}
    # The three active display projects have waited 1,990-2,697 days, longer
    # than the last COD their fuel cohort observed: no number is shipped.
    for pid in ("PJM-ALPHA-001", "PJM-ALPHA-002", "PJM-ALPHA-004"):
        rows = by_pid[pid]
        assert set(rows["basis"]) == {"flat_tail"}
        assert rows["survival_prob"].isna().all()
    assert dict(zip(committed["project_id"], committed["queue_age_days"])) == {
        "PJM-ALPHA-001": 2697, "PJM-ALPHA-002": 2201,
        "PJM-ALPHA-003": 2829, "PJM-ALPHA-004": 1990,
    }
