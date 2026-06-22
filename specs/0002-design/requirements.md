# Spec 0002 requirements

## R-ITA-002-001 - default validation

`python -m interconnect_alpha validate` must run with no flags and validate the
canonical checked-in scenario.

## R-ITA-002-002 - report artifact

The v0.1 report must include one markdown report and one JSONL summary row under
`reports/`.

## R-ITA-002-003 - fixture inputs

The report must validate all checked-in data inputs and fail if a referenced
`data/...` path is missing.

## R-ITA-002-004 - calibration check

The 730-day Brier score must beat the naive announced-COD baseline in the
checked calibration fixture.
