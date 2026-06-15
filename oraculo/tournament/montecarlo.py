from __future__ import annotations

import numpy as np

from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage

_POSITIONS = ("1st", "2nd", "3rd", "4th")


def run_group_stage_mc(
    model, config: WorldCupConfig, *, n_iter: int
) -> dict[str, dict[str, float]]:
    """Corre n_iter simulaciones de la fase de grupos (semilla fija desde config.seed)
    y devuelve, por equipo, las probabilidades de cada posición y de avanzar."""
    rng = np.random.default_rng(config.seed)
    counts = {
        team: {"1st": 0, "2nd": 0, "3rd": 0, "4th": 0, "advance": 0}
        for team in config.teams
    }

    for _ in range(n_iter):
        result = simulate_group_stage(model, config, rng)
        for ranked in result.standings.values():
            for position, record in enumerate(ranked):
                counts[record.team][_POSITIONS[position]] += 1
        for team in result.advancing:
            counts[team]["advance"] += 1

    return {
        team: {key: value / n_iter for key, value in tallies.items()}
        for team, tallies in counts.items()
    }
