from __future__ import annotations

from dataclasses import dataclass

from oraculo.evaluate.metrics import brier_score, rps
from oraculo.models.base import OUTCOMES

Probs = tuple[float, float, float]


def actual_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


@dataclass
class MatchScore:
    fixture_id: int
    probs: Probs
    outcome_pred: str
    outcome_actual: str
    hit: bool
    brier: float
    rps: float


def score_match(fixture_id: int, probs: Probs, home_goals: int, away_goals: int) -> MatchScore:
    actual = actual_outcome(home_goals, away_goals)
    pred = OUTCOMES[max(range(3), key=lambda i: probs[i])]
    return MatchScore(
        fixture_id=fixture_id,
        probs=probs,
        outcome_pred=pred,
        outcome_actual=actual,
        hit=(pred == actual),
        brier=brier_score(probs, actual),
        rps=rps(probs, actual),
    )


@dataclass
class Summary:
    n: int
    hit_rate: float
    mean_brier: float
    mean_rps: float


def aggregate(scores: list[MatchScore]) -> Summary:
    n = len(scores)
    if n == 0:
        return Summary(0, 0.0, 0.0, 0.0)
    return Summary(
        n=n,
        hit_rate=sum(s.hit for s in scores) / n,
        mean_brier=sum(s.brier for s in scores) / n,
        mean_rps=sum(s.rps for s in scores) / n,
    )


@dataclass
class CalibrationBin:
    center: float
    predicted: float
    observed: float
    n: int


def calibration_bins(pairs: list[tuple[float, bool]], n_bins: int = 5) -> list[CalibrationBin]:
    """pairs: (prob predicha de un evento, si ocurrió). Devuelve n_bins ordenados."""
    edges = [i / n_bins for i in range(n_bins + 1)]
    out: list[CalibrationBin] = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        chunk = [(p, occ) for p, occ in pairs if (lo <= p < hi) or (b == n_bins - 1 and p == hi)]
        n = len(chunk)
        predicted = sum(p for p, _ in chunk) / n if n else 0.0
        observed = sum(1 for _, occ in chunk if occ) / n if n else 0.0
        out.append(CalibrationBin(center=(lo + hi) / 2, predicted=predicted, observed=observed, n=n))
    return out
