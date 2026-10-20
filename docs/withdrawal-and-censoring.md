# Withdrawal as a competing event in the survival fit

Method update: October 18, 2026. Proposed experiments below are not reported as executed results.

`kaplan_meier.py` models time to commercial operation. `scripts/build_artifacts.py` codes withdrawals without energization as censored (event 0) at the cohort's `withdrawal_date` before `kaplan_meier.py` fits the curve. Reading the complement of that survival curve as a real-world completion probability requires care: a permanent withdrawal removes the path to operation, while right censoring means the outcome is unobserved after follow-up stops. Those are different data-generating processes.

Do not silently change the shipped estimator or historical backtest to answer a different question. A proposed comparison should retain three explicit statuses: commercial operation, permanent withdrawal and still active at cutoff. Report a competing-risk cumulative-incidence estimate beside the existing per-fuel survival view (S(t) measured from queue entry), with the estimand named in each output.

The implemented refresh rejects negative or nonfinite durations, invalid event indicators, and nonpositive/nonfinite confidence multipliers. These checks guard the numerical contract. Informative censoring is still open. For the next experiment, hold out later entry cohorts, preserve the horizon and show the number of scored versus early-censored cases. An in-sample Brier score remains labeled in-sample.

## What censoring assumes, and what a competing-risks fit would change

Censoring a withdrawn project at its withdrawal date tells the estimator that, had the project stayed, it would have carried the same COD hazard as the projects still in the queue at that age. A withdrawal ends the path to COD instead. So `1 - S(t)` from the shipped fit is the chance of COD by `t` in a queue where nobody withdraws, and it overstates the observed-world chance whenever withdrawals land before `t`.

A competing-risks fit keeps the three outcomes apart (COD, withdrawal, still active at the cutoff) and estimates the cumulative incidence of COD with the Aalen-Johansen estimator: `F_COD(t)` is the sum, over COD times `t_j <= t`, of `S_any(t_j-) * d_j / n_j`, where `S_any` is the Kaplan-Meier curve for leaving the queue by either route, `d_j` the CODs at `t_j` and `n_j` the projects at risk. Switching would change four things:

- Per-fuel COD probabilities. `F_COD(t) <= 1 - S(t)` at every `t`, with equality when no withdrawal precedes `t`. Fuels with early withdrawals move most; a fuel with none does not move. In the shipped fixture every withdrawal lands 1,016 days or more after queue entry, so the 730-day column of the report's fuel-curve table would not change for any fuel. The withdrawn counts in that table (gas has none) only matter at longer horizons.
- The conditional view. An active project of age `a` would get COD probability `(F_COD(a + h) - F_COD(a)) / S_any(a)` in place of `1 - S(a + h) / S(a)`.
- The Brier backtest. A project that withdrew before the horizon has a known outcome (no COD by then). It would be scored as 0; today it is dropped as undetermined. `n_scored` rises at any horizon later than a withdrawal. In the shipped fixture no withdrawal precedes day 730, so the 365- and 730-day scores would not change; only the 1,460-day score would, with `n_scored` going from 65 to 72.
- Nothing about the flat-tail limit. Past the last COD a fuel cohort observed there is still no COD increment to condition on, so those projects still get no estimate.

The shipped code fits Kaplan-Meier only; no Aalen-Johansen estimate is computed or reported.

## References

- https://lifelines.readthedocs.io/en/latest/fitters/univariate/AalenJohansenFitter.html
- https://scikit-learn.org/stable/modules/calibration.html
