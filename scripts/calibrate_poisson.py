"""Calibra el Poisson por grid search minimizando RPS walk-forward, e imprime la
mejor config y su comparación con la vara y el Elo."""
from __future__ import annotations

import datetime
import math
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest
from oraculo.calibrate.poisson import calibrate_poisson

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"
EVAL_FROM = datetime.date(2010, 1, 1)

LR_VALUES = [0.03, 0.06, 0.1]
BASELINE_VALUES = [math.log(1.3)]
HOME_ADV_VALUES = [0.2, 0.3]
RHO_VALUES = [-0.1, -0.05, 0.0]


def main() -> None:
    matches = load_results(DATA)
    eval_set = [m for m in matches if m.date >= EVAL_FROM]
    uni = backtest(UniformPredictor(), eval_set)

    n_configs = len(LR_VALUES) * len(BASELINE_VALUES) * len(HOME_ADV_VALUES) * len(RHO_VALUES)
    print(f"Calibrando Poisson sobre {n_configs} configs (puede tardar varios minutos)...")
    best = calibrate_poisson(
        matches,
        lr_values=LR_VALUES,
        baseline_values=BASELINE_VALUES,
        home_adv_values=HOME_ADV_VALUES,
        rho_values=RHO_VALUES,
        eval_from=EVAL_FROM,
    )

    c = best.config
    print(f"Vara uniforme  RPS: {uni.rps:.4f}")
    print(f"Mejor Poisson  RPS: {best.rps:.4f}  "
          f"(lr={c.lr}, baseline={c.baseline:.4f}, home_adv={c.home_adv}, rho={c.rho})")
    print(f"Mejora sobre la vara: {uni.rps - best.rps:+.4f}")


if __name__ == "__main__":
    main()
