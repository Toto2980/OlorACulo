"""Compara uniforme, Elo (default) y Poisson (default) sobre la MISMA ventana
de evaluación (partidos desde EVAL_FROM; lo anterior es warmup)."""
from __future__ import annotations

import datetime
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonModel
from oraculo.evaluate.backtest import backtest
from oraculo.evaluate.walk_forward import walk_forward

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"
EVAL_FROM = datetime.date(2010, 1, 1)


def main() -> None:
    matches = load_results(DATA)
    eval_set = [m for m in matches if m.date >= EVAL_FROM]

    uni = backtest(UniformPredictor(), eval_set)
    elo = walk_forward(EloModel(), matches, eval_from=EVAL_FROM)
    poi = walk_forward(PoissonModel(), matches, eval_from=EVAL_FROM)

    print(f"Ventana de evaluación: desde {EVAL_FROM} ({uni.n_matches} partidos)")
    print(f"  Uniforme  RPS: {uni.rps:.4f}  Brier: {uni.brier:.4f}  LogLoss: {uni.log_loss:.4f}")
    print(f"  Elo       RPS: {elo.rps:.4f}  Brier: {elo.brier:.4f}  LogLoss: {elo.log_loss:.4f}")
    print(f"  Poisson   RPS: {poi.rps:.4f}  Brier: {poi.brier:.4f}  LogLoss: {poi.log_loss:.4f}")


if __name__ == "__main__":
    main()
