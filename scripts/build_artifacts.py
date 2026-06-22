from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent


def write_parquets(root: Path) -> None:
    data_dir = root / "data"
    data_dir.mkdir(exist_ok=True)

    queue = pd.DataFrame(
        [
            {
                "project_id": "PJM-ALPHA-001",
                "zone": "PSEG",
                "fuel": "solar",
                "queue_date": "2019-03-14",
                "announced_cod": "2027-06-01",
                "actual_cod": "",
                "status": "active",
                "capacity_mw": 120.0,
            },
            {
                "project_id": "PJM-ALPHA-002",
                "zone": "RTO",
                "fuel": "battery",
                "queue_date": "2020-07-22",
                "announced_cod": "2027-12-01",
                "actual_cod": "",
                "status": "active",
                "capacity_mw": 80.0,
            },
            {
                "project_id": "PJM-ALPHA-003",
                "zone": "EMAAC",
                "fuel": "gas",
                "queue_date": "2018-11-02",
                "announced_cod": "2026-11-15",
                "actual_cod": "2026-05-30",
                "status": "online",
                "capacity_mw": 220.0,
            },
            {
                "project_id": "PJM-ALPHA-004",
                "zone": "COMED",
                "fuel": "wind",
                "queue_date": "2021-02-18",
                "announced_cod": "2028-05-01",
                "actual_cod": "",
                "status": "active",
                "capacity_mw": 150.0,
            },
        ]
    )
    queue.to_parquet(data_dir / "pjm_queue_cohort_2018_2023.parquet", index=False)

    survival = pd.DataFrame(
        [
            ["PJM-ALPHA-001", "2026-08-01", 365, 0.62, 0.54, 0.70],
            ["PJM-ALPHA-001", "2026-08-01", 730, 0.41, 0.34, 0.50],
            ["PJM-ALPHA-002", "2026-08-01", 365, 0.74, 0.66, 0.81],
            ["PJM-ALPHA-002", "2026-08-01", 730, 0.52, 0.43, 0.61],
            ["PJM-ALPHA-003", "2026-08-01", 365, 0.18, 0.12, 0.27],
            ["PJM-ALPHA-003", "2026-08-01", 730, 0.08, 0.04, 0.16],
            ["PJM-ALPHA-004", "2026-08-01", 365, 0.81, 0.73, 0.88],
            ["PJM-ALPHA-004", "2026-08-01", 730, 0.63, 0.52, 0.72],
        ],
        columns=[
            "project_id",
            "as_of",
            "days_to_event",
            "survival_prob",
            "confidence_low",
            "confidence_high",
        ],
    )
    survival.to_parquet(data_dir / "survival_distributions.parquet", index=False)

    rpm = pd.DataFrame(
        [
            [2023, 2026, "RTO", 28.92],
            [2023, 2026, "EMAAC", 49.49],
            [2024, 2027, "RTO", 269.92],
            [2024, 2027, "PSEG", 280.75],
            [2025, 2028, "RTO", 312.50],
            [2025, 2028, "COMED", 297.10],
        ],
        columns=["auction_year", "delivery_year", "lda_zone", "clearing_price_mw_day"],
    )
    rpm.to_parquet(data_dir / "pjm_rpm_history.parquet", index=False)

    fan = pd.DataFrame(
        [
            ["base-case", 2027, "RTO", 10, 190.0, "2026-08-01"],
            ["base-case", 2027, "RTO", 50, 244.0, "2026-08-01"],
            ["base-case", 2027, "RTO", 90, 315.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 10, 205.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 50, 268.0, "2026-08-01"],
            ["base-case", 2028, "RTO", 90, 346.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 10, 210.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 50, 274.0, "2026-08-01"],
            ["base-case", 2029, "RTO", 90, 358.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 10, 198.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 50, 260.0, "2026-08-01"],
            ["base-case", 2030, "RTO", 90, 340.0, "2026-08-01"],
        ],
        columns=[
            "scenario",
            "delivery_year",
            "lda_zone",
            "percentile",
            "price_mw_day",
            "as_of",
        ],
    )
    fan.to_parquet(data_dir / "capacity_fan_chart_2027_2030.parquet", index=False)


def write_svg(root: Path) -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420" viewBox="0 0 720 420" role="img" aria-label="PJM RTO capacity-price fan chart 2027 to 2030">
  <rect width="720" height="420" fill="#ffffff"/>
  <text x="48" y="42" font-family="Arial" font-size="20" fill="#1f2937">PJM RTO capacity-price fan chart</text>
  <text x="48" y="66" font-family="Arial" font-size="13" fill="#4b5563">base-case, dollars per MW-day</text>
  <line x1="72" y1="348" x2="660" y2="348" stroke="#111827" stroke-width="1"/>
  <line x1="72" y1="92" x2="72" y2="348" stroke="#111827" stroke-width="1"/>
  <text x="52" y="352" font-family="Arial" font-size="11" fill="#374151">0</text>
  <text x="42" y="232" font-family="Arial" font-size="11" fill="#374151">200</text>
  <text x="42" y="108" font-family="Arial" font-size="11" fill="#374151">400</text>
  <polygon points="120,226 280,206 440,198 600,210 600,130 440,118 280,130 120,154" fill="#c7d2fe" opacity="0.85"/>
  <polyline points="120,181 280,162 440,158 600,169" fill="none" stroke="#1d4ed8" stroke-width="3"/>
  <polyline points="120,226 280,206 440,198 600,210" fill="none" stroke="#4338ca" stroke-width="1.5"/>
  <polyline points="120,154 280,130 440,118 600,130" fill="none" stroke="#4338ca" stroke-width="1.5"/>
  <text x="110" y="372" font-family="Arial" font-size="12" fill="#374151">2027</text>
  <text x="270" y="372" font-family="Arial" font-size="12" fill="#374151">2028</text>
  <text x="430" y="372" font-family="Arial" font-size="12" fill="#374151">2029</text>
  <text x="590" y="372" font-family="Arial" font-size="12" fill="#374151">2030</text>
  <text x="520" y="93" font-family="Arial" font-size="12" fill="#4338ca">p10-p90</text>
  <text x="520" y="113" font-family="Arial" font-size="12" fill="#1d4ed8">median</text>
</svg>
"""
    (root / "data/capacity_fan_chart_2027_2030.svg").write_text(
        svg,
        encoding="utf-8",
    )


def main() -> int:
    write_parquets(ROOT)
    write_svg(ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

