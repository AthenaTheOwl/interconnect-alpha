# Withdrawal as a competing event in the survival fit

Method update: October 18, 2026. Proposed experiments below are not reported as executed results.

`kaplan_meier.py` models time to commercial operation. `scripts/build_artifacts.py` codes withdrawals without energization as censored (event 0) before `kaplan_meier.py` fits the curve. Reading the complement of that survival curve as a real-world completion probability requires care: a permanent withdrawal removes the path to operation, while right censoring means the outcome is unobserved after follow-up stops. Those are different data-generating processes.

Do not silently change the shipped estimator or historical backtest to answer a different question. A proposed comparison should retain three explicit statuses: commercial operation, permanent withdrawal and still active at cutoff. Report a competing-risk cumulative-incidence estimate beside the existing per-fuel survival view (S(t) measured from queue entry), with the estimand named in each output.

The implemented refresh rejects negative or nonfinite durations, invalid event indicators, and nonpositive/nonfinite confidence multipliers. These checks guard the numerical contract. Informative censoring is still open. For the next experiment, hold out later entry cohorts, preserve the horizon and show the number of scored versus early-censored cases. An in-sample Brier score remains labeled in-sample.

## References

- https://lifelines.readthedocs.io/en/latest/fitters/univariate/AalenJohansenFitter.html
- https://scikit-learn.org/stable/modules/calibration.html
