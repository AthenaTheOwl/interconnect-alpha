from __future__ import annotations

import pyarrow.parquet as pq

from interconnect_alpha.cli import main
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
    # Ranked by COD probability: the gas project (92%) leads, wind (37%) trails.
    assert "ranked by 730-day probability of reaching COD" in output
    assert "PJM-ALPHA-003" in output
    assert "92%" in output
    alpha003 = output.index("PJM-ALPHA-003")
    alpha004 = output.index("PJM-ALPHA-004")
    assert alpha003 < alpha004
    # Surfaces the capacity fan and the calibration edge, not raw JSON.
    assert "capacity-price fan" in output
    assert "beats naive" in output

