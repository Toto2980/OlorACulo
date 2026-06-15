from __future__ import annotations

from pathlib import Path

import pandas as pd

from oraculo.match import Match


def load_results(path: str | Path) -> list[Match]:
    """Carga results.csv (formato martj42) en una lista de Match.

    Ignora filas sin marcador (partidos futuros / no jugados).
    """
    df = pd.read_csv(path, parse_dates=["date"])
    matches: list[Match] = []
    for row in df.itertuples(index=False):
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        matches.append(
            Match(
                date=row.date.date(),
                home=str(row.home_team),
                away=str(row.away_team),
                home_goals=int(row.home_score),
                away_goals=int(row.away_score),
                tournament=str(row.tournament),
                neutral=str(row.neutral).strip().lower() == "true",
            )
        )
    return matches
