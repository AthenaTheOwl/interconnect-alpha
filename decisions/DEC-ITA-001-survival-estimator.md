# DEC-ITA-001: Survival Estimator

Status: accepted for v0.1.

## Decision

Use Kaplan-Meier-style survival rows as the v0.1 output shape. The checked-in
artifact stores project-level survival probability by horizon with confidence
bounds:

- `project_id`
- `as_of`
- `days_to_event`
- `survival_prob`
- `confidence_low`
- `confidence_high`

## Rationale

The estimator shape is simple enough to audit from a report and stable enough
to feed capacity-price scenarios. It also keeps censoring explicit for projects
that remain active at report time.

## Consequences

- The full ingest and estimator can replace fixture rows without changing the
  report schema.
- Cox and AFT estimators remain out of scope until the baseline calibration run
  is available on the full cohort.

