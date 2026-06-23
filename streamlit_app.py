"""interconnect-alpha — live demo (Streamlit Community Cloud).

Reads the committed PJM survival fixtures under data/ and shows which queued
projects are likely to reach commercial operation (COD) by the 730-day horizon,
and which capacity is "phantom" (announced in the queue but unlikely to energize).
This mirrors the `python -m interconnect_alpha show` verb — same insight, prettier.

No network, no secrets — runs entirely off the committed fixtures.

Deploy: Streamlit Community Cloud -> New app -> repo AthenaTheOwl/interconnect-alpha,
branch main, main file streamlit_app.py.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# Resolve the committed data relative to this file so it works on Streamlit Cloud.
REPO = Path(__file__).resolve().parent

# Reuse the SAME loaders the `show` verb uses, so the page mirrors that result.
from interconnect_alpha.show import (  # noqa: E402
    _load_calibration,
    _load_cohort,
    _load_fan,
    _load_survival,
)

HORIZON = 730


@st.cache_data(show_spinner=False)
def build_rows() -> tuple[list[dict], dict]:
    survival = _load_survival(REPO)
    cohort = _load_cohort(REPO)
    fan = _load_fan(REPO)
    calib = _load_calibration(REPO)

    rows: list[dict] = []
    for pid, horizons in survival.items():
        h = horizons.get(HORIZON)
        if h is None:
            continue
        meta = cohort.get(pid, {})
        cod_prob = 1.0 - h["survival"]
        mw = float(meta.get("mw", 0.0))
        rows.append(
            {
                "project": pid,
                "zone": meta.get("zone", "?"),
                "fuel": meta.get("fuel", "?"),
                "status": meta.get("status", "?"),
                "MW": mw,
                "cod_prob": cod_prob,
                "lo": 1.0 - h["high"],
                "hi": 1.0 - h["low"],
                "phantom_MW": mw * (1.0 - cod_prob),
            }
        )
    rows.sort(key=lambda r: r["cod_prob"], reverse=True)
    return rows, {"fan": fan, "calib": calib}


st.set_page_config(page_title="interconnect-alpha — PJM queue survival", layout="wide")
st.title("interconnect-alpha")
st.caption(
    "which queued PJM projects are likely to reach commercial operation (COD) by "
    "730 days — and which megawatts are phantom queue capacity unlikely to energize."
)

try:
    rows, extra = build_rows()
except FileNotFoundError:
    st.warning("no committed fixtures found under data/ — cannot render the report.")
    st.stop()

if not rows:
    st.warning("no projects with a 730-day survival horizon in the committed fixtures.")
    st.stop()

fan = extra["fan"]
calib = extra["calib"]

nameplate_mw = sum(r["MW"] for r in rows)
expected_mw = sum(r["MW"] * r["cod_prob"] for r in rows)
phantom_mw = nameplate_mw - expected_mw

st.subheader("PJM queue survival — as-of 2026-08-01 (base-case)")

c1, c2, c3 = st.columns(3)
c1.metric("nameplate", f"{nameplate_mw:,.0f} MW", help="announced queue capacity")
c2.metric(
    "expected to energize",
    f"{expected_mw:,.0f} MW",
    help="sum of MW weighted by 730-day COD probability",
)
c3.metric(
    "phantom",
    f"{phantom_mw:,.0f} MW",
    help="nameplate minus expected — capacity unlikely to reach COD",
)

# One interactive control: filter by minimum 730-day COD probability.
min_prob = st.slider(
    "minimum 730-day COD probability", 0, 100, 0, format="%d%%"
) / 100.0
shown = [r for r in rows if r["cod_prob"] >= min_prob]

st.dataframe(
    [
        {
            "project": r["project"],
            "zone": r["zone"],
            "fuel": r["fuel"],
            "MW": round(r["MW"]),
            "COD p(730d)": f"{r['cod_prob']:.0%}",
            "95% interval": f"{r['lo']:.0%}-{r['hi']:.0%}",
            "phantom MW": round(r["phantom_MW"]),
            "status": r["status"],
        }
        for r in shown
    ],
    use_container_width=True,
    hide_index=True,
)

# Key finding callout: the most at-risk project (largest phantom capacity).
worst = max(rows, key=lambda r: r["phantom_MW"])
st.info(
    f"**most at risk:** {worst['project']} ({worst['zone']}, {worst['fuel']}, "
    f"{worst['MW']:.0f}MW) at only {worst['cod_prob']:.0%} by 730d — "
    f"{worst['phantom_MW']:.0f}MW of phantom queue capacity."
)

c = calib.get(HORIZON)
if c:
    edge = c["naive"] - c["brier"]
    st.success(
        f"**calibration:** 730-day Brier {c['brier']:.3f} beats naive {c['naive']:.3f} "
        f"(-{edge:.3f}); forecasts are better than a base-rate guess."
    )

with st.expander("capacity-price fan (RTO, $/MW-day)"):
    st.dataframe(
        [
            {
                "delivery year": year,
                "p10": f"${fan[year].get(10, 0):.0f}",
                "p50": f"${fan[year].get(50, 0):.0f}",
                "p90": f"${fan[year].get(90, 0):.0f}",
            }
            for year in sorted(fan)
        ],
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "v0.1 ships one PJM fixture month. the survival math + scoring live in "
    "`interconnect_alpha/`; this page reuses the `show` verb's loaders against the "
    "committed `data/*.parquet`. repo: github.com/AthenaTheOwl/interconnect-alpha"
)
