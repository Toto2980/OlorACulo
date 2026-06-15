"""Entrena el Poisson con todo el histórico y simula el Mundial 2026 completo
(semilla fija). Imprime el ranking de P(campeón) y las rondas alcanzadas."""
from __future__ import annotations

from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.tournament.config import load_config
from oraculo.tournament.tournament import run_tournament_mc

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"
N_ITER = 10000


def main() -> None:
    matches = load_results(DATA)
    model = PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)).fit(matches)
    config = load_config(WC)

    print(f"Simulando el Mundial 2026 completo {N_ITER} veces (semilla {config.seed})...\n")
    probs = run_tournament_mc(model, config, n_iter=N_ITER)

    ranking = sorted(config.teams, key=lambda t: probs[t]["Champion"], reverse=True)
    print(f"{'Equipo':<24} {'Campeón':>8} {'Final':>7} {'Semi':>7} {'Cuartos':>8}")
    for team in ranking[:24]:
        p = probs[team]
        print(f"{team:<24} {p['Champion']*100:7.1f}% {p['Final']*100:6.1f}% "
              f"{p['SF']*100:6.1f}% {p['QF']*100:7.1f}%")

    champ = ranking[0]
    print(f"\nSegún el OlorACulo, el favorito es: {champ} "
          f"({probs[champ]['Champion']*100:.1f}% de chances de campeón)")


if __name__ == "__main__":
    main()
