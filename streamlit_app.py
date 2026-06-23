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

# Reuse the SAME loaders + scoring the `show` verb uses, so the page mirrors that
# result AND can drive the real engine on user input.
from interconnect_alpha.show import (  # noqa: E402
    _load_calibration,
    _load_cohort,
    _load_fan,
    _load_survival,
    rank_cohort,
    score_project,
)

HORIZON = 730


@st.cache_data(show_spinner=False)
def load_inputs() -> tuple[dict, dict, dict, dict]:
    return (
        _load_survival(REPO),
        _load_cohort(REPO),
        _load_fan(REPO),
        _load_calibration(REPO),
    )


def build_rows() -> tuple[list[dict], dict]:
    survival, cohort, fan, calib = load_inputs()
    # rank_cohort is the SAME engine the `show` verb runs.
    ranked = rank_cohort(survival, cohort, HORIZON)
    rows = [
        {
            "project": r["pid"],
            "zone": r["zone"],
            "fuel": r["fuel"],
            "status": r["status"],
            "MW": r["mw"],
            "cod_prob": r["cod_prob"],
            "lo": r["lo"],
            "hi": r["hi"],
            "phantom_MW": r["phantom_mw"],
        }
        for r in ranked
    ]
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

# ---------------------------------------------------------------------------
# interactive: score a project yourself.
# Drives the real engine — interconnect_alpha.show.score_project — the same
# transform the `show` verb applies to every queued project. Set the announced
# MW, the 730-day survival probability, and the confidence band; the engine
# returns COD probability, expected MW, and phantom MW live.
# ---------------------------------------------------------------------------
st.divider()
st.subheader("score a project yourself")
st.caption(
    "drive the actual survival engine — `interconnect_alpha.show.score_project` — "
    "with your own inputs. a low survival probability means the project is unlikely "
    "to still be un-energized at 730 days, so its COD probability (the complement) "
    "is high. pick a committed project to pre-fill, then edit."
)

projects_by_id = {r["project"]: r for r in rows}
preset_id = st.selectbox(
    "start from a committed project",
    list(projects_by_id),
    help="pre-fills the sliders with that project's announced MW and survival curve.",
)
preset = projects_by_id[preset_id]
preset_survival = 1.0 - preset["cod_prob"]
# preset["lo"]/["hi"] are COD bounds; the survival bounds are their complements.
preset_surv_lo = round(1.0 - preset["hi"], 2)
preset_surv_hi = round(1.0 - preset["lo"], 2)

ic1, ic2 = st.columns(2)
with ic1:
    in_mw = st.slider(
        "announced capacity (MW)",
        0.0,
        2000.0,
        float(round(preset["MW"])),
        step=10.0,
    )
    in_survival = st.slider(
        "730-day survival probability",
        0.0,
        1.0,
        float(round(preset_survival, 2)),
        step=0.01,
        help="probability the project has NOT energized by 730 days.",
    )
with ic2:
    in_lo = st.slider(
        "survival confidence — low",
        0.0,
        1.0,
        float(min(in_survival, preset_surv_lo)),
        step=0.01,
        help="lower bound of the survival curve.",
    )
    in_hi = st.slider(
        "survival confidence — high",
        0.0,
        1.0,
        float(max(in_survival, preset_surv_hi)),
        step=0.01,
        help="upper bound of the survival curve.",
    )

# Call the REAL function — no inline reimplementation.
result = score_project(in_mw, in_survival, confidence_low=in_lo, confidence_high=in_hi)

rc1, rc2, rc3 = st.columns(3)
rc1.metric("COD probability (730d)", f"{result['cod_prob']:.0%}")
rc2.metric("expected to energize", f"{result['expected_mw']:,.0f} MW")
rc3.metric("phantom capacity", f"{result['phantom_mw']:,.0f} MW")

st.caption(
    f"95% COD interval {result['lo']:.0%}-{result['hi']:.0%}. "
    f"of {in_mw:,.0f} announced MW, the engine expects "
    f"{result['expected_mw']:,.0f} MW to reach COD and flags "
    f"{result['phantom_mw']:,.0f} MW as phantom queue capacity."
)

if result["cod_prob"] >= 0.75:
    st.success("high-confidence build — most of the nameplate is real capacity.")
elif result["cod_prob"] <= 0.4:
    st.warning("at-risk — a large share of this nameplate is phantom queue capacity.")
else:
    st.info("contested — roughly even odds of energizing by 730 days.")

st.caption(
    "v0.1 ships one PJM fixture month. the survival math + scoring live in "
    "`interconnect_alpha/`; this page reuses the `show` verb's loaders and its "
    "`score_project` engine against the committed `data/*.parquet`. "
    "repo: github.com/AthenaTheOwl/interconnect-alpha"
)
