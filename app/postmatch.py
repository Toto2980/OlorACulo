"""Análisis post-partido: lo que el oráculo esperaba (pre-partido) vs lo que pasó.
Determinístico, compone lo que ya existe (score_match, top_scorelines). No usa
internet ni LLM."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from oraculo.verify.scoring import score_match
from app.services import top_scorelines
from app.flags import display_name


@dataclass
class PostMatch:
    home: str
    away: str
    home_goals: int
    away_goals: int
    p_home: float
    p_draw: float
    p_away: float
    outcome_pred: str          # "home" | "draw" | "away"
    outcome_actual: str
    hit: bool
    rps: float
    xg_home: Optional[float]
    xg_away: Optional[float]
    top_scores: list           # [((i, j), prob), ...]
    scoreline_in_top5: bool
    scoreline_rank: Optional[int]
    verdict: str


def _outcome_label(outcome: str, home: str, away: str) -> str:
    if outcome == "home":
        return f"que ganara {display_name(home)}"
    if outcome == "away":
        return f"que ganara {display_name(away)}"
    return "un empate"


def postmatch_report(pred, home: str, away: str, home_goals: int, away_goals: int) -> PostMatch:
    s = score_match(0, pred.probs, home_goals, away_goals)
    top = top_scorelines(pred.score_matrix, 5)
    rank = next(
        (k for k, ((i, j), _) in enumerate(top, start=1) if i == home_goals and j == away_goals),
        None,
    )
    p_fav = max(pred.p_home, pred.p_away)
    esperado = _outcome_label(s.outcome_pred, home, away)
    marcador = f"{display_name(home)} {home_goals}–{away_goals} {display_name(away)}"

    if s.hit:
        verdict = f"El oráculo **acertó**: esperaba {esperado} ({p_fav * 100:.0f}%) y así fue ({marcador})."
    else:
        verdict = f"El oráculo **falló**: esperaba {esperado} ({p_fav * 100:.0f}%) pero terminó {marcador}."
    if rank:
        verdict += f" Además, el marcador estaba {rank}º entre los más probables."
    else:
        verdict += " El marcador no estaba en el top-5 previsto."

    return PostMatch(
        home=home, away=away, home_goals=home_goals, away_goals=away_goals,
        p_home=pred.p_home, p_draw=pred.p_draw, p_away=pred.p_away,
        outcome_pred=s.outcome_pred, outcome_actual=s.outcome_actual,
        hit=s.hit, rps=s.rps,
        xg_home=pred.xg_home, xg_away=pred.xg_away,
        top_scores=top, scoreline_in_top5=rank is not None, scoreline_rank=rank,
        verdict=verdict,
    )
