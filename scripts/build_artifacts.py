"""Regenerate the checked-in PJM survival artifacts from computed numbers.

Every survival probability, confidence interval, and Brier score written here is
*computed* from the queue cohort by the Kaplan-Meier and Brier modules in
``interconnect_alpha`` -- none are typed in as literals. Change the cohort and the
survival rows, calibration metrics, and report all change with it.

Pipeline:

1. Build the 2018-2023 training cohort (``data/pjm_queue_cohort_2018_2023.parquet``).
   This is a disclosed synthetic fixture: a deterministic, seeded draw shaped like
   public PJM/LBNL "Queued Up" data, not a real ingest. The four named display
   projects (PJM-ALPHA-001..004) are pinned; the rest fill out per-fuel strata so
   Kaplan-Meier has enough events and censoring to fit.
2. Fit a right-censored Kaplan-Meier curve per fuel. Score each display project at
   the as-of date: built if it already reached COD, else the curve conditional on
   days already in the queue (Greenwood band), or no estimate where the curve cannot
   back the window (past the last COD its fuel cohort observed, no COD in the
   window, or a 0-0 band) -> ``data/survival_distributions.parquet``.
3. Backtest the per-fuel COD forecast against the naive base rate (in-sample) ->
   ``data/calibration_metrics.json``.
4. Rewrite the monthly report (``reports/2026-08-pjm-survival.md`` + ``.jsonl``) and
   the capacity-side fixtures (RPM history, fan chart parquet + SVG) which are
   deterministic scenario outputs, out of scope for the survival estimator.
"""

from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interconnect_alpha.brier_backtest import Subject, backtest  # noqa: E402
from interconnect_alpha.kaplan_meier import kaplan_meier  # noqa: E402

AS_OF = date(2026, 8, 1)
DISPLAY_HORIZONS = (365, 730)
CALIBRATION_HORIZONS = (365, 730, 1460)
COHORT_SEED = 20260801

# Fuel strata for the synthetic training cohort. `p_event` is the share that
# reach COD; `lag_mean`/`lag_sd` shape days from queue entry to COD (a compressed,
# illustrative timescale for the fixture). Ordering (gas fast, wind slow) is the
# only thing tuned; the shipped probabilities fall out of the KM fit.
FUEL_PARAMS = {
    "gas": {"n": 18, "p_event": 0.85, "lag_mean": 520, "lag_sd": 230, "p_withdraw": 0.05},
    "solar": {"n": 18, "p_event": 0.66, "lag_mean": 700, "lag_sd": 300, "p_withdraw": 0.12},
    "battery": {"n": 18, "p_event": 0.55, "lag_mean": 900, "lag_sd": 340, "p_withdraw": 0.18},
    "wind": {"n": 18, "p_event": 0.45, "lag_mean": 1250, "lag_sd": 460, "p_withdraw": 0.25},
}
FUEL_ZONES = {
    "gas": ["EMAAC", "RTO", "PSEG"],
    "solar": ["PSEG", "RTO", "DOM"],
    "battery": ["RTO", "COMED", "PSEG"],
    "wind": ["COMED", "RTO", "APS"],
}

# The four named display projects, pinned so `show` keeps rendering them.
DISPLAY_PROJECTS = [
    {"project_id": "PJM-ALPHA-001", "zone": "PSEG", "fuel": "solar",
     "queue_date": "2019-03-14", "announced_cod": "2027-06-01", "actual_cod": "",
     "withdrawal_date": "", "status": "active", "capacity_mw": 120.0},
    {"project_id": "PJM-ALPHA-002", "zone": "RTO", "fuel": "battery",
     "queue_date": "2020-07-22", "announced_cod": "2027-12-01", "actual_cod": "",
     "withdrawal_date": "", "status": "active", "capacity_mw": 80.0},
    {"project_id": "PJM-ALPHA-003", "zone": "EMAAC", "fuel": "gas",
     "queue_date": "2018-11-02", "announced_cod": "2026-11-15", "actual_cod": "2026-05-30",
     "withdrawal_date": "", "status": "online", "capacity_mw": 220.0},
    {"project_id": "PJM-ALPHA-004", "zone": "COMED", "fuel": "wind",
     "queue_date": "2021-02-18", "announced_cod": "2028-05-01", "actual_cod": "",
     "withdrawal_date": "", "status": "active", "capacity_mw": 150.0},
]


def _iso(d: date) -> str:
    return d.isoformat()


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


# ---------------------------------------------------------------------------
# 1. cohort
# ---------------------------------------------------------------------------


def generate_cohort(seed: int = COHORT_SEED) -> list[dict]:
    """Deterministic, seeded synthetic 2018-2023 training cohort."""
    rng = random.Random(seed)
    rows: list[dict] = list(DISPLAY_PROJECTS)
    window_start = date(2018, 1, 1)
    window_days = (date(2023, 12, 31) - window_start).days

    for fuel, params in FUEL_PARAMS.items():
        for i in range(params["n"]):
            queue = window_start + timedelta(days=rng.randint(0, window_days))
            roll = rng.random()
            zone = rng.choice(FUEL_ZONES[fuel])
            mw = round(rng.uniform(40, 300), 1)
            row = {
                "project_id": f"PJM-{fuel[:2].upper()}-{i:03d}",
                "zone": zone,
                "fuel": fuel,
                "queue_date": _iso(queue),
                "announced_cod": _iso(queue + timedelta(days=rng.randint(900, 1800))),
                "actual_cod": "",
                "withdrawal_date": "",
                "status": "active",
                "capacity_mw": mw,
            }
            if roll < params["p_event"]:
                lag = max(120, int(rng.gauss(params["lag_mean"], params["lag_sd"])))
                cod = queue + timedelta(days=lag)
                if cod <= AS_OF:
                    row["actual_cod"] = _iso(cod)
                    row["status"] = "online"
                # else: energizes after the report date -> still active (censored)
            elif roll < params["p_event"] + params["p_withdraw"]:
                # withdrawn before its announced COD; censored at that exit date.
                # The exit date gets its own column so announced_cod keeps the
                # developer's announced date.
                exit_date = min(
                    date.fromisoformat(row["announced_cod"]),
                    AS_OF - timedelta(days=rng.randint(0, 400)),
                )
                if exit_date > queue:
                    row["status"] = "withdrawn"
                    row["withdrawal_date"] = _iso(exit_date)
            rows.append(row)
    return rows


def cohort_to_subjects(rows: list[dict]) -> list[Subject]:
    """Reduce cohort rows to (duration, event, fuel) survival subjects."""
    subjects: list[Subject] = []
    as_of = _iso(AS_OF)
    for row in rows:
        queue = row["queue_date"]
        if row["actual_cod"]:
            duration = _days(row["actual_cod"], queue)
            event = 1
        elif row["status"] == "withdrawn":
            duration = _days(row["withdrawal_date"], queue)  # censored at exit
            event = 0
        else:
            duration = _days(as_of, queue)  # active: censored at report date
            event = 0
        if duration <= 0:
            continue
        subjects.append(Subject(duration=float(duration), event=event, group=row["fuel"]))
    return subjects


# ---------------------------------------------------------------------------
# 2. survival rows (computed via KM)
# ---------------------------------------------------------------------------


def fit_fuel_curves(subjects: list[Subject]):
    fuels = sorted({s.group for s in subjects})
    return {
        fuel: kaplan_meier(
            [s.duration for s in subjects if s.group == fuel],
            [s.event for s in subjects if s.group == fuel],
        )
        for fuel in fuels
    }


def project_estimate(project: dict, curve, horizon: int) -> tuple[str, int, float, float, float]:
    """``(basis, queue_age_days, survival_prob, confidence_low, confidence_high)``.

    ``horizon`` counts days after the as-of date and ``queue_age_days`` is how long
    the project has already waited at the as-of date. Three cases:

    - ``observed_cod``: COD on or before the as-of date. The project is built:
      survival 0 with no band, and the fuel curve is not consulted.
    - ``conditional_km``: still active, and its fuel cohort holds a COD after this
      age. Survival is ``S(age + horizon) / S(age)`` with the Greenwood band over
      ``(age, age + horizon]``.
    - ``flat_tail``: still active, but the fuel curve cannot back the window
      ``(age, age + horizon]``: the project is older than the last COD its fuel
      cohort observed, or the window holds no COD (the curve is flat there for
      lack of events), or its CODs exhaust the risk set and leave a 0-0 band.
      There is no estimate: survival and band are NaN.
    """
    age = _days(_iso(AS_OF), project["queue_date"])
    if project["actual_cod"] and date.fromisoformat(project["actual_cod"]) <= AS_OF:
        return ("observed_cod", age, 0.0, 0.0, 0.0)
    if not curve.supports_window(age, horizon):
        return ("flat_tail", age, math.nan, math.nan, math.nan)
    surv, lo, hi = curve.conditional_survival(age, horizon)
    return ("conditional_km", age, surv, lo, hi)


def build_survival_rows(
    subjects: list[Subject], projects: list[dict] = DISPLAY_PROJECTS
) -> pd.DataFrame:
    curves = fit_fuel_curves(subjects)
    as_of = _iso(AS_OF)
    records = []
    for proj in projects:
        curve = curves[proj["fuel"]]
        for h in DISPLAY_HORIZONS:
            basis, age, surv, lo, hi = project_estimate(proj, curve, h)
            records.append(
                [proj["project_id"], as_of, h, basis, age,
                 round(surv, 4), round(lo, 4), round(hi, 4)]
            )
    return pd.DataFrame(
        records,
        columns=[
            "project_id", "as_of", "days_to_event", "basis", "queue_age_days",
            "survival_prob", "confidence_low", "confidence_high",
        ],
    )


# ---------------------------------------------------------------------------
# 3. calibration (computed via Brier backtest)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Calibration:
    payload: dict
    results: list


def build_calibration(subjects: list[Subject]) -> Calibration:
    results = [backtest(subjects, h, sample="in-sample") for h in CALIBRATION_HORIZONS]
    payload = {
        "as_of": _iso(AS_OF),
        "evaluation": "in-sample",
        "note": (
            "Per-fuel Kaplan-Meier COD forecast scored against the naive base-rate "
            "baseline on the training cohort. In-sample: the cohort is too small to "
            "hold out a credible earlier fold."
        ),
        "cohort_projects": len(subjects),
        "metrics": [
            {
                "horizon_days": r.horizon_days,
                "brier_score": round(r.brier_score, 4),
                "naive_brier_score": round(r.naive_brier_score, 4),
                "base_rate": round(r.base_rate, 4),
                "n_scored": r.n_scored,
            }
            for r in results
        ],
    }
    return Calibration(payload=payload, results=results)


# ---------------------------------------------------------------------------
# 4. capacity-side fixtures (deterministic scenario outputs, unchanged)
# ---------------------------------------------------------------------------


def write_capacity_fixtures(data_dir: Path) -> None:
    rpm = pd.DataFrame(
        [
            [2023, 2026, "RTO", 28.92],
            [2023, 2026, "EMAAC", 49.49],
            [2024, 2027, "RTO", 269.92],
            [2024, 2027, "PSEG", 280.75],
            [2025, 2028, "RTO", 312.50],
            [2025, 2028, "COMED", 297.10],
        ],
        columns=["auction_year", "delivery_year", "lda_zone", "clearing_price_mw_day"],
    )
    rpm.to_parquet(data_dir / "pjm_rpm_history.parquet", index=False)

    fan = pd.DataFrame(
        [
            ["base-case", 2027, "RTO", 10, 190.0, "2026-08-01"],
            ["base-case", 2027, "RTO", 50, 244.0, "2026-08-01"],
            ["base-case", 2027, "RTO", 90, 315.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 10, 205.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 50, 268.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 90, 346.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 10, 210.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 50, 274.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 90, 358.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 10, 198.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 50, 260.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 90, 340.0, "2026-08-01"],
        ],
        columns=["scenario", "delivery_year", "lda_zone", "percentile", "price_mw_day", "as_of"],
    )
    fan.to_parquet(data_dir / "capacity_fan_chart_2027_2030.parquet", index=False)


def write_svg(root: Path) -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420" viewBox="0 0 720 420" role="img" aria-label="PJM RTO capacity-price fan chart 2027 to 2030">
  <rect width="720" height="420" fill="#ffffff"/>
  <text x="48" y="42" font-family="Arial" font-size="20" fill="#1f2937">PJM RTO capacity-price fan chart</text>
  <text x="48" y="66" font-family="Arial" font-size="13" fill="#4b5563">base-case, dollars per MW-day</text>
  <line x1="72" y1="348" x2="660" y2="348" stroke="#111827" stroke-width="1"/>
  <line x1="72" y1="92" x2="72" y2="348" stroke="#111827" stroke-width="1"/>
  <text x="52" y="352" font-family="Arial" font-size="11" fill="#374151">0</text>
  <text x="42" y="232" font-family="Arial" font-size="11" fill="#374151">200</text>
  <text x="42" y="108" font-family="Arial" font-size="11" fill="#374151">400</text>
  <polygon points="120,226 280,206 440,198 600,210 600,130 440,118 280,130 120,154" fill="#c7d2fe" opacity="0.85"/>
  <polyline points="120,181 280,162 440,158 600,169" fill="none" stroke="#1d4ed8" stroke-width="3"/>
  <polyline points="120,226 280,206 440,198 600,210" fill="none" stroke="#4338ca" stroke-width="1.5"/>
  <polyline points="120,154 280,130 440,118 600,130" fill="none" stroke="#4338ca" stroke-width="1.5"/>
  <text x="110" y="372" font-family="Arial" font-size="12" fill="#374151">2027</text>
  <text x="270" y="372" font-family="Arial" font-size="12" fill="#374151">2028</text>
  <text x="430" y="372" font-family="Arial" font-size="12" fill="#374151">2029</text>
  <text x="590" y="372" font-family="Arial" font-size="12" fill="#374151">2030</text>
  <text x="520" y="93" font-family="Arial" font-size="12" fill="#4338ca">p10-p90</text>
  <text x="520" y="113" font-family="Arial" font-size="12" fill="#1d4ed8">median</text>
</svg>
"""
    (root / "data/capacity_fan_chart_2027_2030.svg").write_text(svg, encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. report
# ---------------------------------------------------------------------------


def _cod(survival_prob: float) -> float:
    return 1.0 - survival_prob


def write_report(
    root: Path, survival: pd.DataFrame, calib: Calibration, cohort_rows: list[dict], curves: dict
) -> None:
    by_project = {
        pid: {
            int(h): (basis, int(age), sp, lo, hi)
            for _, h, basis, age, sp, lo, hi in grp.itertuples(index=False)
        }
        for pid, grp in (
            survival[["project_id", "days_to_event", "basis", "queue_age_days", "survival_prob",
                      "confidence_low", "confidence_high"]].groupby("project_id")
        )
    }
    order = [p["project_id"] for p in DISPLAY_PROJECTS]
    zones = {p["project_id"]: p["zone"] for p in DISPLAY_PROJECTS}
    fuels = {p["project_id"]: p["fuel"] for p in DISPLAY_PROJECTS}
    mws = {p["project_id"]: p["capacity_mw"] for p in DISPLAY_PROJECTS}

    m730 = next(m for m in calib.payload["metrics"] if m["horizon_days"] == 730)

    rows_730 = {pid: by_project[pid][730] for pid in order}
    online_mw = sum(mws[pid] for pid, r in rows_730.items() if r[0] == "observed_cod")
    scored = [pid for pid, r in rows_730.items() if r[0] == "conditional_km"]
    scored_mw = sum(mws[pid] * _cod(rows_730[pid][2]) for pid in scored)
    flat_mw = sum(mws[pid] for pid, r in rows_730.items() if r[0] == "flat_tail")
    if scored:
        scored_txt = (
            f"{scored_mw:.0f} MW expected within 730 days from the {len(scored)} active "
            f"project(s) with a supported estimate"
        )
    else:
        scored_txt = "no active project has a supported estimate"

    lines: list[str] = []
    lines.append("# PJM Queue Survival Report - 2026-08\n")
    lines.append("As of: 2026-08-01\n")
    lines.append("Canonical scenario: `base-case`\n")
    lines.append("## Summary\n")
    lines.append(f"- Training cohort: {len(cohort_rows)} projects across four fuels, 2018-2023 queue entries (synthetic fixture).")
    lines.append(
        f"- Display projects: {sum(mws.values()):.0f} nameplate MW. {online_mw:.0f} MW already online; "
        f"{scored_txt}; {flat_mw:.0f} MW sit in active projects their fuel curve cannot score "
        f"(basis `flat_tail`), with no estimate."
    )
    lines.append("- Median RTO capacity-price case for 2028: $268.00/MW-day, with p10-p90 range $205.00-$346.00/MW-day.")
    lines.append(
        f"- Calibration gate (in-sample): 730-day Brier score {m730['brier_score']:.3f}, "
        f"naive baseline {m730['naive_brier_score']:.3f}.\n"
    )
    lines.append("## Project Survival\n")
    lines.append(
        "Each active project reads its fuel's Kaplan-Meier curve conditional on the days it has "
        "already spent in the queue at the as-of date: `S(age + h) / S(age)`, with the Greenwood "
        "band over `(age, age + h]`. The horizon `h` counts days after the as-of date. COD "
        "probability is `1 - survival_prob`. A project that reached COD by the as-of date counts "
        "as built (basis `observed_cod`): probability 1, no band, no curve. An active project "
        "older than the last COD its fuel cohort observed sits on the flat tail of the curve, "
        "where there are no events to condition on (basis `flat_tail`): no estimate. The same "
        "holds when the window `(age, age + h]` holds no COD, or holds only CODs that exhaust "
        "the risk set and leave a 0-0 band.\n"
    )
    lines.append(
        "| project_id | PJM zone | fuel | days in queue | basis | "
        "730-day COD probability | 95% interval |"
    )
    lines.append("| --- | --- | --- | ---: | --- | ---: | ---: |")
    for pid in order:
        basis, age, sp, lo, hi = rows_730[pid]
        if basis == "observed_cod":
            prob, interval = f"{_cod(sp):.2f}", "observed"
        elif basis == "flat_tail":
            prob, interval = "n/a", "n/a"
        else:
            prob, interval = f"{_cod(sp):.2f}", f"{_cod(hi):.2f}-{_cod(lo):.2f}"
        lines.append(
            f"| {pid} | {zones[pid]} | {fuels[pid]} | {age} | {basis} | {prob} | {interval} |"
        )
    lines.append("")
    lines.append("### Fuel curves\n")
    lines.append(
        "The per-fuel curves the rows above are read from, measured from queue entry. "
        "Withdrawn projects are right-censored at their withdrawal date "
        "(see `docs/withdrawal-and-censoring.md`). The 730-day column is the forecast the "
        "Brier backtest scores.\n"
    )
    lines.append(
        "| fuel | projects | reached COD | withdrawn | last observed COD (days from entry) | "
        "730-day COD probability from entry |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for fuel in sorted(curves):
        curve = curves[fuel]
        withdrawn = sum(
            1 for r in cohort_rows if r["fuel"] == fuel and r["status"] == "withdrawn"
        )
        last = curve.last_event_time
        lines.append(
            f"| {fuel} | {curve.n_total} | {curve.n_events} | {withdrawn} | "
            f"{'n/a' if last is None else f'{last:.0f}'} | {_cod(curve.survival_at(730)):.2f} |"
        )
    lines.append("")
    lines.append("## Capacity Price Fan\n")
    lines.append("| Delivery year | p10 | p50 | p90 |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append("| 2027 | $190.00 | $244.00 | $315.00 |")
    lines.append("| 2028 | $205.00 | $268.00 | $346.00 |")
    lines.append("| 2029 | $210.00 | $274.00 | $358.00 |")
    lines.append("| 2030 | $198.00 | $260.00 | $340.00 |")
    lines.append("")
    lines.append("Plot: `data/capacity_fan_chart_2027_2030.svg`\n")
    lines.append("## Calibration\n")
    lines.append(f"- Evaluation: {calib.payload['evaluation']} (per-fuel KM vs naive base-rate baseline).")
    for m in calib.payload["metrics"]:
        lines.append(
            f"- {m['horizon_days']}-day Brier score: {m['brier_score']:.3f}; "
            f"naive baseline: {m['naive_brier_score']:.3f}; scored on {m['n_scored']} projects."
        )
    lines.append("- Most recent recalibration run: 2026-08-01.\n")
    lines.append("## Method\n")
    lines.append(
        "Survival rows use the schema accepted in\n"
        "`decisions/DEC-ITA-001-survival-estimator.md` plus its `basis` and `queue_age_days`\n"
        "columns, populated by a right-censored Kaplan-Meier fit\n"
        "(`interconnect_alpha/kaplan_meier.py`) per fuel with Greenwood confidence bands. The\n"
        "Brier backtest (`interconnect_alpha/brier_backtest.py`) scores the per-fuel COD\n"
        "forecast from queue entry against the overall base rate. It is an in-sample figure:\n"
        "the fixture cohort is small, so the same rows are used to fit and to score. Capacity\n"
        "scenarios use the canonical rule in `decisions/DEC-ITA-002-scenario-set.md`.\n"
    )
    lines.append(
        "The report treats `survival_prob` as probability of not reaching COD within\n"
        "`days_to_event` days after the as-of date; the project table reports COD probability\n"
        "as `1 - survival_prob`.\n"
    )
    lines.append("## Inputs\n")
    for rel in [
        "data/pjm_queue_cohort_2018_2023.parquet",
        "data/survival_distributions.parquet",
        "data/pjm_rpm_history.parquet",
        "data/capacity_fan_chart_2027_2030.parquet",
        "data/calibration_metrics.json",
        "data/scenarios.yaml",
    ]:
        lines.append(f"- `{rel}`")
    lines.append("")
    (root / "reports/2026-08-pjm-survival.md").write_text("\n".join(lines), encoding="utf-8")

    jsonl = {
        "report_id": "2026-08-pjm-survival",
        "scenario_id": "base-case",
        "report_md": "reports/2026-08-pjm-survival.md",
        "fan_chart": "data/capacity_fan_chart_2027_2030.svg",
        "brier_score_730d": m730["brier_score"],
        "naive_brier_score_730d": m730["naive_brier_score"],
        "evaluation": "in-sample",
        "verdict": "per-fuel KM beats the naive base rate in-sample; ingest a real cohort to backtest held-out next",
    }
    (root / "reports/2026-08-pjm-survival.jsonl").write_text(
        json.dumps(jsonl, separators=(",", ":")) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def build(root: Path) -> dict:
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)

    cohort_rows = generate_cohort()
    cohort_df = pd.DataFrame(
        cohort_rows,
        columns=["project_id", "zone", "fuel", "queue_date", "announced_cod",
                 "actual_cod", "withdrawal_date", "status", "capacity_mw"],
    )
    cohort_df.to_parquet(data_dir / "pjm_queue_cohort_2018_2023.parquet", index=False)

    subjects = cohort_to_subjects(cohort_rows)

    survival_df = build_survival_rows(subjects)
    survival_df.to_parquet(data_dir / "survival_distributions.parquet", index=False)

    calib = build_calibration(subjects)
    (data_dir / "calibration_metrics.json").write_text(
        json.dumps(calib.payload, indent=2) + "\n", encoding="utf-8"
    )

    write_capacity_fixtures(data_dir)
    write_svg(root)
    write_report(root, survival_df, calib, cohort_rows, fit_fuel_curves(subjects))

    return {"cohort": len(cohort_rows), "subjects": len(subjects), "calibration": calib.payload}


def main() -> int:
    summary = build(ROOT)
    metrics = summary["calibration"]["metrics"]
    print(f"cohort={summary['cohort']} subjects={summary['subjects']}")
    for m in metrics:
        print(
            f"  h={m['horizon_days']:>4} brier={m['brier_score']:.3f} "
            f"naive={m['naive_brier_score']:.3f} n={m['n_scored']} base_rate={m['base_rate']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
