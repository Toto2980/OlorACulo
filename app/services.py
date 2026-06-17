from __future__ import annotations

import datetime

import numpy as np

from oraculo.match import Match
from oraculo.models.uniform import UniformPredictor
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel
from typing import TYPE_CHECKING

from oraculo.evaluate.backtest import backtest, EvalResult
from oraculo.evaluate.walk_forward import walk_forward
from app.flags import display_name

if TYPE_CHECKING:
    from oraculo.report.match_report import MatchReport


def top_scorelines(matrix: np.ndarray, n: int = 5) -> list[tuple[tuple[int, int], float]]:
    """Los n marcadores más probables: lista de ((goles_local, goles_visit), prob)."""
    cols = matrix.shape[1]
    order = np.argsort(matrix, axis=None)[::-1][:n]
    out: list[tuple[tuple[int, int], float]] = []
    for idx in order:
        i, j = divmod(int(idx), cols)
        out.append(((i, j), float(matrix[i, j])))
    return out


def head_to_head(matches, team_a: str, team_b: str) -> tuple[int, int, int, int]:
    """Historial entre dos equipos sobre el dataset histórico.
    Devuelve (PJ, victorias_de_a, victorias_de_b, empates)."""
    pj = wa = wb = dr = 0
    pair = {team_a, team_b}
    for m in matches:
        if {m.home, m.away} != pair:
            continue
        pj += 1
        if m.home_goals == m.away_goals:
            dr += 1
        else:
            winner = m.home if m.home_goals > m.away_goals else m.away
            if winner == team_a:
                wa += 1
            else:
                wb += 1
    return pj, wa, wb, dr


def scoreline_hit(matrix, home_goals: int, away_goals: int, n: int = 5) -> bool:
    """True si el marcador real (home_goals, away_goals) está entre los n marcadores
    más probables de la matriz."""
    return any(
        i == home_goals and j == away_goals for (i, j), _ in top_scorelines(matrix, n)
    )


def model_comparison(
    matches: list[Match], eval_from: datetime.date
) -> dict[str, EvalResult]:
    """Backtest comparativo (uniforme vs Elo vs Poisson) sobre la misma ventana."""
    eval_set = [m for m in matches if m.date >= eval_from]
    return {
        "uniforme": backtest(UniformPredictor(), eval_set),
        "elo": walk_forward(EloModel(), matches, eval_from=eval_from),
        "poisson": walk_forward(
            PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)),
            matches,
            eval_from=eval_from,
        ),
    }


def prode_verdict(report: "MatchReport") -> str:
    """Conclusión pre-partido en lenguaje natural a partir del MatchReport.
    Determinística (sin LLM ni internet)."""
    probs = {report.home: report.p_home, report.away: report.p_away}
    fav = max(probs, key=probs.get)
    rival = report.away if fav == report.home else report.home
    fav_p = probs[fav]
    spread = max(report.p_home, report.p_draw, report.p_away)

    if spread < 0.45:
        tono = (
            f"Cruce parejo entre {display_name(fav)} y {display_name(rival)}: "
            f"{display_name(fav)} apenas favorito ({fav_p * 100:.0f}%)."
        )
    else:
        tono = (
            f"{display_name(fav)} llega favorito ({fav_p * 100:.0f}%) "
            f"ante {display_name(rival)}."
        )

    if report.over25 >= 0.55:
        goles = f"Se esperan goles (Over 2.5 al {report.over25 * 100:.0f}%)."
    elif report.over25 <= 0.40:
        goles = f"Partido trabado, pocos goles (Over 2.5 al {report.over25 * 100:.0f}%)."
    else:
        goles = f"Los goles están en duda (Over 2.5 al {report.over25 * 100:.0f}%)."

    return f"{tono} {goles}"
