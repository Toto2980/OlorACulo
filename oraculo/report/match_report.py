from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services import top_scorelines


@dataclass
class Speculative:
    """Extras NO rigurosos (no salen del modelo Poisson). Marcar en la UI como estimación."""
    top_scorer_team: str
    cards_band: str


@dataclass
class MatchReport:
    home: str
    away: str
    p_home: float
    p_draw: float
    p_away: float
    xg_home: float
    xg_away: float
    top_scores: list[tuple[tuple[int, int], float]]
    btts: float
    over25: float
    speculative: Speculative


def btts_prob(matrix: np.ndarray) -> float:
    """P(ambos marcan) = 1 - P(local=0) - P(visit=0) + P(0,0)."""
    p_home0 = float(matrix[0, :].sum())
    p_away0 = float(matrix[:, 0].sum())
    return 1.0 - p_home0 - p_away0 + float(matrix[0, 0])


def over_prob(matrix: np.ndarray, line: float = 2.5) -> float:
    """P(total de goles > line)."""
    threshold = int(line) + 1  # 2.5 -> total >= 3
    total = 0.0
    rows, cols = matrix.shape
    for i in range(rows):
        for j in range(cols):
            if i + j >= threshold:
                total += float(matrix[i, j])
    return total


def _cards_band(p_home: float, p_draw: float, p_away: float) -> str:
    """Heurística: cuanto más parejo el cruce, mayor la banda de tarjetas estimada."""
    spread = max(p_home, p_draw, p_away)
    if spread < 0.40:
        return "4–6"
    if spread < 0.55:
        return "3–5"
    return "2–4"


def build_match_report(model, home: str, away: str, *, neutral: bool = True) -> MatchReport:
    pred = model.predict(home, away, neutral=neutral)
    matrix = pred.score_matrix
    top_scorer = home if (pred.xg_home or 0) >= (pred.xg_away or 0) else away
    return MatchReport(
        home=home,
        away=away,
        p_home=pred.p_home,
        p_draw=pred.p_draw,
        p_away=pred.p_away,
        xg_home=float(pred.xg_home) if pred.xg_home is not None else 0.0,
        xg_away=float(pred.xg_away) if pred.xg_away is not None else 0.0,
        top_scores=top_scorelines(matrix, 5),
        btts=btts_prob(matrix),
        over25=over_prob(matrix, 2.5),
        speculative=Speculative(
            top_scorer_team=top_scorer,
            cards_band=_cards_band(pred.p_home, pred.p_draw, pred.p_away),
        ),
    )
