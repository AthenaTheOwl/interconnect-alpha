"""Readable, no-arg view of the committed PJM survival report.

The `validate` command proves the artifacts are well-formed. `show` answers the
question a user actually has: of the projects in the queue, which capacity is
likely to reach commercial operation (COD) by the 730-day horizon, and which is
likely to stall? It joins the committed survival distributions with the queue
cohort metadata and the capacity-price fan, then prints a ranked table.

Read-only and offline. Defaults to the checked-in fixtures under data/.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .validation import PARQUET_SCHEMAS, ValidationError, project_root


def _read_table(root: Path, relative: str):
    """Read a parquet fixture, or fail with the same clean error `validate` gives.

    A bad --root (missing directory, a file where a directory was expected, or a
    truncated parquet) otherwise surfaces as a raw pyarrow traceback. Convert it
    to a ValidationError so cli.py prints "SHOW_ERROR ..." and exits non-zero.
    """
    import pyarrow.parquet as pq
    from pyarrow.lib import ArrowInvalid

    path = root / relative
    try:
        return pq.read_table(path).to_pydict()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, ArrowInvalid, OSError) as exc:
        raise ValidationError("show", f"cannot read {relative} under {root}: {exc}") from exc


def _number(value: object) -> float | None:
    """A parquet float, or None for null/NaN (a flat-tail row carries no estimate)."""
    if value is None:
        return None
    number = float(value)
    return None if math.isnan(number) else number


def _load_survival(root: Path) -> dict[str, dict[int, dict[str, object]]]:
    relative = "data/survival_distributions.parquet"
    table = _read_table(root, relative)
    missing = sorted(PARQUET_SCHEMAS[relative] - set(table))
    if missing:
        # e.g. an artifact built before the `basis`/`queue_age_days` columns.
        raise ValidationError(
            "show", f"{relative} under {root} is missing columns: {', '.join(missing)}"
        )
    out: dict[str, dict[int, dict[str, object]]] = {}
    for pid, horizon, basis, age, surv, lo, hi in zip(
        table["project_id"],
        table["days_to_event"],
        table["basis"],
        table["queue_age_days"],
        table["survival_prob"],
        table["confidence_low"],
        table["confidence_high"],
    ):
        out.setdefault(str(pid), {})[int(horizon)] = {
            "basis": str(basis),
            "age_days": int(age),
            "survival": _number(surv),
            "low": _number(lo),
            "high": _number(hi),
        }
    return out


def _load_cohort(root: Path) -> dict[str, dict[str, object]]:
    table = _read_table(root, "data/pjm_queue_cohort_2018_2023.parquet")
    out: dict[str, dict[str, object]] = {}
    for pid, zone, fuel, status, mw in zip(
        table["project_id"],
        table["zone"],
        table["fuel"],
        table["status"],
        table["capacity_mw"],
    ):
        out[str(pid)] = {
            "zone": str(zone),
            "fuel": str(fuel),
            "status": str(status),
            "mw": float(mw),
        }
    return out


def _load_fan(root: Path) -> dict[int, dict[int, float]]:
    table = _read_table(root, "data/capacity_fan_chart_2027_2030.parquet")
    out: dict[int, dict[int, float]] = {}
    for year, pct, price in zip(
        table["delivery_year"], table["percentile"], table["price_mw_day"]
    ):
        out.setdefault(int(year), {})[int(pct)] = float(price)
    return out


def _load_calibration(root: Path) -> dict[int, dict[str, float]]:
    path = root / "data/calibration_metrics.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, OSError) as exc:
        raise ValidationError(
            "show", f"cannot read data/calibration_metrics.json under {root}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "show", f"data/calibration_metrics.json under {root} is not valid JSON: {exc}"
        ) from exc
    return {
        int(row["horizon_days"]): {
            "brier": float(row["brier_score"]),
            "naive": float(row["naive_brier_score"]),
        }
        for row in payload.get("metrics", [])
    }


def score_project(
    mw: float,
    survival_prob: float,
    confidence_low: float | None = None,
    confidence_high: float | None = None,
) -> dict[str, float]:
    """Turn a single project's survival distribution into COD economics.

    This is the core transform the `show` verb applies to every queued project:
    a survival probability at the horizon is the chance the project has NOT yet
    energized, so the probability of reaching commercial operation (COD) is its
    complement. From that we derive how many of the announced megawatts are
    expected to actually energize, and how many are "phantom" queue capacity.

    `confidence_low`/`confidence_high` are the survival-curve bounds; because COD
    is the complement, the COD interval flips them (1 - high, 1 - low).
    """
    survival_prob = max(0.0, min(1.0, float(survival_prob)))
    mw = max(0.0, float(mw))
    cod_prob = 1.0 - survival_prob
    lo = 1.0 - confidence_high if confidence_high is not None else cod_prob
    hi = 1.0 - confidence_low if confidence_low is not None else cod_prob
    return {
        "cod_prob": cod_prob,
        "lo": max(0.0, min(1.0, lo)),
        "hi": max(0.0, min(1.0, hi)),
        "mw": mw,
        "expected_mw": mw * cod_prob,
        "phantom_mw": mw * survival_prob,
    }


def rank_cohort(
    survival: dict[str, dict[int, dict[str, object]]],
    cohort: dict[str, dict[str, object]],
    horizon: int = 730,
) -> list[dict]:
    """Score every project at `horizon` and rank by COD probability (desc).

    `horizon` counts days after the as-of date. Each row carries the survival
    row's `basis` and `age_days` (days already in the queue). `observed_cod` rows
    reached COD by the as-of date: survival 0, so COD probability 1 and the full
    MW count as built. `conditional_km` rows read the fuel curve conditional on
    `age_days`. `flat_tail` rows have no survival number, so `cod_prob`, the
    interval, `expected_mw` and `phantom_mw` are None; they rank last.
    """
    rows: list[dict] = []
    for pid, horizons in survival.items():
        h = horizons.get(horizon)
        if h is None:
            continue
        meta = cohort.get(pid, {})
        mw = float(meta.get("mw", 0.0))
        if h.get("survival") is None:
            scored = {
                "cod_prob": None,
                "lo": None,
                "hi": None,
                "mw": max(0.0, mw),
                "expected_mw": None,
                "phantom_mw": None,
            }
        else:
            scored = score_project(mw, h["survival"], h.get("low"), h.get("high"))
        rows.append(
            {
                "pid": pid,
                "zone": meta.get("zone", "?"),
                "fuel": meta.get("fuel", "?"),
                "status": meta.get("status", "?"),
                "basis": h.get("basis", "?"),
                "age_days": h.get("age_days"),
                **scored,
            }
        )
    rows.sort(key=lambda r: -1.0 if r["cod_prob"] is None else r["cod_prob"], reverse=True)
    return rows


def summarize(rows: list[dict]) -> dict[str, float]:
    """MW totals over ranked rows.

    `online_mw` is built capacity. `scored_mw` is the COD-weighted MW of active
    projects with a supported estimate and `phantom_mw` their remainder;
    `expected_mw` is the two together. `unsupported_mw` is nameplate in flat-tail
    rows, counted in neither expected nor phantom.
    """
    online = [r for r in rows if r["basis"] == "observed_cod"]
    scored = [r for r in rows if r["basis"] != "observed_cod" and r["cod_prob"] is not None]
    online_mw = sum(r["mw"] for r in online)
    scored_mw = sum(r["expected_mw"] for r in scored)
    return {
        "nameplate_mw": sum(r["mw"] for r in rows),
        "online_mw": online_mw,
        "scored_mw": scored_mw,
        "expected_mw": online_mw + scored_mw,
        "phantom_mw": sum(r["phantom_mw"] for r in scored),
        "unsupported_mw": sum(r["mw"] for r in rows if r["cod_prob"] is None),
    }


def render(root: Path | None = None) -> str:
    """Return the human-readable report as a string."""
    resolved = (root or project_root()).resolve()
    survival = _load_survival(resolved)
    cohort = _load_cohort(resolved)
    fan = _load_fan(resolved)
    calib = _load_calibration(resolved)

    horizon = 730
    rows = rank_cohort(survival, cohort, horizon)

    lines: list[str] = []
    lines.append("interconnect-alpha - PJM queue survival, as-of 2026-08-01 (base-case)")
    totals = summarize(rows)
    lines.append(
        f"{len(rows)} project(s), ranked by probability of reaching COD within 730 days of the "
        f"as-of date, given days already in the queue."
    )
    lines.append(
        f"of {totals['nameplate_mw']:.0f} nameplate MW: {totals['online_mw']:.0f} already online, "
        f"{totals['scored_mw']:.0f} expected from scored active projects, "
        f"{totals['unsupported_mw']:.0f} with no supported estimate.\n"
    )

    header = (
        f"{'project':<14} {'zone':<6} {'fuel':<8} {'MW':>6} "
        f"{'COD p(730d)':>11} {'95% interval':>14}  status"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        if r["cod_prob"] is None:
            prob, interval = f"{'n/a':>10}", f"{'flat tail':>9}  "
        elif r["basis"] == "observed_cod":
            prob, interval = f"{r['cod_prob']:>10.0%}", f"{'observed':>9}  "
        else:
            prob, interval = f"{r['cod_prob']:>10.0%}", f"{r['lo']:>5.0%}-{r['hi']:<5.0%}"
        lines.append(
            f"{r['pid']:<14} {r['zone']:<6} {r['fuel']:<8} {r['mw']:>5.0f}M "
            f"{prob} {interval}  {r['status']}"
        )

    # Best and worst are scored forecasts; a project already online is neither,
    # and a flat-tail project has no number to rank.
    forecast = [r for r in rows if r["basis"] != "observed_cod" and r["cod_prob"] is not None]
    if forecast:
        lines.append("")
        best = forecast[0]
        worst = forecast[-1]
        lines.append(
            f"most likely to energize: {best['pid']} ({best['zone']}, {best['fuel']}, "
            f"{best['mw']:.0f}MW) at {best['cod_prob']:.0%} by 730d."
        )
        lines.append(
            f"most at risk: {worst['pid']} ({worst['zone']}, {worst['fuel']}, "
            f"{worst['mw']:.0f}MW) at only {worst['cod_prob']:.0%} - "
            f"{worst['phantom_mw']:.0f}MW of phantom queue capacity."
        )
    unsupported = [r for r in rows if r["cod_prob"] is None]
    if unsupported:
        names = ", ".join(f"{r['pid']} ({r['age_days']}d in queue)" for r in unsupported)
        lines.append("")
        lines.append(f"no supported estimate: {names}.")
        lines.append(
            "for each, the fuel's Kaplan-Meier curve holds no COD in the 730-day window to condition on "
            "(past the cohort's last COD, or on a flat stretch), or only CODs that exhaust the risk set."
        )

    lines.append("")
    lines.append("capacity-price fan (RTO, $/MW-day):")
    for year in sorted(fan):
        pcts = fan[year]
        lines.append(
            f"  {year}: p10 ${pcts.get(10, 0):.0f}  p50 ${pcts.get(50, 0):.0f}  "
            f"p90 ${pcts.get(90, 0):.0f}"
        )

    c = calib.get(horizon)
    if c:
        edge = c["naive"] - c["brier"]
        lines.append("")
        lines.append(
            f"calibration (in-sample): 730-day Brier {c['brier']:.3f} beats naive {c['naive']:.3f} "
            f"(-{edge:.3f}) for the per-fuel curve from queue entry; forecasts are better than "
            f"a base-rate guess."
        )
    return "\n".join(lines)
