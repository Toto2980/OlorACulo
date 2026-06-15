from __future__ import annotations

import datetime

import numpy as np

from oraculo.match import Match
from oraculo.models.uniform import UniformPredictor
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.backtest import backtest, EvalResult
from oraculo.evaluate.walk_forward import walk_forward


def top_scorelines(matrix: np.ndarray, n: int = 5) -> list[tuple[tuple[int, int], float]]:
    """Los n marcadores más probables: lista de ((goles_local, goles_visit), prob)."""
    cols = matrix.shape[1]
    order = np.argsort(matrix, axis=None)[::-1][:n]
    out: list[tuple[tuple[int, int], float]] = []
    for idx in order:
        i, j = divmod(int(idx), cols)
        out.append(((i, j), float(matrix[i, j])))
    return out


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
