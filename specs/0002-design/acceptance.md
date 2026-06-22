# Spec 0002 acceptance

The v0.1 release is accepted when:

- `python -m interconnect_alpha validate` exits 0 with no flags.
- `python -m pytest -q` passes.
- `PRODUCT_BRIEF.md`, `SYSTEM_MAP.md`, `STATUS.md`, `README.md`,
  `pyproject.toml`, and `specs/0002-design/` exist.
- `reports/2026-08-pjm-survival.jsonl` exists and names the checked report.
