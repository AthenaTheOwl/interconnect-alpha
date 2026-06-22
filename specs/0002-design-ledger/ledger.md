# 0002 Design Ledger

Status: accepted for v0.1 implementation.

## Purpose

This ledger records the v0.1 decisions needed to turn the scaffold into a
usable data-report repo. It does not replace the broader 0001 foundation spec;
it narrows the first shipped artifact to a deterministic, checked-in PJM report.

## Decisions

| ID | Decision | Files | Acceptance check |
| --- | --- | --- | --- |
| D-ITA-002-001 | The promised first user action is `python -m interconnect_alpha validate`. | `interconnect_alpha/cli.py`, `interconnect_alpha/__main__.py` | Command exits 0 with no flags. |
| D-ITA-002-002 | The canonical v0.1 scenario is declared in `data/scenarios.yaml`. | `data/scenarios.yaml` | Exactly one scenario has `canonical: true`. |
| D-ITA-002-003 | Fixture parquets are checked in so the report can be validated without network access. | `data/*.parquet` | Required parquet files exist and have expected columns. |
| D-ITA-002-004 | Calibration acceptance uses the 730-day Brier score against the naive announced-COD baseline. | `data/calibration_metrics.json` | `brier_score < naive_brier_score` at 730 days. |
| D-ITA-002-005 | The fan chart is an SVG in v0.1 because the local environment does not require a plotting backend. | `data/capacity_fan_chart_2027_2030.svg` | File exists and contains an SVG root. |
| D-ITA-002-006 | Report traceability is literal: every backticked `data/...` path in the report must exist. | `reports/2026-08-pjm-survival.md` | Traceability check exits 0. |

## Open Follow-ups

- Replace fixture rows with public-source ingest outputs.
- Add richer estimators after the Kaplan-Meier baseline is calibrated on the full cohort.
- Add PNG rendering if the project standard requires raster report plots.

