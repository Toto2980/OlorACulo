from __future__ import annotations

import datetime
import math
from dataclasses import dataclass
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import expected_goals, outcome_probs, score_matrix


@dataclass
class PoissonConfig:
    lr: float = 0.05
    baseline: float = math.log(1.3)
    home_adv: float = 0.25
    rho: float = -0.05
    max_goals: int = 10
    initial_strength: float = 0.0


class PoissonModel:
    """Nivel 4: modelo de goles. Ataque/defensa incrementales -> λ por lado ->
    matriz Poisson con corrección Dixon-Coles. Implementa Predictor y expone
    observe()/reset() para el walk-forward.

    `predict` usa los ratings ACTUALES; `on_date` no se usa internamente (el
    walk_forward garantiza no-fuga prediciendo antes de observar; para predicción
    en vivo, llamar a `fit` con los partidos previos al corte)."""

    name = "poisson"

    def __init__(self, config: Optional[PoissonConfig] = None) -> None:
        self.config = config or PoissonConfig()
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}

    def reset(self) -> None:
        self.attack = {}
        self.defense = {}

    def _att(self, team: str) -> float:
        return self.attack.get(team, self.config.initial_strength)

    def _def(self, team: str) -> float:
        return self.defense.get(team, self.config.initial_strength)

    def _expected(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        return expected_goals(
            self._att(home),
            self._def(home),
            self._att(away),
            self._def(away),
            baseline=self.config.baseline,
            home_adv=self.config.home_adv,
            neutral=neutral,
        )

    def observe(self, match: Match) -> None:
        lam_home, lam_away = self._expected(match.home, match.away, match.neutral)
        e_home = match.home_goals - lam_home
        e_away = match.away_goals - lam_away
        lr = self.config.lr
        self.attack[match.home] = self._att(match.home) + lr * e_home
        self.defense[match.away] = self._def(match.away) - lr * e_home
        self.attack[match.away] = self._att(match.away) + lr * e_away
        self.defense[match.home] = self._def(match.home) - lr * e_away

    def fit(self, matches: Iterable[Match]) -> "PoissonModel":
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
        lam_home, lam_away = self._expected(home, away, neutral)
        matrix = score_matrix(
            lam_home, lam_away, rho=self.config.rho, max_goals=self.config.max_goals
        )
        p_home, p_draw, p_away = outcome_probs(matrix)
        return MatchPrediction(
            p_home=p_home,
            p_draw=p_draw,
            p_away=p_away,
            xg_home=lam_home,
            xg_away=lam_away,
            score_matrix=matrix,
        )
