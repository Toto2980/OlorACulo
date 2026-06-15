from __future__ import annotations

import datetime
from typing import Iterable, Protocol

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.evaluate.metrics import brier_score, rps, log_loss
from oraculo.evaluate.backtest import EvalResult


class StatefulModel(Protocol):
    """Modelo que aprende incrementalmente: predice y luego observa cada partido."""

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date: datetime.date | None = None,
    ) -> MatchPrediction: ...

    def observe(self, match: Match) -> None: ...

    def reset(self) -> None: ...


def walk_forward(
    model: StatefulModel,
    matches: Iterable[Match],
    *,
    eval_from: datetime.date | None = None,
) -> EvalResult:
    """Backtest walk-forward: por cada partido en orden cronológico, predecir con el
    estado previo y luego observar el resultado real (sin fuga de información).

    Solo se acumulan métricas para partidos con fecha >= eval_from; los anteriores
    sirven de warmup. Si eval_from es None, se evalúan todos.
    """
    ordered = sorted(matches, key=lambda m: m.date)
    model.reset()

    bs = rp = ll = 0.0
    n = 0
    for m in ordered:
        if eval_from is None or m.date >= eval_from:
            probs = model.predict(m.home, m.away, neutral=m.neutral, on_date=m.date).probs
            bs += brier_score(probs, m.outcome)
            rp += rps(probs, m.outcome)
            ll += log_loss(probs, m.outcome)
            n += 1
        model.observe(m)

    if n == 0:
        raise ValueError("no hay partidos para evaluar en el rango dado")
    return EvalResult(n_matches=n, brier=bs / n, rps=rp / n, log_loss=ll / n)
