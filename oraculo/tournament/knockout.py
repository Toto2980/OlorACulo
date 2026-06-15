from __future__ import annotations

import numpy as np

from oraculo.tournament.group import sample_scoreline

_KNOCKOUT_ROUNDS = ("R16", "QF", "SF", "Final", "Champion")


def knockout_winner(model, home: str, away: str, rng: np.random.Generator) -> str:
    """Simula un partido de eliminación (neutral). Empate -> penales ponderados
    por la fuerza relativa del modelo (p_local / (p_local + p_visit))."""
    pred = model.predict(home, away, neutral=True)
    hg, ag = sample_scoreline(pred.score_matrix, rng)
    if hg > ag:
        return home
    if ag > hg:
        return away
    denom = pred.p_home + pred.p_away
    p_home_pens = 0.5 if denom == 0 else pred.p_home / denom
    return home if rng.random() < p_home_pens else away


def simulate_knockout(model, r32_pairs, rng: np.random.Generator) -> dict[str, list[str]]:
    """Simula el cuadro completo desde 32avos. Devuelve, por ronda, la lista de
    equipos que LLEGARON a esa instancia. Claves: R32, R16, QF, SF, Final, Champion."""
    rounds: dict[str, list[str]] = {"R32": [team for pair in r32_pairs for team in pair]}
    pairs = list(r32_pairs)
    for name in _KNOCKOUT_ROUNDS:
        winners = [knockout_winner(model, home, away, rng) for home, away in pairs]
        rounds[name] = winners
        if len(winners) == 1:
            break
        pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    return rounds
