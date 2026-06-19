# InterconnectAlpha

Queue-survival and capacity-curve module. Calibrated per-project
probability-of-COD forecasts across PJM, MISO, ERCOT, CAISO, SPP.
Probabilistic capacity-market clearing-price curves conditioned on
queue-progression and load-growth scenarios. Shipped as the
analytics module inside GridSilicon.

## What this is

PJM's December 2025 capacity auction made it explicit: capacity prices
are now driven by queue throughput and data-center load, not by
legacy fundamentals. LBNL's Queued Up 2025 dataset made queue
snapshots accessible. No vendor produces calibrated capacity-curve
forecasts conditioned on queue clearing. Aurora, Wood Mac, and ICF
sell point forecasts; the differentiator is calibration.

InterconnectAlpha is the survival-model and capacity-curve module
that lives inside the GridSilicon report. The first artifact is a
PJM-only markdown report: every project in the queue with a
Kaplan-Meier survival curve to COD, a Brier-score backtest against
the 2018-2023 cohort, and a 2027-2030 capacity-price fan chart by
LDA zone.

Bucket: ai-infra. Category: ai-infra. Brand prefix: `ITA`.

## Who this is for

- Power and utility hedge funds.
- IPP developers.
- Hyperscaler PPA structurers.
- Infrastructure debt funds.
- State-PUC and FERC consultants.

## Status

v0 scaffold. No implementation yet. The first PR after the scaffold
lands the PJM queue-cohort ingest and the Kaplan-Meier estimator;
see `docs/first-pr.md`.

## How to run

Placeholder. Run commands will land in spec `0002-pjm-survival`.
The shape will be:

```powershell
uv sync
uv run ita ingest pjm-queue --cohort 2018-2023
uv run ita fit survival --estimator kaplan_meier
uv run ita backtest brier --baseline naive
uv run ita capacity ingest rpm --since 2014
uv run ita capacity fan-chart --years 2027-2030
uv run ita render report --month 2026-08
```

## Layout

```
interconnect-alpha/
  AGENTS.md
  LICENSE
  README.md
  specs/
    0001-foundation/
      requirements.md
      design.md
      tasks.md
      acceptance.md
  docs/
    first-pr.md
  src/
    survival/           # kaplan_meier.py, brier_backtest.py
    capacity/           # rpm_history_ingest.py, fan_chart.py
    render/             # report template, plots
  data/
    pjm_queue_cohort_2018_2023.parquet
  reports/              # checked-in monthly markdown
  eval/                 # calibration_metrics.py
  decisions/            # DEC-ITA-* architectural choices
```

## Relationship to GridSilicon

InterconnectAlpha is intended to live as the analytics module inside
the GridSilicon repo when both are stable. v0 ships as a standalone
repo so the survival math and the capacity-curve fitter can be
validated independently before the merge. Reports land under
`reports/` here in v0; they get folded into GridSilicon's
`reports/<year>-<month>-<iso>.md` after the merge spec ships.

## Compounds with

- GridSilicon is the parent. Long-term home of this module.
- RatepayerExposure uses the capacity-curve outputs.
- RobustSiting uses the survival distributions as a robust-opt input.

## License

MIT. See [LICENSE](LICENSE).
