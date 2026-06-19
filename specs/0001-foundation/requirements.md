# Requirements — 0001-foundation (interconnect-alpha)

Brand prefix: `ITA`.

## Scope

The foundation spec names the queue-cohort ingest, the survival
estimator, the capacity-curve ingest, the fan-chart fitter, and the
calibration discipline that v0 must respect.

## Requirements

- R-ITA-001: The repo ingests the PJM 2018-2023 queue cohort from
  LBNL's Queued Up dataset and persists it at
  `data/pjm_queue_cohort_2018_2023.parquet`. The parquet schema is
  declared at `schemas/queue-cohort.schema.json`.
- R-ITA-002: A Kaplan-Meier survival estimator fits per-project
  survival curves to COD. The output parquet shape carries
  `project_id`, `as_of`, `days_to_event`, `survival_prob`,
  `confidence_low`, `confidence_high`.
- R-ITA-003: A Brier-score backtest at horizons {365, 730, 1460}
  days runs against held-out cohort folds. The Brier score must
  beat a naive announced-as-COD baseline. Both numbers print in the
  same run.
- R-ITA-004: A capacity-market RPM history ingest pulls the public
  PJM Reliability Pricing Model auction results since 2014 and
  persists them at `data/pjm_rpm_history.parquet`.
- R-ITA-005: A fan-chart fitter produces a probabilistic 2027-2030
  capacity-price forecast by LDA zone, conditioned on a small set
  of queue-clearing and load-growth scenarios.
- R-ITA-006: The PJM-only monthly report at
  `reports/YYYY-MM-pjm-survival.md` contains: per-project survival
  curves for the active queue, the Brier-score backtest figures, the
  fan-chart plot, and a methodology section linking to the decision
  records.
- R-ITA-007: The report includes a `## Calibration` section that
  prints the Brier score, the baseline Brier score, the held-out
  fold count, and the date of the most recent recalibration run.
- R-ITA-008: All scenarios named in the fan chart are declared in
  a checked-in YAML at `data/scenarios.yaml` with a documented set
  of input perturbations.
- R-ITA-009: A `voice_lint` pass runs against every checked-in
  report.
- R-ITA-010: Decision records live under `decisions/DEC-ITA-NNN.md`.
  The first is `DEC-ITA-001-survival-estimator.md`.
- R-ITA-011: The capacity-price plot is reproducible: running the
  fan-chart command twice on the same inputs produces a
  byte-identical PNG (modulo embedded timestamp, which is fixed
  via `--as-of`).
- R-ITA-012: This repo does not call any private API or scraped
  source that violates a publisher's terms.
