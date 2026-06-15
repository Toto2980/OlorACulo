from __future__ import annotations

import datetime
import itertools
from dataclasses import dataclass
from typing import Optional, Sequence

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel
from oraculo.evaluate.walk_forward import walk_forward


@dataclass
class CalibrationResult:
    config: EloConfig
    rps: float


def calibrate_elo(
    matches: Sequence[Match],
    *,
    k_values: Sequence[float],
    home_adv_values: Sequence[float],
    nu_values: Sequence[float],
    eval_from: datetime.date | None = None,
) -> CalibrationResult:
    """Grid search: devuelve la EloConfig que minimiza el RPS walk-forward."""
    matches = list(matches)
    best: Optional[CalibrationResult] = None
    for k, home_adv, nu in itertools.product(k_values, home_adv_values, nu_values):
        cfg = EloConfig(k=k, home_adv=home_adv, nu=nu)
        res = walk_forward(EloModel(cfg), matches, eval_from=eval_from)
        if best is None or res.rps < best.rps:
            best = CalibrationResult(config=cfg, rps=res.rps)
    if best is None:
        raise ValueError("el grid de calibración está vacío")
    return best
