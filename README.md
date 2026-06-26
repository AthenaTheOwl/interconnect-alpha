# interconnect-alpha

Five hundred seventy megawatts sit in the PJM queue. Three hundred sixty-seven are
expected to actually energize. The other 203 are a wind project in COMED at 37%, a
battery at 48%, and the slow attrition of things that filed but never built.
interconnect-alpha puts a survival probability on each one.

## What it does

A queue position is not a power plant. Most projects that enter an interconnection
queue never reach commercial operation — they stall on studies, lose their offtake,
or get priced out by network upgrade costs. The nameplate megawatts get counted in
forecasts anyway, because counting a queue row is easy and modeling whether it
survives is not.

interconnect-alpha fits the survival curve. It takes the PJM queue, builds a
Kaplan-Meier probability that each project reaches COD by a given horizon, and
backtests the forecast with a Brier score against an earlier cohort so the
probabilities are calibrated rather than asserted. On top of the survival output it
fits a capacity-price fan — the $/MW-day band PJM clears at, conditioned on how much
of the queue is expected to show up. The survival math and the capacity-curve fitter
are the point; the data adapter is small and offline by design.

## try it

No-arg, read-only, offline. Reads the committed PJM survival fixtures under
`data/` and prints a ranked view of which queued projects are likely to reach
commercial operation (COD):

```
python -m interconnect_alpha show
```

```
interconnect-alpha - PJM queue survival, as-of 2026-08-01 (base-case)
4 project(s), ranked by 730-day probability of reaching COD. 367 of 570 nameplate MW expected to energize.

project        zone   fuel         MW COD p(730d)   95% interval  status
------------------------------------------------------------------------
PJM-ALPHA-003  EMAAC  gas        220M        92%   84%-96%    online
PJM-ALPHA-001  PSEG   solar      120M        59%   50%-66%    active
PJM-ALPHA-002  RTO    battery     80M        48%   39%-57%    active
PJM-ALPHA-004  COMED  wind       150M        37%   28%-48%    active

most likely to energize: PJM-ALPHA-003 (EMAAC, gas, 220MW) at 92% by 730d.
most at risk: PJM-ALPHA-004 (COMED, wind, 150MW) at only 37% - 94MW of phantom queue capacity.

capacity-price fan (RTO, $/MW-day):
  2027: p10 $190  p50 $244  p90 $315
  2028: p10 $205  p50 $268  p90 $346
  2029: p10 $210  p50 $274  p90 $358
  2030: p10 $198  p50 $260  p90 $340

calibration: 730-day Brier 0.181 beats naive 0.238 (-0.057); forecasts are better than a base-rate guess.
```

Ranked by 730-day probability of reaching COD, surest build at the top. The wind
project in COMED is 94 megawatts of phantom queue capacity — counted in the
nameplate, unlikely to ever clear. The Brier line is the part that keeps the rest
honest: 0.181 against a naive 0.238 means the curve beats a base-rate guess.

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
  src/
    survival/    kaplan_meier.py, brier_backtest.py
    capacity/    rpm_history_ingest.py, fan_chart.py
    render/      report template, plots
  data/pjm_queue_cohort_2018_2023.parquet
  reports/   checked-in monthly markdown
  eval/      calibration_metrics.py
  decisions/ DEC-ITA-* architectural choices
```

## License

MIT. See [LICENSE](LICENSE).
