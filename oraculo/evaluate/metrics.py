from __future__ import annotations

import math

from oraculo.models.base import OUTCOMES

Probs = tuple[float, float, float]


def _onehot(outcome: str) -> tuple[float, ...]:
    return tuple(1.0 if o == outcome else 0.0 for o in OUTCOMES)


def brier_score(probs: Probs, outcome: str) -> float:
    o = _onehot(outcome)
    return sum((p - oi) ** 2 for p, oi in zip(probs, o))


def rps(probs: Probs, outcome: str) -> float:
    """Ranked Probability Score para resultados ordenados (home < draw < away)."""
    o = _onehot(outcome)
    cum_p = 0.0
    cum_o = 0.0
    total = 0.0
    for i in range(len(OUTCOMES) - 1):
        cum_p += probs[i]
        cum_o += o[i]
        total += (cum_p - cum_o) ** 2
    return total / (len(OUTCOMES) - 1)


def log_loss(probs: Probs, outcome: str, *, eps: float = 1e-15) -> float:
    idx = OUTCOMES.index(outcome)
    p = min(max(probs[idx], eps), 1 - eps)
    return -math.log(p)
