"""Descarga results.csv del dataset martj42/international_results."""
from __future__ import annotations

import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
DEST = Path(__file__).resolve().parent.parent / "data" / "results.csv"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando {URL} ...")
    urllib.request.urlretrieve(URL, DEST)
    size = DEST.stat().st_size
    print(f"Guardado en {DEST} ({size} bytes)")


if __name__ == "__main__":
    main()
