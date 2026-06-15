from __future__ import annotations

from oraculo.models.base import MatchPrediction


class UniformPredictor:
    """Nivel 0: el oloráculo. No sabe nada de fútbol; 1/3 a cada resultado."""

    name = "uniform"

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date=None,
    ) -> MatchPrediction:
        return MatchPrediction(p_home=1 / 3, p_draw=1 / 3, p_away=1 / 3)
