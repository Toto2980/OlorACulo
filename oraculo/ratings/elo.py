from __future__ import annotations

import math


def expected_score(rating_diff: float) -> float:
    """Expectativa Elo (incluye medio empate) para una diferencia de rating efectiva."""
    return 1.0 / (1.0 + 10 ** (-rating_diff / 400.0))


def goal_multiplier(margin: int) -> float:
    """Multiplicador por margen de victoria (estilo World Football Elo)."""
    m = abs(margin)
    if m <= 1:
        return 1.0
    if m == 2:
        return 1.5
    return (11 + m) / 8.0


def update_ratings(
    r_home: float,
    r_away: float,
    home_goals: int,
    away_goals: int,
    *,
    k: float,
    home_adv: float,
    neutral: bool = False,
) -> tuple[float, float]:
    """Devuelve (nuevo_rating_local, nuevo_rating_visitante) tras un partido."""
    dr = r_home - r_away + (0.0 if neutral else home_adv)
    we = expected_score(dr)
    if home_goals > away_goals:
        w = 1.0
    elif home_goals < away_goals:
        w = 0.0
    else:
        w = 0.5
    g = goal_multiplier(home_goals - away_goals)
    delta = k * g * (w - we)
    return r_home + delta, r_away - delta


def davidson_probs(rating_diff: float, nu: float) -> tuple[float, float, float]:
    """Probabilidades (local, empate, visitante) via modelo Davidson.

    `nu` >= 0 controla la frecuencia de empates (nu=0 -> sin empates).
    `rating_diff` es la diferencia efectiva (ya incluye la ventaja de localía).
    """
    gamma = 10 ** (rating_diff / 400.0)
    root = math.sqrt(gamma)
    denom = gamma + 1.0 + nu * root
    p_home = gamma / denom
    p_draw = nu * root / denom
    p_away = 1.0 / denom
    return p_home, p_draw, p_away
