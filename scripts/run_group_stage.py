"""Entrena el Poisson con todo el histórico y simula la fase de grupos del Mundial
2026 (semilla fija). Imprime, por grupo, P(1º)/P(2º)/P(avanza) de cada equipo."""
from __future__ import annotations

from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.tournament.config import load_config
from oraculo.tournament.montecarlo import run_group_stage_mc

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"
N_ITER = 10000


def main() -> None:
    matches = load_results(DATA)
    model = PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)).fit(matches)
    config = load_config(WC)

    print(f"Simulando la fase de grupos {N_ITER} veces (semilla {config.seed})...")
    probs = run_group_stage_mc(model, config, n_iter=N_ITER)

    for group, teams in config.groups.items():
        print(f"\nGrupo {group}:")
        ranked = sorted(teams, key=lambda t: probs[t]["advance"], reverse=True)
        for team in ranked:
            p = probs[team]
            print(f"  {team:<24} avanza {p['advance']*100:5.1f}%   "
                  f"(1º {p['1st']*100:4.1f}%  2º {p['2nd']*100:4.1f}%)")


if __name__ == "__main__":
    main()
