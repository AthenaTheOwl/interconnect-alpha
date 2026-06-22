# Product Brief

## Product

Interconnect Alpha v0.1 is a local data-report repo for PJM queue survival
and capacity-price scenario analysis. The first user action is:

```powershell
python -m interconnect_alpha validate
```

That command uses the checked-in `base-case` scenario and validates the
current report artifact without extra flags.

## User

- Power and utility investors who need queue-throughput probabilities.
- IPP developers comparing project timing risk across PJM zones.
- Infrastructure lenders checking whether capacity-price cases depend on
specific queue-clearing assumptions.
- Public-sector analysts who need reproducible inputs and readable methods.

## v0.1 Artifact

- `reports/2026-08-pjm-survival.md`
- `data/pjm_queue_cohort_2018_2023.parquet`
- `data/survival_distributions.parquet`
- `data/pjm_rpm_history.parquet`
- `data/capacity_fan_chart_2027_2030.parquet`
- `data/capacity_fan_chart_2027_2030.svg`

## Quality Bar

- Every report input is named and must exist on disk.
- The Brier score at the 730-day horizon must beat the naive baseline.
- Report text avoids the banned voice list in `interconnect_alpha.validation`.
- `STATUS.md` keeps the exact section headings required by the factory gate.

