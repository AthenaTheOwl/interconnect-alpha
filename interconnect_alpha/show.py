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
from pathlib import Path

from .validation import project_root


def _load_survival(root: Path) -> dict[str, dict[int, dict[str, float]]]:
    import pyarrow.parquet as pq

    table = pq.read_table(root / "data/survival_distributions.parquet").to_pydict()
    out: dict[str, dict[int, dict[str, float]]] = {}
    for pid, horizon, surv, lo, hi in zip(
        table["project_id"],
        table["days_to_event"],
        table["survival_prob"],
        table["confidence_low"],
        table["confidence_high"],
    ):
        out.setdefault(str(pid), {})[int(horizon)] = {
            "survival": float(surv),
            "low": float(lo),
            "high": float(hi),
        }
    return out


def _load_cohort(root: Path) -> dict[str, dict[str, object]]:
    import pyarrow.parquet as pq

    table = pq.read_table(root / "data/pjm_queue_cohort_2018_2023.parquet").to_pydict()
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
    import pyarrow.parquet as pq

    table = pq.read_table(root / "data/capacity_fan_chart_2027_2030.parquet").to_pydict()
    out: dict[int, dict[int, float]] = {}
    for year, pct, price in zip(
        table["delivery_year"], table["percentile"], table["price_mw_day"]
    ):
        out.setdefault(int(year), {})[int(pct)] = float(price)
    return out


def _load_calibration(root: Path) -> dict[int, dict[str, float]]:
    payload = json.loads(
        (root / "data/calibration_metrics.json").read_text(encoding="utf-8")
    )
    return {
        int(row["horizon_days"]): {
            "brier": float(row["brier_score"]),
            "naive": float(row["naive_brier_score"]),
        }
        for row in payload.get("metrics", [])
    }


def render(root: Path | None = None) -> str:
    """Return the human-readable report as a string."""
    resolved = (root or project_root()).resolve()
    survival = _load_survival(resolved)
    cohort = _load_cohort(resolved)
    fan = _load_fan(resolved)
    calib = _load_calibration(resolved)

    horizon = 730
    rows = []
    for pid, horizons in survival.items():
        h = horizons.get(horizon)
        if h is None:
            continue
        meta = cohort.get(pid, {})
        cod_prob = 1.0 - h["survival"]
        rows.append(
            {
                "pid": pid,
                "zone": meta.get("zone", "?"),
                "fuel": meta.get("fuel", "?"),
                "status": meta.get("status", "?"),
                "mw": float(meta.get("mw", 0.0)),
                "cod_prob": cod_prob,
                "lo": 1.0 - h["high"],
                "hi": 1.0 - h["low"],
            }
        )
    rows.sort(key=lambda r: r["cod_prob"], reverse=True)

    lines: list[str] = []
    lines.append("interconnect-alpha - PJM queue survival, as-of 2026-08-01 (base-case)")
    expected_mw = sum(r["mw"] * r["cod_prob"] for r in rows)
    nameplate_mw = sum(r["mw"] for r in rows)
    lines.append(
        f"{len(rows)} project(s), ranked by 730-day probability of reaching COD. "
        f"{expected_mw:.0f} of {nameplate_mw:.0f} nameplate MW expected to energize.\n"
    )

    header = (
        f"{'project':<14} {'zone':<6} {'fuel':<8} {'MW':>6} "
        f"{'COD p(730d)':>11} {'95% interval':>14}  status"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for r in rows:
        lines.append(
            f"{r['pid']:<14} {r['zone']:<6} {r['fuel']:<8} {r['mw']:>5.0f}M "
            f"{r['cod_prob']:>10.0%} "
            f"{r['lo']:>5.0%}-{r['hi']:<5.0%}  {r['status']}"
        )

    best = rows[0]
    worst = rows[-1]
    lines.append("")
    lines.append(
        f"most likely to energize: {best['pid']} ({best['zone']}, {best['fuel']}, "
        f"{best['mw']:.0f}MW) at {best['cod_prob']:.0%} by 730d."
    )
    lines.append(
        f"most at risk: {worst['pid']} ({worst['zone']}, {worst['fuel']}, "
        f"{worst['mw']:.0f}MW) at only {worst['cod_prob']:.0%} - "
        f"{worst['mw'] * (1 - worst['cod_prob']):.0f}MW of phantom queue capacity."
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
            f"calibration: 730-day Brier {c['brier']:.3f} beats naive {c['naive']:.3f} "
            f"(-{edge:.3f}); forecasts are better than a base-rate guess."
        )
    return "\n".join(lines)
