# AGENTS.md — interconnect-alpha

Operating contract for AI agents (Claude, Codex, Cursor) working in
this repo. Conventions match the AthenaTheOwl portfolio so an agent
already trained on `grid-silicon` or `semiconductor-wafer-robust-optimization`
recognizes the shape.

## What this repo is

A small survival-modeling and capacity-curve module. The artifact is
the PJM monthly report under `reports/`, the per-project survival
distributions as parquet, and the capacity-price fan chart as a
deterministic plot. The math is the moat; the report renders are
deliberately spartan.

## Voice constraints

- No marketing words. The banned set will live in
  `scripts/voice_lint.py::BANNED_FAIL` once the lint script lands in
  spec 0002. Examples that always fail: leverage, demonstrate, seamless,
  cutting-edge, best-in-class, synergy.
- No antithetical reversals as a structural device.
- Plain assertions. Every probability is a number with a confidence
  interval and a backtested calibration figure attached.

## Gates

Will land in spec `0002-pjm-survival`. The intended chain:

- `voice_lint` on every report.
- `validate_schemas` on the survival-distribution parquet and the
  capacity-curve parquet.
- `calibration_metrics`: Brier score on the held-out cohort must
  beat the naive (announced-as-COD) baseline. Both numbers print
  in the same run.
- `traceability`: every input file referenced by the report must
  exist on disk at report-render time.

## Out of scope

- ISOs other than PJM in v0. MISO, ERCOT, CAISO, SPP arrive under
  their own specs once the PJM module is calibrated.
- A live dashboard. Monthly cadence.
- Hyperscaler-NDA channel checks. Public sources only.
- A REST API. Consumers read the parquet directly.
