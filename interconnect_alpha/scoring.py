"""Compatibility report surface for the active-MVP factory contract."""

from __future__ import annotations

import json
from pathlib import Path

from interconnect_alpha.model import FactorScore


def write_report(scores: list[FactorScore], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    for score in scores:
        path.write_text(json.dumps(score.__dict__, sort_keys=True) + "\n", encoding="utf-8")
    return path
