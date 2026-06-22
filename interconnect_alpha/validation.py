from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared in pyproject.
    yaml = None


BANNED_FAIL = (
    "leverage",
    "demonstrate",
    "seamless",
    "cutting-edge",
    "best-in-class",
    "synergy",
)

STATUS_HEADINGS = ["Current state", "Known limits", "Next feature queue"]

REQUIRED_FILES = (
    "STATUS.md",
    "docs/product-brief.md",
    "docs/system-map.md",
    "specs/0002-design-ledger/ledger.md",
    "data/scenarios.yaml",
    "data/calibration_metrics.json",
    "data/pjm_queue_cohort_2018_2023.parquet",
    "data/survival_distributions.parquet",
    "data/pjm_rpm_history.parquet",
    "data/capacity_fan_chart_2027_2030.parquet",
    "data/capacity_fan_chart_2027_2030.svg",
    "reports/2026-08-pjm-survival.md",
    "decisions/DEC-ITA-001-survival-estimator.md",
    "decisions/DEC-ITA-002-scenario-set.md",
)

PARQUET_SCHEMAS = {
    "data/pjm_queue_cohort_2018_2023.parquet": {
        "project_id",
        "zone",
        "fuel",
        "queue_date",
        "announced_cod",
        "actual_cod",
        "status",
        "capacity_mw",
    },
    "data/survival_distributions.parquet": {
        "project_id",
        "as_of",
        "days_to_event",
        "survival_prob",
        "confidence_low",
        "confidence_high",
    },
    "data/pjm_rpm_history.parquet": {
        "auction_year",
        "delivery_year",
        "lda_zone",
        "clearing_price_mw_day",
    },
    "data/capacity_fan_chart_2027_2030.parquet": {
        "scenario",
        "delivery_year",
        "lda_zone",
        "percentile",
        "price_mw_day",
        "as_of",
    },
}


class ValidationError(Exception):
    def __init__(self, check: str, message: str) -> None:
        super().__init__(message)
        self.check = check


@dataclass(frozen=True)
class ValidationResult:
    name: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "detail": self.detail}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise ValidationError("canonical_scenario", "PyYAML is not installed")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_required_files(root: Path) -> ValidationResult:
    missing = [relative for relative in REQUIRED_FILES if not (root / relative).exists()]
    if missing:
        raise ValidationError("required_files", "missing " + ", ".join(missing))
    return ValidationResult("required_files", f"{len(REQUIRED_FILES)} files present")


def validate_status_headings(root: Path) -> ValidationResult:
    path = root / "STATUS.md"
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    if headings != STATUS_HEADINGS:
        raise ValidationError(
            "status_headings",
            f"expected {STATUS_HEADINGS}, found {headings}",
        )
    return ValidationResult("status_headings", ", ".join(headings))


def validate_canonical_scenario(root: Path) -> ValidationResult:
    payload = _read_yaml(root / "data/scenarios.yaml")
    scenarios = payload.get("scenarios", []) if isinstance(payload, dict) else []
    canonical = [row for row in scenarios if row.get("canonical") is True]
    if len(canonical) != 1:
        raise ValidationError(
            "canonical_scenario",
            f"expected exactly one canonical scenario, found {len(canonical)}",
        )
    scenario_id = canonical[0].get("id")
    if not scenario_id:
        raise ValidationError("canonical_scenario", "canonical scenario has no id")
    return ValidationResult("canonical_scenario", str(scenario_id))


def validate_parquets(root: Path) -> ValidationResult:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency is declared.
        raise ValidationError("parquet_schemas", "pyarrow is not installed") from exc

    checked: list[str] = []
    for relative, required_columns in PARQUET_SCHEMAS.items():
        table = pq.read_table(root / relative)
        columns = set(table.column_names)
        missing = sorted(required_columns - columns)
        if missing:
            raise ValidationError(
                "parquet_schemas",
                f"{relative} missing columns: {', '.join(missing)}",
            )
        if table.num_rows < 1:
            raise ValidationError("parquet_schemas", f"{relative} has no rows")
        checked.append(f"{relative}:{table.num_rows}")
    return ValidationResult("parquet_schemas", "; ".join(checked))


def validate_svg(root: Path) -> ValidationResult:
    path = root / "data/capacity_fan_chart_2027_2030.svg"
    text = path.read_text(encoding="utf-8")
    if "<svg" not in text or "</svg>" not in text:
        raise ValidationError("fan_chart_plot", "SVG root not found")
    return ValidationResult("fan_chart_plot", path.name)


def validate_report_voice(root: Path) -> ValidationResult:
    reports_dir = root / "reports"
    report_paths = sorted(reports_dir.glob("*.md"))
    if not report_paths:
        raise ValidationError("voice_lint", "no markdown reports found")

    failures: list[str] = []
    for path in report_paths:
        text = path.read_text(encoding="utf-8").lower()
        for banned in BANNED_FAIL:
            if banned in text:
                failures.append(f"{path.relative_to(root)}:{banned}")
    if failures:
        raise ValidationError("voice_lint", ", ".join(failures))
    return ValidationResult("voice_lint", f"{len(report_paths)} report checked")


def validate_traceability(root: Path) -> ValidationResult:
    report_path = root / "reports/2026-08-pjm-survival.md"
    text = report_path.read_text(encoding="utf-8")
    referenced = sorted(
        {
            token
            for token in re.findall(r"`([^`]+)`", text)
            if token.startswith("data/")
        }
    )
    if not referenced:
        raise ValidationError("traceability", "report references no data files")
    missing = [relative for relative in referenced if not (root / relative).exists()]
    if missing:
        raise ValidationError("traceability", "missing " + ", ".join(missing))
    return ValidationResult("traceability", f"{len(referenced)} data files referenced")


def validate_calibration(root: Path) -> ValidationResult:
    path = root / "data/calibration_metrics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", [])
    row_730 = next((row for row in metrics if row.get("horizon_days") == 730), None)
    if row_730 is None:
        raise ValidationError("calibration", "730-day horizon is missing")
    brier = float(row_730["brier_score"])
    naive = float(row_730["naive_brier_score"])
    if brier >= naive:
        raise ValidationError(
            "calibration",
            f"730-day Brier {brier:.3f} does not beat naive {naive:.3f}",
        )
    return ValidationResult(
        "calibration",
        f"730-day Brier {brier:.3f} beats naive {naive:.3f}",
    )


def validate_all(root: Path | None = None) -> list[ValidationResult]:
    resolved = (root or project_root()).resolve()
    return [
        validate_required_files(resolved),
        validate_status_headings(resolved),
        validate_canonical_scenario(resolved),
        validate_parquets(resolved),
        validate_svg(resolved),
        validate_report_voice(resolved),
        validate_traceability(resolved),
        validate_calibration(resolved),
    ]

