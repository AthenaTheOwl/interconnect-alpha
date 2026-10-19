# PJM Queue Survival Report - 2026-08

As of: 2026-08-01

Canonical scenario: `base-case`

## Summary

- Training cohort: 76 projects across four fuels, 2018-2023 queue entries (synthetic fixture).
- Median RTO capacity-price case for 2028: $268.00/MW-day, with p10-p90 range $205.00-$346.00/MW-day.
- Calibration gate (in-sample): 730-day Brier score 0.141, naive baseline 0.239.

## Project Survival

Per-fuel Kaplan-Meier survival read at the horizon, days since queue entry. COD probability is `1 - survival_prob`; the interval is the Greenwood band. A project that reached COD by the as-of date counts as built (basis `observed_cod`): probability 1, no band, no curve.

| project_id | PJM zone | fuel | basis | 730-day COD probability | 95% interval |
| --- | --- | --- | --- | ---: | ---: |
| PJM-ALPHA-001 | PSEG | solar | km_from_entry | 0.42 | 0.20-0.64 |
| PJM-ALPHA-002 | RTO | battery | km_from_entry | 0.16 | 0.00-0.32 |
| PJM-ALPHA-003 | EMAAC | gas | observed_cod | 1.00 | observed |
| PJM-ALPHA-004 | COMED | wind | km_from_entry | 0.11 | 0.00-0.24 |

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
`decisions/DEC-ITA-001-survival-estimator.md`, now populated by a right-censored
Kaplan-Meier fit (`interconnect_alpha/kaplan_meier.py`) per fuel with Greenwood
confidence bands. The Brier backtest (`interconnect_alpha/brier_backtest.py`) scores
the per-fuel COD forecast against the overall base rate. It is an in-sample figure:
the fixture cohort is small, so the same rows are used to fit and to score. Capacity
scenarios use the canonical rule in `decisions/DEC-ITA-002-scenario-set.md`.

The report treats `survival_prob` as probability of not reaching COD by the
horizon; the project table reports COD probability as `1 - survival_prob`.

## Inputs

- `data/pjm_queue_cohort_2018_2023.parquet`
- `data/survival_distributions.parquet`
- `data/pjm_rpm_history.parquet`
- `data/capacity_fan_chart_2027_2030.parquet`
- `data/calibration_metrics.json`
- `data/scenarios.yaml`
