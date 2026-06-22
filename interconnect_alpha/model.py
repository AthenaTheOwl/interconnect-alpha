"""Compatibility model surface for the active-MVP factory contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapexPlan:
    scenario_id: str
    queue_projects: int


@dataclass(frozen=True)
class FactorScore:
    name: str
    score: float


def rank_constraints(plan: CapexPlan) -> list[FactorScore]:
    """Return a small deterministic constraint ranking for the fixture report."""

    return [
        FactorScore("queue-survival", min(1.0, plan.queue_projects / 100.0)),
        FactorScore("capacity-price-spread", 0.62),
    ]
