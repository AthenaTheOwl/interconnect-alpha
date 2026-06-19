# Tasks — 0001-foundation (interconnect-alpha)

Ordered for the first two to three PRs after this scaffold lands.

## PR 1 — cohort ingest plus Kaplan-Meier

- [ ] Add `pyproject.toml` with `lifelines`, `polars`, `pyarrow`, `numpy`, `pandas`, `matplotlib`, `pydantic`, `jsonschema`, `pyyaml`, `jinja2`, `pytest`, `ruff`.
- [ ] Add `schemas/queue-cohort.schema.json`.
- [ ] Add `schemas/survival-distribution.schema.json`.
- [ ] Add `src/ita/survival/cohort_ingest.py`.
- [ ] Add `tests/fixtures/pjm_queue_cohort_small.csv` (~30 projects).
- [ ] Add `src/ita/survival/kaplan_meier.py`.
- [ ] Add `tests/test_cohort_ingest.py` and `tests/test_kaplan_meier.py`.
- [ ] Add `scripts/validate_schemas.py`.
- [ ] Add `decisions/DEC-ITA-001-survival-estimator.md`.

## PR 2 — Brier backtest plus RPM ingest

- [ ] Add `src/ita/survival/brier_backtest.py`.
- [ ] Add `eval/calibration_metrics.py`.
- [ ] Add `src/ita/capacity/rpm_history_ingest.py`.
- [ ] Add `tests/fixtures/pjm_rpm_history_small.csv`.
- [ ] Add `schemas/capacity-fan-chart.schema.json`.
- [ ] Add `tests/test_brier_backtest.py`.
- [ ] Add `tests/test_rpm_history_ingest.py`.
- [ ] Add `decisions/DEC-ITA-002-scenario-set.md`.

## PR 3 — fan chart plus first report

- [ ] Add `src/ita/capacity/scenarios.py` plus `data/scenarios.yaml`.
- [ ] Add `src/ita/capacity/fan_chart.py`.
- [ ] Add `src/ita/render/plots.py` (matplotlib, deterministic).
- [ ] Add `src/ita/render/report.py` plus the Jinja template.
- [ ] Add `reports/2026-08-pjm-survival.md` (the first real report).
- [ ] Add `scripts/voice_lint.py` and wire as gate.
- [ ] Add `scripts/traceability.py` enforcing the input-files-exist rule.
