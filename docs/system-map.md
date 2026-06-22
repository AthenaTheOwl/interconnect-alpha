# System Map

## Data Flow

```text
tests/fixtures shape
        |
        v
scripts/build_artifacts.py
        |
        +--> data/pjm_queue_cohort_2018_2023.parquet
        +--> data/survival_distributions.parquet
        +--> data/pjm_rpm_history.parquet
        +--> data/capacity_fan_chart_2027_2030.parquet
        +--> data/capacity_fan_chart_2027_2030.svg
        |
        v
reports/2026-08-pjm-survival.md
        |
        v
python -m interconnect_alpha validate
```

## Runtime Modules

- `interconnect_alpha.cli` owns argparse and the no-flag validation command.
- `interconnect_alpha.validation` owns the artifact checks, schemas, voice
  gate, traceability gate, calibration gate, and canonical scenario lookup.
- `scripts/build_artifacts.py` regenerates the checked-in parquet fixtures and
  SVG fan chart from deterministic in-repo rows.
- `scripts/voice_lint.py` and `scripts/traceability.py` expose two focused
  gates for the factory.

## Validation Contract

The default `validate` command loads `data/scenarios.yaml`, chooses the single
scenario marked `canonical: true`, and validates the artifact set for that
scenario. Failure prints `VALIDATION_ERROR` with the check name and exits
non-zero.

