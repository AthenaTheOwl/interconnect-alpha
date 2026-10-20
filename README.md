# interconnect-alpha

Four PJM queue projects carry five hundred seventy megawatts of nameplate. Two
hundred twenty of them are a gas plant in EMAAC that reached commercial operation in
May 2026, which settles its odds. The other three hundred fifty sit in a solar, a
battery and a wind project that have each waited longer than any project of their
fuel in the cohort took to energize. The Kaplan-Meier curve has gone flat by the
time it reaches them, so interconnect-alpha prints `n/a` for all three. It puts a
survival probability on a queue project when its fuel cohort has seen projects that
old reach COD, and says so when it has not. (Those figures are the `show` output
over the committed `data/` fixtures, as-of 2026-08-01, base-case.)

## What it does

A queue position is not a power plant. Most projects that enter an interconnection
queue never reach commercial operation — they stall on studies, lose their offtake,
or get priced out by network upgrade costs. The nameplate megawatts get counted in
forecasts anyway, because counting a queue row is easy and modeling whether it
survives is not.

interconnect-alpha fits the survival curve. It takes a PJM queue cohort, fits a
right-censored Kaplan-Meier curve per fuel (with Greenwood confidence bands), reads
each active project's chance of reaching COD within a horizon given the days it has
already spent in the queue, and backtests the per-fuel forecast with a Brier score
against the naive base-rate baseline so the probabilities are computed rather than
asserted. The backtest here is **in-sample**: the shipped
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
4 project(s), ranked by probability of reaching COD within 730 days of the as-of date, given days already in the queue.
of 570 nameplate MW: 220 already online, 0 expected from scored active projects, 350 with no supported estimate.

project        zone   fuel         MW COD p(730d)   95% interval  status
------------------------------------------------------------------------
PJM-ALPHA-003  EMAAC  gas        220M       100%  observed    online
PJM-ALPHA-001  PSEG   solar      120M        n/a flat tail    active
PJM-ALPHA-002  RTO    battery     80M        n/a flat tail    active
PJM-ALPHA-004  COMED  wind       150M        n/a flat tail    active

no supported estimate: PJM-ALPHA-001 (2697d in queue), PJM-ALPHA-002 (2201d in queue), PJM-ALPHA-004 (1990d in queue).
for each, the fuel's Kaplan-Meier curve holds no COD in the 730-day window to condition on (past the cohort's last COD, or on a flat stretch), or only CODs that exhaust the risk set.

capacity-price fan (RTO, $/MW-day):
  2027: p10 $190  p50 $244  p90 $315
  2028: p10 $205  p50 $268  p90 $346
  2029: p10 $210  p50 $274  p90 $358
  2030: p10 $198  p50 $260  p90 $340

calibration (in-sample): 730-day Brier 0.141 beats naive 0.239 (-0.098) for the per-fuel curve from queue entry; forecasts are better than a base-rate guess.
```

Ranked by probability of reaching COD within 730 days of the as-of date. A project
already online counts as built: 100%, full megawatts, no curve. An active project's
`p(730d)` is `1 - S(age + 730) / S(age)` from its fuel's right-censored Kaplan-Meier
fit, where `age` is its days in the queue, and the interval is the Greenwood band
over that window. When no project of that fuel reached COD after `age` days, the
curve is flat from there on and the ratio would read 1 for lack of data; `show`
prints `n/a` and keeps those megawatts out of both the expected and the phantom
totals. It does the same when the window holds no COD (a flat stretch mid-curve) or
holds only CODs that exhaust the risk set, which would read 0 with a 0-0 band. In the committed fixture that is every active project: the cohort's last
solar, battery and wind CODs land at 1,332, 1,391 and 1,551 days (the fuel-curve
table in `reports/2026-08-pjm-survival.md`). The Brier line scores the per-fuel
curve from queue entry: an in-sample 0.141 against a naive base-rate 0.239 means
conditioning on fuel type beats a single base-rate guess. Withdrawn projects are
censored at their withdrawal date, which reads withdrawal as uninformative about
COD; [the method note](docs/withdrawal-and-censoring.md) says what a competing-risks
fit would change. All of these numbers are recomputed by
`scripts/build_artifacts.py` from the cohort; none are hand-typed.

To check the artifacts are well-formed: `python -m interconnect_alpha validate`.

## live demo

The same `show` result as an interactive page: ranked COD probabilities, phantom
MW, the projects with no supported estimate, and the calibration edge, read
directly off the committed `data/*.parquet`.

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

[October method update: Withdrawal as a competing event in the survival fit](docs/withdrawal-and-censoring.md).

## License

MIT. See [LICENSE](LICENSE).
