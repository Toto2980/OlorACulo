"""Calibra el Elo por grid search minimizando RPS walk-forward, e imprime la
mejor config y su mejora sobre la vara uniforme."""
from __future__ import annotations

import datetime
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest
from oraculo.calibrate.elo import calibrate_elo

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"
EVAL_FROM = datetime.date(2010, 1, 1)

K_VALUES = [10.0, 20.0, 30.0, 40.0]
HOME_ADV_VALUES = [0.0, 50.0, 65.0, 100.0]
NU_VALUES = [0.3, 0.6, 1.0]


def main() -> None:
    matches = load_results(DATA)
    eval_set = [m for m in matches if m.date >= EVAL_FROM]
    uni = backtest(UniformPredictor(), eval_set)

    print(f"Calibrando Elo sobre {len(K_VALUES) * len(HOME_ADV_VALUES) * len(NU_VALUES)} "
          f"configs (esto puede tardar ~1 min)...")
    best = calibrate_elo(
        matches,
        k_values=K_VALUES,
        home_adv_values=HOME_ADV_VALUES,
        nu_values=NU_VALUES,
        eval_from=EVAL_FROM,
    )

    c = best.config
    print(f"Vara uniforme  RPS: {uni.rps:.4f}")
    print(f"Mejor Elo      RPS: {best.rps:.4f}  (K={c.k}, home_adv={c.home_adv}, nu={c.nu})")
    print(f"Mejora: {uni.rps - best.rps:+.4f}")


if __name__ == "__main__":
    main()
