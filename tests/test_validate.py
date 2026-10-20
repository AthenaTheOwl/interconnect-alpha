from __future__ import annotations

import pyarrow.parquet as pq
import pytest

from interconnect_alpha.cli import main
from interconnect_alpha.model import CapexPlan, FactorScore, rank_constraints
from interconnect_alpha.scoring import write_report
from interconnect_alpha.show import rank_cohort, summarize
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
    # Ranked by COD probability within 730 days of the as-of date. These rows are
    # COMPUTED by scripts/build_artifacts.py, not hand-typed; test_survival.py
    # proves that.
    assert "ranked by probability of reaching COD within 730 days of the as-of date" in output
    lines = {line.split()[0]: line for line in output.splitlines() if line.startswith("PJM-")}
    # PJM-ALPHA-003 came online 2026-05-30, before the as-of date: it counts as
    # built at full MW, and it is not the "most likely to energize" forecast.
    assert "100%" in lines["PJM-ALPHA-003"] and "observed" in lines["PJM-ALPHA-003"]
    assert "most likely to energize: PJM-ALPHA-003" not in output
    # The active projects have waited longer than the last COD their fuel cohort
    # observed: no number, and no phantom MW invented for them.
    for pid in ("PJM-ALPHA-001", "PJM-ALPHA-002", "PJM-ALPHA-004"):
        assert "n/a" in lines[pid] and "flat tail" in lines[pid]
        assert "%" not in lines[pid]
    assert "of 570 nameplate MW: 220 already online, 0 expected from scored active projects, " \
        "350 with no supported estimate." in output
    assert "no supported estimate: PJM-ALPHA-001 (2697d in queue)" in output
    assert "phantom" not in output
    # Surfaces the capacity fan and the calibration edge, not raw JSON.
    assert "capacity-price fan" in output
    assert "beats naive" in output
    # Pin the 2027 fan prices from capacity_fan_chart_2027_2030.parquet so a
    # column swap (p10<->p90) or a shifted fixture fails here, not silently.
    assert "2027: p10 $190  p50 $244  p90 $315" in output
    # Pin the concrete computed calibration numbers and the edge sign for 730d.
    assert "Brier 0.141 beats naive 0.239 (-0.098)" in output
    # The backtest fits and scores the same rows; the line must say so, and it
    # must say which curve it scored.
    assert "calibration (in-sample): 730-day Brier" in output
    assert "for the per-fuel curve from queue entry" in output


def test_rank_cohort_scores_conditional_rows_and_leaves_flat_tail_blank():
    survival = {
        "A": {730: {"basis": "observed_cod", "age_days": 900,
                    "survival": 0.0, "low": 0.0, "high": 0.0}},
        "B": {730: {"basis": "conditional_km", "age_days": 300,
                    "survival": 0.6, "low": 0.4, "high": 0.8}},
        "C": {730: {"basis": "flat_tail", "age_days": 2500,
                    "survival": None, "low": None, "high": None}},
    }
    cohort = {pid: {"zone": "RTO", "fuel": "solar", "status": "active", "mw": 100.0}
              for pid in survival}
    rows = rank_cohort(survival, cohort, 730)

    assert [r["pid"] for r in rows] == ["A", "B", "C"]
    a, b, c = rows
    assert (a["cod_prob"], a["expected_mw"]) == (1.0, 100.0)
    assert b["cod_prob"] == pytest.approx(0.4)
    assert (b["lo"], b["hi"]) == (pytest.approx(0.2), pytest.approx(0.6))
    assert c["cod_prob"] is None and c["expected_mw"] is None and c["phantom_mw"] is None
    assert c["age_days"] == 2500

    totals = summarize(rows)
    assert totals["online_mw"] == 100.0
    assert totals["scored_mw"] == pytest.approx(40.0)
    assert totals["expected_mw"] == pytest.approx(140.0)
    assert totals["phantom_mw"] == pytest.approx(60.0)  # B only; C is not phantom
    assert totals["unsupported_mw"] == 100.0


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



def test_show_rejects_survival_parquet_without_new_columns(tmp_path, capsys):
    # A survival artifact built before `basis`/`queue_age_days` existed gets the
    # clean SHOW_ERROR exit, not a KeyError traceback.
    import shutil

    root = project_root()
    shutil.copytree(root / "data", tmp_path / "data")
    path = tmp_path / "data/survival_distributions.parquet"
    table = pq.read_table(path).drop_columns(["basis", "queue_age_days"])
    pq.write_table(table, path)

    exit_code = main(["show", "--root", str(tmp_path)])
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "SHOW_ERROR" in err
    assert "missing columns: basis, queue_age_days" in err
