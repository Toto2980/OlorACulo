from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from oraculo.match import Match
from oraculo.models.base import Predictor
from oraculo.evaluate.metrics import brier_score, rps, log_loss


@dataclass
class EvalResult:
    n_matches: int
    brier: float
    rps: float
    log_loss: float


def backtest(predictor: Predictor, matches: Iterable[Match]) -> EvalResult:
    """Evalúa un predictor sobre partidos jugados, en orden cronológico.

    Cada predictor es responsable de usar solo datos previos a `on_date`.
    """
    ordered = sorted(matches, key=lambda m: m.date)
    if not ordered:
        raise ValueError("no hay partidos para evaluar")

    bs = rp = ll = 0.0
    for m in ordered:
        pred = predictor.predict(m.home, m.away, neutral=m.neutral, on_date=m.date)
        probs = pred.probs
        bs += brier_score(probs, m.outcome)
        rp += rps(probs, m.outcome)
        ll += log_loss(probs, m.outcome)

    n = len(ordered)
    return EvalResult(n_matches=n, brier=bs / n, rps=rp / n, log_loss=ll / n)
