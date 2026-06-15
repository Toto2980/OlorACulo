from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.group import TeamRecord, simulate_group


@dataclass
class GroupStageResult:
    standings: dict[str, list[TeamRecord]]
    advancing: set[str]
    best_thirds: list[TeamRecord]


def simulate_group_stage(
    model, config: WorldCupConfig, rng: np.random.Generator
) -> GroupStageResult:
    """Simula los 12 grupos; avanzan 1º y 2º de cada uno + los 8 mejores terceros."""
    standings: dict[str, list[TeamRecord]] = {}
    advancing: set[str] = set()
    thirds: list[TeamRecord] = []

    for group, teams in config.groups.items():
        ranked = simulate_group(model, teams, rng)
        standings[group] = ranked
        advancing.add(ranked[0].team)
        advancing.add(ranked[1].team)
        thirds.append(ranked[2])

    best_thirds = sorted(
        thirds,
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, rng.random()),
    )[:8]
    for record in best_thirds:
        advancing.add(record.team)

    return GroupStageResult(standings=standings, advancing=advancing, best_thirds=best_thirds)
