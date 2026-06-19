# First PR — interconnect-alpha

The literal first PR after the scaffold. Narrow scope: cohort
ingest, the Kaplan-Meier estimator wrapper, and the survival
schemas.

## Title

`feat(ITA): PJM queue cohort ingest plus Kaplan-Meier estimator (PR 1)`

## Goal

Land the cohort ingest, the typed survival-distribution output, and
the Kaplan-Meier wrapper that produces it. The Brier backtest, the
RPM ingest, and the fan chart arrive in later PRs.

## Files added

- `pyproject.toml` — deps: `lifelines`, `polars`, `pyarrow`,
  `numpy`, `pandas`, `matplotlib`, `pydantic`, `jsonschema`,
  `pyyaml`, `jinja2`, `pytest`, `ruff`.
- `src/ita/__init__.py`
- `src/ita/survival/__init__.py`
- `src/ita/survival/cohort_ingest.py` — reads the LBNL Queued Up
  PJM 2018-2023 CSV export, normalizes column names, writes
  `data/pjm_queue_cohort_2018_2023.parquet`.
- `src/ita/survival/kaplan_meier.py` — thin wrapper over
  `lifelines.KaplanMeierFitter`. Inputs a cohort parquet plus a list
  of project IDs; outputs a survival-distribution parquet with
  `project_id`, `as_of`, `days_to_event`, `survival_prob`,
  `confidence_low`, `confidence_high`.
- `schemas/queue-cohort.schema.json`.
- `schemas/survival-distribution.schema.json`.
- `tests/fixtures/pjm_queue_cohort_small.csv` — thirty projects,
  hand-curated, covering both energized and withdrawn outcomes.
- `tests/test_cohort_ingest.py` — round-trips the fixture, asserts
  column types and row count.
- `tests/test_kaplan_meier.py` — fits the estimator on the fixture,
  asserts survival probabilities sit in [0, 1], and that confidence
  bounds bracket the point estimate.
- `tests/test_schemas_self.py` — validates each schema against
  JSON Schema 2020-12.
- `scripts/validate_schemas.py` — walks `schemas/` plus any
  `data/*.parquet` and exits 1 on mismatch.
- `decisions/DEC-ITA-001-survival-estimator.md` — names KM as the
  v0 estimator, the reasons, and the alternatives (Cox, AFT) held
  for a follow-up spec.

## Files not in this PR

- The Brier backtest. PR 2.
- The RPM history ingest. PR 2.
- The fan chart. PR 3.
- The first report. PR 3.
- The deterministic plot renderer. PR 3.
- Any CI workflow.

## Verification

Reviewer runs:

```powershell
uv sync
uv run pytest
uv run python scripts/validate_schemas.py
```

Expected: all tests pass; `validate_schemas.py` exits 0.

## Review checklist

- [ ] Cohort ingest does not silently drop rows; missing values are
      either imputed under a named rule or rejected with a log line.
- [ ] The KM wrapper exposes a `fit(...)` plus `survival_curve(...)`
      surface that is independent of the underlying estimator
      library, so a Cox or AFT swap later is mechanical.
- [ ] Both schemas declare `$id` and `$schema`.
- [ ] No marketing words in any added markdown.

## After merge

PR 2 lands the Brier-score backtest at horizons 365, 730, 1460 days
plus the PJM RPM history ingest. PR 3 ships the fan chart, the
deterministic plot renderer, and the first
`reports/2026-08-pjm-survival.md` report.
