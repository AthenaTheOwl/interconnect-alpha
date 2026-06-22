# Spec 0002 design

The v0.1 system is a deterministic data-report pipeline:

- `data/scenarios.yaml` names the canonical scenario.
- `scripts/build_artifacts.py` regenerates the fixture data and fan chart.
- `interconnect_alpha.validation` checks files, voice, traceability, and
  calibration.
- `reports/2026-08-pjm-survival.md` is the readable report.
- `reports/2026-08-pjm-survival.jsonl` is the machine-readable row.

The implementation deliberately avoids live network access. Public-source ingest
is queued for the next feature pass.
