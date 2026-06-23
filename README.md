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


v0.1 shipped and runs end to end. The entry command `python -m interconnect_alpha validate` runs. See `specs/0002-design/` for the v0.1 scope and `STATUS.md` (where present) for the current state and next-feature queue.

## try it

No-arg, read-only, offline. Reads the committed PJM survival fixtures under
`data/` and prints a ranked view of which queued projects are likely to reach
commercial operation (COD):

```
python -m interconnect_alpha show
```

```
interconnect-alpha - PJM queue survival, as-of 2026-08-01 (base-case)
4 project(s), ranked by 730-day probability of reaching COD. 367 of 570 nameplate MW expected to energize.

project        zone   fuel         MW COD p(730d)   95% interval  status
PJM-ALPHA-003  EMAAC  gas        220M        92%   84%-96%    online
PJM-ALPHA-004  COMED  wind       150M        37%   28%-48%    active
most at risk: PJM-ALPHA-004 (COMED, wind, 150MW) at only 37% - 94MW of phantom queue capacity.
calibration: 730-day Brier 0.181 beats naive 0.238 (-0.057); forecasts are better than a base-rate guess.
```

The point: announced queue capacity is not energized capacity, and the ranked
COD probabilities (with a Brier backtest that beats the base rate) tell you which
megawatts to actually count on.

To check the artifacts are well-formed: `python -m interconnect_alpha validate`.

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
