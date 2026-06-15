from __future__ import annotations

import numpy as np

from oraculo.tournament.bracket import resolve_bracket
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage
from oraculo.tournament.knockout import simulate_knockout

ROUNDS = ("R32", "R16", "QF", "SF", "Final", "Champion")


def simulate_tournament(
    model, config: WorldCupConfig, rng: np.random.Generator
) -> dict[str, list[str]]:
    """Un torneo completo: fase de grupos -> cuadro -> eliminatorias.
    Devuelve, por ronda, la lista de equipos que llegaron."""
    gsr = simulate_group_stage(model, config, rng)
    r32_pairs = resolve_bracket(gsr)
    return simulate_knockout(model, r32_pairs, rng)


def run_tournament_mc(
    model, config: WorldCupConfig, *, n_iter: int
) -> dict[str, dict[str, float]]:
    """Corre n_iter torneos completos (semilla fija desde config.seed) y devuelve,
    por equipo, P(llega a cada ronda) y P(campeón)."""
    rng = np.random.default_rng(config.seed)
    counts = {team: {r: 0 for r in ROUNDS} for team in config.teams}
    for _ in range(n_iter):
        rounds = simulate_tournament(model, config, rng)
        for r in ROUNDS:
            for team in rounds[r]:
                counts[team][r] += 1
    return {
        team: {r: c / n_iter for r, c in tallies.items()}
        for team, tallies in counts.items()
    }
