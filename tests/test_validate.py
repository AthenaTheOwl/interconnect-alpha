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

