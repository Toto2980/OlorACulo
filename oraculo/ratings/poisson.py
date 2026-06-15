from __future__ import annotations

import math

import numpy as np


def poisson_pmf(k: int, lam: float) -> float:
    """Probabilidad de k eventos para una Poisson de media lam."""
    return math.exp(-lam) * lam ** k / math.factorial(k)


def dc_tau(i: int, j: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Corrección Dixon-Coles para marcadores bajos."""
    if i == 0 and j == 0:
        return 1.0 - lam_home * lam_away * rho
    if i == 0 and j == 1:
        return 1.0 + lam_home * rho
    if i == 1 and j == 0:
        return 1.0 + lam_away * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def expected_goals(
    att_home: float,
    def_home: float,
    att_away: float,
    def_away: float,
    *,
    baseline: float,
    home_adv: float,
    neutral: bool = False,
) -> tuple[float, float]:
    """Goles esperados (λ_local, λ_visit) a partir de ataque/defensa de cada equipo."""
    eta_home = baseline + att_home - def_away + (0.0 if neutral else home_adv)
    eta_away = baseline + att_away - def_home
    return math.exp(eta_home), math.exp(eta_away)


def score_matrix(
    lam_home: float,
    lam_away: float,
    *,
    rho: float,
    max_goals: int = 10,
) -> np.ndarray:
    """Matriz normalizada P(local=i, visit=j) con corrección Dixon-Coles."""
    home_pmf = np.array([poisson_pmf(i, lam_home) for i in range(max_goals + 1)])
    away_pmf = np.array([poisson_pmf(j, lam_away) for j in range(max_goals + 1)])
    m = np.outer(home_pmf, away_pmf)
    m[0, 0] *= 1.0 - lam_home * lam_away * rho
    m[0, 1] *= 1.0 + lam_home * rho
    m[1, 0] *= 1.0 + lam_away * rho
    m[1, 1] *= 1.0 - rho
    return m / m.sum()


def outcome_probs(matrix: np.ndarray) -> tuple[float, float, float]:
    """(P(local), P(empate), P(visit)) a partir de la matriz de resultados."""
    home = float(np.tril(matrix, -1).sum())  # i > j
    draw = float(np.trace(matrix))           # i == j
    away = float(np.triu(matrix, 1).sum())   # i < j
    return home, draw, away
