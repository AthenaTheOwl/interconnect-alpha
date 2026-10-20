# PJM Queue Survival Report - 2026-08

As of: 2026-08-01

Canonical scenario: `base-case`

## Summary

- Training cohort: 76 projects across four fuels, 2018-2023 queue entries (synthetic fixture).
- Display projects: 570 nameplate MW. 220 MW already online; no active project has a supported estimate; 350 MW sit in active projects their fuel curve cannot score (basis `flat_tail`), with no estimate.
- Median RTO capacity-price case for 2028: $268.00/MW-day, with p10-p90 range $205.00-$346.00/MW-day.
- Calibration gate (in-sample): 730-day Brier score 0.141, naive baseline 0.239.

## Project Survival

Each active project reads its fuel's Kaplan-Meier curve conditional on the days it has already spent in the queue at the as-of date: `S(age + h) / S(age)`, with the Greenwood band over `(age, age + h]`. The horizon `h` counts days after the as-of date. COD probability is `1 - survival_prob`. A project that reached COD by the as-of date counts as built (basis `observed_cod`): probability 1, no band, no curve. An active project older than the last COD its fuel cohort observed sits on the flat tail of the curve, where there are no events to condition on (basis `flat_tail`): no estimate. The same holds when the window `(age, age + h]` holds no COD, or holds only CODs that exhaust the risk set and leave a 0-0 band.

| project_id | PJM zone | fuel | days in queue | basis | 730-day COD probability | 95% interval |
| --- | --- | --- | ---: | --- | ---: | ---: |
| PJM-ALPHA-001 | PSEG | solar | 2697 | flat_tail | n/a | n/a |
| PJM-ALPHA-002 | RTO | battery | 2201 | flat_tail | n/a | n/a |
| PJM-ALPHA-003 | EMAAC | gas | 2829 | observed_cod | 1.00 | observed |
| PJM-ALPHA-004 | COMED | wind | 1990 | flat_tail | n/a | n/a |

### Fuel curves

The per-fuel curves the rows above are read from, measured from queue entry. Withdrawn projects are right-censored at their withdrawal date (see `docs/withdrawal-and-censoring.md`). The 730-day column is the forecast the Brier backtest scores.

| fuel | projects | reached COD | withdrawn | last observed COD (days from entry) | 730-day COD probability from entry |
| --- | ---: | ---: | ---: | ---: | ---: |
| battery | 19 | 11 | 4 | 1391 | 0.16 |
| gas | 19 | 18 | 0 | 2766 | 0.89 |
| solar | 19 | 15 | 1 | 1332 | 0.42 |
| wind | 19 | 7 | 3 | 1551 | 0.11 |

## Capacity Price Fan

| Delivery year | p10 | p50 | p90 |
| --- | ---: | ---: | ---: |
| 2027 | $190.00 | $244.00 | $315.00 |
| 2028 | $205.00 | $268.00 | $346.00 |
| 2029 | $210.00 | $274.00 | $358.00 |
| 2030 | $198.00 | $260.00 | $340.00 |

Plot: `data/capacity_fan_chart_2027_2030.svg`

## Calibration

- Evaluation: in-sample (per-fuel KM vs naive base-rate baseline).
- 365-day Brier score: 0.049; naive baseline: 0.061; scored on 76 projects.
- 730-day Brier score: 0.141; naive baseline: 0.239; scored on 76 projects.
- 1460-day Brier score: 0.171; naive baseline: 0.186; scored on 65 projects.
- Most recent recalibration run: 2026-08-01.

## Method

Survival rows use the schema accepted in
`decisions/DEC-ITA-001-survival-estimator.md` plus its `basis` and `queue_age_days`
columns, populated by a right-censored Kaplan-Meier fit
(`interconnect_alpha/kaplan_meier.py`) per fuel with Greenwood confidence bands. The
Brier backtest (`interconnect_alpha/brier_backtest.py`) scores the per-fuel COD
forecast from queue entry against the overall base rate. It is an in-sample figure:
the fixture cohort is small, so the same rows are used to fit and to score. Capacity
scenarios use the canonical rule in `decisions/DEC-ITA-002-scenario-set.md`.

The report treats `survival_prob` as probability of not reaching COD within
`days_to_event` days after the as-of date; the project table reports COD probability
as `1 - survival_prob`.

## Inputs

- `data/pjm_queue_cohort_2018_2023.parquet`
- `data/survival_distributions.parquet`
- `data/pjm_rpm_history.parquet`
- `data/capacity_fan_chart_2027_2030.parquet`
- `data/calibration_metrics.json`
- `data/scenarios.yaml`
