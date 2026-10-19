# DEC-ITA-001: Survival Estimator

Status: accepted for v0.1; estimator implemented (previously the rows were
hand-typed literals — see Implementation note).

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

## Implementation note

The v0.1 shape shipped first with the survival probabilities, confidence bounds,
and Brier metrics typed in as literals — no estimator behind them. That is now
fixed. `interconnect_alpha/kaplan_meier.py` computes the product-limit estimator
with right-censoring and a Greenwood confidence band; `interconnect_alpha/brier_backtest.py`
computes the Brier backtest of the per-fuel COD forecast against the naive
base-rate baseline. `scripts/build_artifacts.py` fits both over the queue cohort
and writes `survival_distributions.parquet` and `calibration_metrics.json` from
the fitted output, so the numbers move when the cohort moves. The schema in the
Decision section is unchanged, so `show`/`validate` and downstream consumers keep
working.

The backtest is labelled in-sample because the shipped cohort is a small
synthetic fixture; the earlier `held_out_fold_count: 5` claim was unearned and has
been removed. See STATUS.md "Known limits".

## Consequences

- The full ingest can replace the synthetic cohort without changing the report
  schema; the estimator already computes from whatever cohort is supplied.
- Cox and AFT estimators remain out of scope until a held-out calibration run is
  available on a real, larger cohort.

## Amendment (2026-10-19)

The survival rows gained two columns, and `days_to_event` changed its reference
point. The six columns above are still present.

- `basis`: `observed_cod` (COD on or before `as_of`; survival 0, no band),
  `conditional_km` (active; the fuel curve conditional on days already in the
  queue), or `flat_tail` (active and older than the last COD its fuel cohort
  observed; survival and band are null, because the curve has no events there).
- `queue_age_days`: days from queue entry to `as_of`.
- `days_to_event` counts days after `as_of`. For `conditional_km` rows
  `survival_prob` is `S(queue_age_days + days_to_event) / S(queue_age_days)`.
  Before this amendment it counted days since queue entry and every row read the
  unconditional fuel curve, including a project already online.
