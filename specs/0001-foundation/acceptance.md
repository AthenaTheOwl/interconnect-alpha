# Acceptance — 0001-foundation (interconnect-alpha)

v0 is done when the following commands all succeed on a clean clone.

## Commands

```powershell
uv sync
uv run ita ingest pjm-queue --source tests/fixtures/pjm_queue_cohort_small.csv
uv run ita fit survival --estimator kaplan_meier
uv run ita backtest brier --horizons 365,730,1460 --folds 5
uv run ita capacity ingest rpm --source tests/fixtures/pjm_rpm_history_small.csv
uv run ita capacity fan-chart --years 2027-2030 --as-of 2026-08-01
uv run ita render report --month 2026-08
uv run python eval/calibration_metrics.py
uv run pytest
uv run python scripts/validate_schemas.py
uv run python scripts/voice_lint.py
uv run python scripts/traceability.py
```

## Gates that must pass

- All tests pass under `pytest`.
- `validate_schemas.py` exits 0 against the survival-distribution
  parquet and the capacity-fan-chart parquet.
- `voice_lint.py` exits 0 against
  `reports/2026-08-pjm-survival.md`.
- `traceability.py` exits 0: every input parquet referenced in the
  report exists on disk.
- `calibration_metrics.py` prints a Brier score strictly lower than
  the naive announced-as-COD baseline at the 730-day horizon. Both
  numbers print in the same run.

## Artifacts produced

- `data/pjm_queue_cohort_2018_2023.parquet` validates against the
  queue-cohort schema.
- `data/survival_distributions.parquet` validates against the
  survival-distribution schema.
- `data/pjm_rpm_history.parquet` is present.
- `data/capacity_fan_chart_2027_2030.parquet` plus the deterministic
  PNG are present and reproducible across two runs.
- `reports/2026-08-pjm-survival.md` exists and lints clean.
- `decisions/DEC-ITA-001-survival-estimator.md` and
  `decisions/DEC-ITA-002-scenario-set.md` are present and linked
  from the report.

## What v0 explicitly does not promise

- Coverage of ISOs other than PJM.
- A Cox or AFT survival estimator — KM only in v0.
- An hourly capacity forecast.
- A live dashboard.
- A REST API.
