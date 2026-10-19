# interconnect-alpha

Five hundred seventy megawatts sit in the PJM queue. Two hundred seventy-six are
expected to actually energize. The other 294 are a wind project in COMED at 11%, a
battery at 16%, and the slow attrition of things that filed but never built.
interconnect-alpha puts a survival probability on each one. (Those figures are the
730-day `show` output over the committed `data/` fixtures, as-of 2026-08-01,
base-case.)

## What it does

A queue position is not a power plant. Most projects that enter an interconnection
queue never reach commercial operation — they stall on studies, lose their offtake,
or get priced out by network upgrade costs. The nameplate megawatts get counted in
forecasts anyway, because counting a queue row is easy and modeling whether it
survives is not.

interconnect-alpha fits the survival curve. It takes a PJM queue cohort, fits a
right-censored Kaplan-Meier probability that a project reaches COD by a given
horizon (per fuel, with Greenwood confidence bands), and backtests that forecast
with a Brier score against the naive base-rate baseline so the probabilities are
computed rather than asserted. The backtest here is **in-sample**: the shipped
cohort is a small synthetic fixture, so the same rows are used to fit and to score
(see STATUS.md). On top of the survival output it fits a capacity-price fan — the
$/MW-day band PJM clears at, conditioned on how much of the queue is expected to
show up. The survival math and the capacity-curve fitter are the point; the data
adapter is small and offline by design.

## try it

No-arg, read-only, offline. Reads the committed PJM survival fixtures under
`data/` and prints a ranked view of which queued projects are likely to reach
commercial operation (COD):

```
python -m interconnect_alpha show
```

```
interconnect-alpha - PJM queue survival, as-of 2026-08-01 (base-case)
4 project(s), ranked by 730-day probability of reaching COD. 276 of 570 nameplate MW expected to energize.

project        zone   fuel         MW COD p(730d)   95% interval  status
------------------------------------------------------------------------
PJM-ALPHA-003  EMAAC  gas        220M        89%   76%-100%   online
PJM-ALPHA-001  PSEG   solar      120M        42%   20%-64%    active
PJM-ALPHA-002  RTO    battery     80M        16%    0%-32%    active
PJM-ALPHA-004  COMED  wind       150M        11%    0%-24%    active

most likely to energize: PJM-ALPHA-003 (EMAAC, gas, 220MW) at 89% by 730d.
most at risk: PJM-ALPHA-004 (COMED, wind, 150MW) at only 11% - 134MW of phantom queue capacity.

capacity-price fan (RTO, $/MW-day):
  2027: p10 $190  p50 $244  p90 $315
  2028: p10 $205  p50 $268  p90 $346
  2029: p10 $210  p50 $274  p90 $358
  2030: p10 $198  p50 $260  p90 $340

calibration: 730-day Brier 0.141 beats naive 0.239 (-0.098); forecasts are better than a base-rate guess.
```

Ranked by 730-day probability of reaching COD, surest build at the top. Each
project's `p(730d)` is `1 - S(730)` from the right-censored Kaplan-Meier fit for
its fuel class, and the interval is the Greenwood band; the wind project in COMED
is 134 megawatts of phantom queue capacity — counted in the nameplate, unlikely to
clear on that curve. The Brier line is the part that keeps the rest honest: an
in-sample 0.141 against a naive base-rate 0.239 means conditioning the forecast on
fuel type beats a single base-rate guess. All of these numbers are recomputed by
`scripts/build_artifacts.py` from the cohort; none are hand-typed.

To check the artifacts are well-formed: `python -m interconnect_alpha validate`.

## live demo

The same `show` result as an interactive page: ranked COD probabilities, phantom
MW, and the calibration edge, read directly off the committed `data/*.parquet`.

run locally:

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

deploy on streamlit community cloud: new app -> repo `AthenaTheOwl/interconnect-alpha`,
branch `main`, main file `streamlit_app.py`.

<!-- live url: https://<your-app>.streamlit.app -->

## How it connects

interconnect-alpha is the survival layer over the same project graph the energy
repos share:

- [grid-silicon](https://github.com/AthenaTheOwl/grid-silicon) — the data floor:
  scores how real an announced large-load project is. interconnect-alpha is meant to
  fold in as its analytics module once the survival math is validated standalone.
- [ratepayer-exposure](https://github.com/AthenaTheOwl/ratepayer-exposure) — takes
  the capacity-price fan and turns it into one household's power bill.
- [robust-siting-lab](https://github.com/AthenaTheOwl/robust-siting-lab) — uses the
  survival distributions as an input to robust facility-location optimization.

Reports land under `reports/` here while it ships standalone; they get folded into
grid-silicon's `reports/<year>-<month>-<iso>.md` after the merge spec ships.

## Run it in full

```
python -m interconnect_alpha validate
```

`validate` (no args) checks the committed artifacts against the schema and confirms
the survival and capacity outputs are well-formed. See `specs/0002-design/` for the
v0.1 scope and `STATUS.md` (where present) for the current state and next-feature
queue.

## Layout

```
interconnect-alpha/
  AGENTS.md  LICENSE  README.md
  specs/0001-foundation/   requirements, design, tasks, acceptance
  docs/first-pr.md
  interconnect_alpha/
    kaplan_meier.py     right-censored KM estimator + Greenwood CIs
    brier_backtest.py   Brier score of the KM COD forecast vs base-rate baseline
    show.py  validation.py  cli.py   read-only report + schema checks
  scripts/build_artifacts.py   fits KM/Brier and regenerates every data/ artifact
  data/pjm_queue_cohort_2018_2023.parquet   training cohort (synthetic fixture)
  data/survival_distributions.parquet       computed KM survival rows
  data/calibration_metrics.json             computed in-sample Brier backtest
  reports/   checked-in monthly markdown
  decisions/ DEC-ITA-* architectural choices
```

## Method update

[October method update: Withdrawal is a competing event, not proof of eventual delivery](docs/withdrawal-and-censoring.md).

## License

MIT. See [LICENSE](LICENSE).
