from __future__ import annotations

import datetime
import itertools
from dataclasses import dataclass
from typing import Optional, Sequence

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.walk_forward import walk_forward


@dataclass
class PoissonCalibrationResult:
    config: PoissonConfig
    rps: float


def calibrate_poisson(
    matches: Sequence[Match],
    *,
    lr_values: Sequence[float],
    baseline_values: Sequence[float],
    home_adv_values: Sequence[float],
    rho_values: Sequence[float],
    eval_from: datetime.date | None = None,
) -> PoissonCalibrationResult:
    """Grid search: devuelve la PoissonConfig que minimiza el RPS walk-forward."""
    match_list = list(matches)
    best: Optional[PoissonCalibrationResult] = None
    for lr, baseline, home_adv, rho in itertools.product(
        lr_values, baseline_values, home_adv_values, rho_values
    ):
        cfg = PoissonConfig(lr=lr, baseline=baseline, home_adv=home_adv, rho=rho)
        res = walk_forward(PoissonModel(cfg), match_list, eval_from=eval_from)
        if best is None or res.rps < best.rps:
            best = PoissonCalibrationResult(config=cfg, rps=res.rps)
    if best is None:
        raise ValueError("el grid de calibración está vacío")
    return best
