# Interconnect Alpha Status

## Current state

- v0.1 ships a checked-in PJM report for 2026-08 with fixture parquet inputs and a deterministic SVG fan chart.
- Survival numbers are now computed, not hand-typed: `interconnect_alpha/kaplan_meier.py` fits a right-censored Kaplan-Meier curve per fuel with Greenwood confidence bands, and `interconnect_alpha/brier_backtest.py` scores the COD forecast against the naive base-rate baseline. `scripts/build_artifacts.py` fits both over the cohort and regenerates every `data/` artifact; nothing in `survival_distributions.parquet` or `calibration_metrics.json` is a literal.
- `python -m interconnect_alpha validate` runs with no flags and checks canonical scenario selection, report voice, parquet schemas, traceability, calibration, and required files.
- The product brief, system map, and 0002 design ledger are present for the next implementation pass.

## Known limits

- The training cohort is a small synthetic fixture (deterministic seeded draw shaped like public PJM/LBNL "Queued Up" data), not a real LBNL or PJM RPM ingest. Its fuel timescales are compressed and illustrative.
- The Brier backtest is **in-sample**: the cohort is too small to hold out a credible earlier fold, so the same rows fit and score the curve. The reported edge measures whether conditioning on fuel type beats a single base-rate guess, not out-of-sample generalisation. `held_out_fold_count` (an unearned claim in earlier fixtures) has been removed.
- Per-project rows condition the fuel class's KM curve on days already spent in the queue, and the horizon counts days after the as-of date. Fuel is the only stratum. A project that reached COD by the as-of date counts as built. A project gets no estimate (`flat_tail`) when its fuel curve cannot back the window `(age, age + h]`: it is older than the last COD its fuel cohort observed, or the window holds no COD, or the window's CODs exhaust the risk set and would leave a 0-0 band. No minimum at-risk count is enforced beyond that; a thin risk set shows as a wide Greenwood band. In the shipped fixture all three active display projects are past the last COD, because the cohort's timescales are compressed and its last solar, battery and wind CODs land more than a year short of those projects' ages (see the fuel-curve table in the report).
- Withdrawn projects are right-censored at their `withdrawal_date`, which treats withdrawal as uninformative about COD. `1 - S(t)` is therefore the chance of COD in a queue with no withdrawals; the competing-risks (Aalen-Johansen) cumulative incidence never exceeds it and falls below it for fuels with early withdrawals. See `docs/withdrawal-and-censoring.md`.
- The capacity fan chart is deterministic scenario output, not a full Monte Carlo sampler, and remains out of scope for the survival estimator.

## Next feature queue

- Replace the synthetic cohort with a public LBNL Queued Up ingest and relabel the Brier backtest as held-out once a real earlier fold exists.
- Add RPM history ingest from checked public PJM auction-result files.
- Stratify the Kaplan-Meier fit on more than fuel (zone, vintage) once the cohort is large enough to support it.
- Add deterministic PNG rendering once the plotting dependency is installed in the project environment.

