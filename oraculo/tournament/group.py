from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from oraculo.models.base import MatchPrediction


def sample_scoreline(matrix: np.ndarray, rng: np.random.Generator) -> tuple[int, int]:
    """Muestrea (goles_local, goles_visit) de una matriz de resultados normalizada."""
    flat = matrix.ravel()
    idx = int(rng.choice(flat.size, p=flat))
    cols = matrix.shape[1]
    return idx // cols, idx % cols


def simulate_match(model, home: str, away: str, rng: np.random.Generator, *, neutral: bool = True) -> tuple[int, int]:
    """Predice con el modelo y muestrea un marcador concreto."""
    pred: MatchPrediction = model.predict(home, away, neutral=neutral)
    return sample_scoreline(pred.score_matrix, rng)


@dataclass
class TeamRecord:
    team: str
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def compute_standings(teams, results) -> dict[str, TeamRecord]:
    """results: iterable de (home, away, home_goals, away_goals). Devuelve tabla por equipo."""
    table = {t: TeamRecord(t) for t in teams}
    for home, away, hg, ag in results:
        table[home].goals_for += hg
        table[home].goals_against += ag
        table[away].goals_for += ag
        table[away].goals_against += hg
        if hg > ag:
            table[home].points += 3
        elif hg < ag:
            table[away].points += 3
        else:
            table[home].points += 1
            table[away].points += 1
    return table


def rank_group(table: dict[str, TeamRecord], rng: np.random.Generator) -> list[TeamRecord]:
    """Ordena por puntos -> DG -> GF -> azar sembrado (rompe empates irresolubles)."""
    return sorted(
        table.values(),
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, rng.random()),
    )


def simulate_group(model, teams, rng: np.random.Generator) -> list[TeamRecord]:
    """Juega todos contra todos (cancha neutral) y devuelve los 4 equipos rankeados."""
    results = []
    for home, away in itertools.combinations(teams, 2):
        hg, ag = simulate_match(model, home, away, rng, neutral=True)
        results.append((home, away, hg, ag))
    return rank_group(compute_standings(teams, results), rng)
