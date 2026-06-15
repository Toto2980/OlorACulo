from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

OUTCOMES: tuple[str, str, str] = ("home", "draw", "away")


@dataclass
class MatchPrediction:
    p_home: float
    p_draw: float
    p_away: float
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    score_matrix: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        total = self.p_home + self.p_draw + self.p_away
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"las probabilidades deben sumar 1, suman {total}")

    @property
    def probs(self) -> tuple[float, float, float]:
        return (self.p_home, self.p_draw, self.p_away)


class Predictor(Protocol):
    name: str

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date=None,
    ) -> MatchPrediction: ...
