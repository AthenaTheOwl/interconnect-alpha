# Interconnect Alpha Status

## Current state

- v0.1 ships a checked-in PJM report for 2026-08 with fixture parquet inputs and a deterministic SVG fan chart.
- `python -m interconnect_alpha validate` runs with no flags and checks canonical scenario selection, report voice, parquet schemas, traceability, calibration, and required files.
- The product brief, system map, and 0002 design ledger are present for the next implementation pass.

## Known limits

- Fixture data is small and public-source shaped; it is not a full LBNL or PJM RPM ingest.
- The capacity fan chart is deterministic scenario output, not a full Monte Carlo sampler.
- Validation covers the v0.1 artifact contract; it does not prove production calibration on the full 2018-2023 cohort.

## Next feature queue

- Replace fixture parquet generation with a public LBNL Queued Up cohort ingest.
- Add RPM history ingest from checked public PJM auction-result files.
- Add Kaplan-Meier fitting over the full cohort and store per-project survival rows.
- Add deterministic PNG rendering once the plotting dependency is installed in the project environment.

