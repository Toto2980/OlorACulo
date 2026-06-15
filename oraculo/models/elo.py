from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.ratings.elo import davidson_probs, update_ratings


@dataclass
class EloConfig:
    k: float = 20.0
    home_adv: float = 65.0
    nu: float = 0.6
    initial_rating: float = 1500.0


class EloModel:
    """Nivel 2: Elo calculado desde resultados. Implementa el protocolo Predictor
    y además expone observe()/reset() para el backtest walk-forward."""

    name = "elo"

    def __init__(self, config: Optional[EloConfig] = None) -> None:
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = {}

    def reset(self) -> None:
        self.ratings = {}

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    def observe(self, match: Match) -> None:
        new_home, new_away = update_ratings(
            self.rating(match.home),
            self.rating(match.away),
            match.home_goals,
            match.away_goals,
            k=self.config.k,
            home_adv=self.config.home_adv,
            neutral=match.neutral,
        )
        self.ratings[match.home] = new_home
        self.ratings[match.away] = new_away

    def fit(self, matches: Iterable[Match]) -> "EloModel":
        for m in sorted(matches, key=lambda m: m.date):
            self.observe(m)
        return self

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date: datetime.date | None = None,
    ) -> MatchPrediction:
        """Predice usando los ratings ACTUALES del modelo.

        `on_date` no se usa internamente: el Elo es incremental, así que es
        responsabilidad del caller que `self.ratings` ya refleje el estado hasta
        la fecha de corte (el backtest `walk_forward` lo garantiza al predecir
        antes de observar cada partido; para predicción en vivo, llamar a `fit`
        con los partidos previos al corte).
        """
        dr = self.rating(home) - self.rating(away)
        if not neutral:
            dr += self.config.home_adv
        p_home, p_draw, p_away = davidson_probs(dr, self.config.nu)
        return MatchPrediction(p_home=p_home, p_draw=p_draw, p_away=p_away)
