# PJM Queue Survival Report - 2026-08

As of: 2026-08-01

Canonical scenario: `base-case`

## Summary

- Active and recently completed fixture projects: 4.
- Median RTO capacity-price case for 2028: $268.00/MW-day, with p10-p90 range $205.00-$346.00/MW-day.
- Calibration gate: 730-day Brier score 0.181, naive baseline 0.238, held-out folds 5.

## Project Survival

| project_id | PJM zone | 730-day COD probability | 95% interval | Backtest figure |
| --- | --- | ---: | ---: | --- |
| PJM-ALPHA-001 | PSEG | 0.59 | 0.50-0.66 | 730-day Brier 0.181 vs naive 0.238 |
| PJM-ALPHA-002 | RTO | 0.48 | 0.39-0.57 | 730-day Brier 0.181 vs naive 0.238 |
| PJM-ALPHA-003 | EMAAC | 0.92 | 0.84-0.96 | 730-day Brier 0.181 vs naive 0.238 |
| PJM-ALPHA-004 | COMED | 0.37 | 0.28-0.48 | 730-day Brier 0.181 vs naive 0.238 |

## Capacity Price Fan

| Delivery year | p10 | p50 | p90 |
| --- | ---: | ---: | ---: |
| 2027 | $190.00 | $244.00 | $315.00 |
| 2028 | $205.00 | $268.00 | $346.00 |
| 2029 | $210.00 | $274.00 | $358.00 |
| 2030 | $198.00 | $260.00 | $340.00 |

Plot: `data/capacity_fan_chart_2027_2030.svg`

## Calibration

- Held-out fold count: 5.
- 365-day Brier score: 0.154; naive baseline: 0.192.
- 730-day Brier score: 0.181; naive baseline: 0.238.
- 1460-day Brier score: 0.226; naive baseline: 0.267.
- Most recent recalibration run: 2026-08-01.

## Method

Survival rows use the schema accepted in
`decisions/DEC-ITA-001-survival-estimator.md`. Capacity scenarios use the
canonical scenario rule in `decisions/DEC-ITA-002-scenario-set.md`.

The fixture report treats `survival_prob` as probability of not reaching COD by
the horizon. The project table reports COD probability as `1 - survival_prob`
for the 730-day horizon.

## Inputs

- `data/pjm_queue_cohort_2018_2023.parquet`
- `data/survival_distributions.parquet`
- `data/pjm_rpm_history.parquet`
- `data/capacity_fan_chart_2027_2030.parquet`
- `data/calibration_metrics.json`
- `data/scenarios.yaml`

