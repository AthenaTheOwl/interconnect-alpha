from __future__ import annotations

import pyarrow.parquet as pq

from interconnect_alpha.cli import main
from interconnect_alpha.model import CapexPlan, FactorScore, rank_constraints
from interconnect_alpha.scoring import write_report
from interconnect_alpha.validation import project_root, validate_all


def test_validate_default_command(capsys):
    exit_code = main(["validate"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "VALIDATION_OK canonical_scenario=base-case" in output


def test_validate_all_includes_calibration():
    results = validate_all(project_root())
    names = {result.name for result in results}

    assert "calibration" in names
    assert "traceability" in names
    assert "voice_lint" in names


def test_survival_parquet_has_fixture_rows():
    table = pq.read_table(project_root() / "data/survival_distributions.parquet")

    assert table.num_rows == 8
    assert "survival_prob" in table.column_names


def test_show_command_prints_ranked_report(capsys):
    exit_code = main(["show"])
    output = capsys.readouterr().out

    assert exit_code == 0
    # Ranked by COD probability: the gas plant already online leads, wind trails.
    # These numbers are now COMPUTED by the per-fuel Kaplan-Meier fit in
    # scripts/build_artifacts.py, not hand-typed; test_survival.py proves that.
    assert "ranked by 730-day probability of reaching COD" in output
    alpha003 = output.index("PJM-ALPHA-003")
    alpha004 = output.index("PJM-ALPHA-004")
    assert alpha003 < alpha004
    # PJM-ALPHA-003 came online 2026-05-30, before the as-of date: it counts as
    # built at full MW, and it is not the "most likely to energize" forecast.
    alpha003_line = next(line for line in output.splitlines() if line.startswith("PJM-ALPHA-003"))
    assert "100%" in alpha003_line and "observed" in alpha003_line
    assert "220 of them already online" in output
    assert "most likely to energize: PJM-ALPHA-003" not in output
    # Surfaces the capacity fan and the calibration edge, not raw JSON.
    assert "capacity-price fan" in output
    assert "beats naive" in output
    # Pin the 2027 fan prices from capacity_fan_chart_2027_2030.parquet so a
    # column swap (p10<->p90) or a shifted fixture fails here, not silently.
    assert "2027: p10 $190  p50 $244  p90 $315" in output
    # Pin the concrete computed calibration numbers and the edge sign for 730d.
    assert "Brier 0.141 beats naive 0.239 (-0.098)" in output
    # The backtest fits and scores the same rows; the line must say so.
    assert "calibration (in-sample): 730-day Brier" in output


def test_rank_constraints_returns_fixture_factor_scores():
    # Golden-master lock on the deterministic factory ranking. If the scores or
    # factor names drift, this fails instead of the numbers passing unchecked.
    scores = rank_constraints(CapexPlan("base-case", 50))

    assert scores == [
        FactorScore("queue-survival", 0.50),
        FactorScore("capacity-price-spread", 0.62),
    ]


def test_write_report_round_trips_last_score(tmp_path):
    scores = [
        FactorScore("queue-survival", 0.50),
        FactorScore("capacity-price-spread", 0.62),
    ]
    target = tmp_path / "nested" / "report.json"

    written = write_report(scores, target)

    assert written == target
    # write_report rewrites the file per score, so the file holds the last one.
    assert target.read_text(encoding="utf-8") == (
        '{"name": "capacity-price-spread", "score": 0.62}\n'
    )

