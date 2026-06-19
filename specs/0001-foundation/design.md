# Design — 0001-foundation (interconnect-alpha)

## Shape

Two pipelines that share an output report. The survival pipeline
ingests the LBNL queue cohort, fits Kaplan-Meier curves per project,
backtests the fit against held-out folds. The capacity pipeline
ingests PJM RPM auction history and fits a probabilistic fan chart
for the 2027-2030 horizon. The report stitches both together.

## Components

### Survival (`src/survival/`)

- `cohort_ingest.py` — pulls and parses the LBNL Queued Up 2018-2023
  PJM cohort export; writes
  `data/pjm_queue_cohort_2018_2023.parquet`. Pure transform on the
  raw download.
- `kaplan_meier.py` — fits per-project survival curves. v0 uses
  `lifelines` under the hood; the wrapper exposes a thin typed API
  so the estimator can be swapped later (Cox, AFT) under a
  follow-up spec.
- `brier_backtest.py` — k-fold backtest. Computes Brier at 365,
  730, 1460 days. Prints the naive baseline (announced-as-COD)
  alongside.

### Capacity (`src/capacity/`)

- `rpm_history_ingest.py` — reads PJM Reliability Pricing Model
  auction results from the PJM public results page since 2014;
  writes `data/pjm_rpm_history.parquet`.
- `scenarios.py` — loads `data/scenarios.yaml` and applies each
  scenario's perturbations to the inputs the fan-chart fitter sees.
- `fan_chart.py` — Monte Carlo sampler over (queue clearing, load
  growth, weather). Emits a probabilistic fan chart per LDA zone
  for 2027-2030. Output is both parquet (per percentile per year)
  and a deterministic PNG.

### Render (`src/render/`)

- `report.py` — emits `reports/YYYY-MM-pjm-survival.md` from the
  survival parquet, the capacity parquet, and a Jinja template.
- `plots.py` — survival curve plots and fan-chart PNG generation.

### Eval (`eval/`)

- `calibration_metrics.py` — top-level entry that runs
  `brier_backtest.py` and asserts the calibration constraint.

## Data flow

```
LBNL Queued Up -> cohort_ingest -> pjm_queue_cohort_2018_2023.parquet
                                              |
                                              v
                                       kaplan_meier.py
                                              |
                                              v
                                survival_distributions.parquet
                                              |
                                              +--> brier_backtest.py
                                              |
PJM RPM page -> rpm_history_ingest -> pjm_rpm_history.parquet
                                              |
                                              v
                                        scenarios.py
                                              |
                                              v
                                       fan_chart.py
                                              |
                                              v
                                  capacity_fan_chart.parquet + .png
                                              |
                                              v
                                       render/report.py
                                              |
                                              v
                              reports/2026-08-pjm-survival.md
```

## Non-goals for 0001

- ISOs other than PJM.
- A live dashboard.
- A Cox or AFT estimator. KM in v0; richer estimators land under a
  follow-up spec once KM is calibrated.
- Hourly capacity forecasts. Annual-clearing only.
