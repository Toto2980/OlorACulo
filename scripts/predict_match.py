"""Analiza un partido específico con el OlorACulo.

Uso:
  python scripts/predict_match.py "Argentina" "Brazil"
  python scripts/predict_match.py "Argentina" "Brazil" --home   # con ventaja de localía para el primero
  python scripts/predict_match.py "Spain" "France" --model elo

Por defecto el partido se considera en cancha NEUTRAL (como en el Mundial).
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

import numpy as np

from oraculo.ingest.results import load_results
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results.csv"


def _check_team(name: str, known: set[str]) -> None:
    if name not in known:
        sugg = difflib.get_close_matches(name, known, n=4, cutoff=0.4)
        hint = f" ¿Quisiste decir: {', '.join(sugg)}?" if sugg else ""
        raise SystemExit(f"Equipo no encontrado en el histórico: '{name}'.{hint}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Predice un partido con el OlorACulo.")
    parser.add_argument("home", help="equipo local (o primero, si es neutral)")
    parser.add_argument("away", help="equipo visitante (o segundo)")
    parser.add_argument("--home", action="store_true", help="aplicar ventaja de localía al primero")
    parser.add_argument("--model", choices=["poisson", "elo"], default="poisson")
    args = parser.parse_args()

    matches = load_results(DATA)
    known = {m.home for m in matches} | {m.away for m in matches}
    _check_team(args.home, known)
    _check_team(args.away, known)

    if args.model == "elo":
        model = EloModel().fit(matches)
    else:
        model = PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)).fit(matches)

    neutral = not args.home
    pred = model.predict(args.home, args.away, neutral=neutral)

    venue = "cancha neutral" if neutral else f"localía de {args.home}"
    print(f"\n{args.home} vs {args.away}  ({args.model}, {venue})\n")
    print(f"  Gana {args.home:<18} {pred.p_home * 100:5.1f}%")
    print(f"  Empate{'':<17} {pred.p_draw * 100:5.1f}%")
    print(f"  Gana {args.away:<18} {pred.p_away * 100:5.1f}%")

    if pred.xg_home is not None:
        print(f"\n  Goles esperados: {args.home} {pred.xg_home:.2f} - {pred.xg_away:.2f} {args.away}")

    if pred.score_matrix is not None:
        m = pred.score_matrix
        top = np.argsort(m, axis=None)[::-1][:5]
        print("\n  Marcadores más probables:")
        for idx in top:
            i, j = divmod(int(idx), m.shape[1])
            print(f"    {args.home} {i}-{j} {args.away}   {m[i, j] * 100:4.1f}%")


if __name__ == "__main__":
    main()
