"""Corre el predictor uniforme sobre todos los resultados históricos
e imprime las métricas. Esta es la vara contra la que se mide todo lo demás."""
from __future__ import annotations

from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"


def main() -> None:
    matches = load_results(DATA)
    res = backtest(UniformPredictor(), matches)
    print(f"Baseline uniforme sobre {res.n_matches} partidos:")
    print(f"  Brier:    {res.brier:.4f}")
    print(f"  RPS:      {res.rps:.4f}")
    print(f"  Log loss: {res.log_loss:.4f}")


if __name__ == "__main__":
    main()
