# Oráculo Mundial 2026 — Plan 1: Cimientos + vara de medición

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar el esqueleto del proyecto funcionando y el "oloráculo" uniforme medible contra datos reales con Brier/RPS/log-loss — la vara contra la que se comparará todo lo demás.

**Architecture:** Núcleo Python puro en el paquete `oraculo/`. Modelo de dominio `Match`, ingesta de `results.csv`, un protocolo `Predictor` común, el predictor uniforme (nivel 0), métricas y un harness de backtest. Sin UI todavía.

**Tech Stack:** Python 3.11+, pandas, numpy, pytest. Entorno virtual local. Git.

**Decomposición:** Este es el Plan 1 de una serie. Los siguientes (cada uno su propio plan): Plan 2 ranking FIFA + Elo propio + calibración · Plan 3 Poisson/Dixon-Coles · Plan 4 Monte Carlo + `wc2026.yaml` · Plan 5 SQLite + ingesta en vivo · Plan 6 CLI + Streamlit.

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Todos los paths son relativos a esa carpeta.

**Nota sobre commits (Windows/PowerShell):** Cada commit lleva el trailer de coautoría. Los comandos usan la forma con doble `-m` para que ande igual en PowerShell y bash. Para evitar problemas de execution-policy de PowerShell con `Activate.ps1`, los comandos llaman al Python del venv por ruta directa (`.\.venv\Scripts\python.exe`).

---

## Task 1: Andamiaje del proyecto + git

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `oraculo/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Crear la estructura de carpetas**

Desde `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo` (crearla si no existe):

```powershell
New-Item -ItemType Directory -Force oraculo, oraculo\ingest, oraculo\models, oraculo\evaluate, tests, tests\fixtures, scripts, data, docs\superpowers\plans
```

- [ ] **Step 2: Escribir `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "oraculo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pandas", "numpy"]

[project.optional-dependencies]
dev = ["pytest"]

[tool.setuptools.packages.find]
include = ["oraculo*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Escribir `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
*.egg-info/
data/*.csv
data/*.db
.pytest_cache/
```

- [ ] **Step 4: Escribir `README.md`**

```markdown
# Oráculo Mundial 2026

Predictor del Mundial 2026 por niveles (uniforme → FIFA → Elo → Poisson/Dixon-Coles)
con simulación Monte Carlo. Núcleo Python; interfaz CLI + Streamlit.

## Setup
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```
```

- [ ] **Step 5: Crear los `__init__.py` vacíos**

Crear `oraculo/__init__.py` y `tests/__init__.py` como archivos vacíos.

- [ ] **Step 6: Escribir un test de humo en `tests/test_smoke.py`**

```python
def test_smoke():
    assert True
```

- [ ] **Step 7: Crear el entorno e instalar**

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
Expected: instala pandas, numpy, pytest y el paquete `oraculo` en modo editable, sin errores.

- [ ] **Step 8: Correr el test de humo**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Inicializar git y primer commit**

```powershell
git init
git add .
git commit -m "chore: project scaffolding" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Modelo de dominio `Match`

**Files:**
- Create: `oraculo/match.py`
- Test: `tests/test_match.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import datetime
from oraculo.match import Match


def _match(hg, ag):
    return Match(
        date=datetime.date(2022, 11, 20),
        home="A", away="B",
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=False,
    )


def test_outcome_home_win():
    assert _match(2, 0).outcome == "home"


def test_outcome_away_win():
    assert _match(0, 1).outcome == "away"


def test_outcome_draw():
    assert _match(1, 1).outcome == "draw"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.match'`.

- [ ] **Step 3: Escribir la implementación mínima**

```python
from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    date: datetime.date
    home: str
    away: str
    home_goals: int
    away_goals: int
    tournament: str
    neutral: bool

    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return "home"
        if self.home_goals < self.away_goals:
            return "away"
        return "draw"
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/match.py tests/test_match.py
git commit -m "feat: add Match domain model with outcome" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Ingesta de `results.csv`

**Files:**
- Create: `oraculo/ingest/__init__.py` (vacío)
- Create: `oraculo/ingest/results.py`
- Create: `tests/fixtures/sample_results.csv`
- Test: `tests/test_results.py`

- [ ] **Step 1: Crear el fixture `tests/fixtures/sample_results.csv`**

Replica las columnas reales del dataset martj42. Incluye una fila con marcador vacío (partido futuro) que debe ignorarse:

```csv
date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
2022-11-20,Qatar,Ecuador,0,2,FIFA World Cup,Al Khor,Qatar,FALSE
2022-11-21,England,Iran,6,2,FIFA World Cup,Al Rayyan,Qatar,TRUE
2022-11-21,Senegal,Netherlands,0,2,FIFA World Cup,Al Khor,Qatar,TRUE
2026-06-11,Mexico,TBD,,,FIFA World Cup,Mexico City,Mexico,FALSE
```

- [ ] **Step 2: Escribir el test que falla**

```python
import datetime
from pathlib import Path

from oraculo.ingest.results import load_results

FIXTURE = Path(__file__).parent / "fixtures" / "sample_results.csv"


def test_loads_only_played_matches():
    matches = load_results(FIXTURE)
    # la 4ta fila tiene marcador vacío y se ignora
    assert len(matches) == 3


def test_parses_fields():
    matches = load_results(FIXTURE)
    first = matches[0]
    assert first.date == datetime.date(2022, 11, 20)
    assert first.home == "Qatar"
    assert first.away == "Ecuador"
    assert first.home_goals == 0
    assert first.away_goals == 2
    assert first.neutral is False


def test_parses_neutral_true():
    matches = load_results(FIXTURE)
    assert matches[1].neutral is True
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_results.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.ingest.results'`.

- [ ] **Step 4: Escribir la implementación mínima**

`oraculo/ingest/results.py`:

```python
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
```

No olvidar crear `oraculo/ingest/__init__.py` vacío.

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_results.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```powershell
git add oraculo/ingest/ tests/test_results.py tests/fixtures/sample_results.csv
git commit -m "feat: load results.csv into Match objects" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Descargar los datos reales

**Files:**
- Create: `scripts/download_data.py`

- [ ] **Step 1: Escribir el script de descarga**

`scripts/download_data.py`:

```python
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
```

- [ ] **Step 2: Correr el script**

Run: `.\.venv\Scripts\python.exe scripts\download_data.py`
Expected: imprime "Guardado en ...\data\results.csv" con un tamaño de varios MB.

- [ ] **Step 3: Verificar que cargan muchos partidos**

Run:
```powershell
.\.venv\Scripts\python.exe -c "from oraculo.ingest.results import load_results; print(len(load_results('data/results.csv')))"
```
Expected: imprime un número grande (más de 40000 partidos).

- [ ] **Step 4: Commit (solo el script; el CSV está en .gitignore)**

```powershell
git add scripts/download_data.py
git commit -m "feat: add results.csv download script" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Protocolo `Predictor` + `MatchPrediction`

**Files:**
- Create: `oraculo/models/__init__.py` (vacío)
- Create: `oraculo/models/base.py`
- Test: `tests/test_base.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import pytest

from oraculo.models.base import MatchPrediction, OUTCOMES


def test_outcomes_order():
    assert OUTCOMES == ("home", "draw", "away")


def test_probs_tuple():
    pred = MatchPrediction(p_home=0.5, p_draw=0.3, p_away=0.2)
    assert pred.probs == (0.5, 0.3, 0.2)


def test_rejects_probs_not_summing_to_one():
    with pytest.raises(ValueError):
        MatchPrediction(p_home=0.5, p_draw=0.5, p_away=0.5)
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_base.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.models.base'`.

- [ ] **Step 3: Escribir la implementación mínima**

`oraculo/models/base.py`:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

OUTCOMES: tuple[str, str, str] = ("home", "draw", "away")


@dataclass
class MatchPrediction:
    p_home: float
    p_draw: float
    p_away: float
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    score_matrix: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        total = self.p_home + self.p_draw + self.p_away
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"las probabilidades deben sumar 1, suman {total}")

    @property
    def probs(self) -> tuple[float, float, float]:
        return (self.p_home, self.p_draw, self.p_away)


class Predictor(Protocol):
    name: str

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date=None,
    ) -> MatchPrediction: ...
```

No olvidar crear `oraculo/models/__init__.py` vacío.

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_base.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/models/__init__.py oraculo/models/base.py tests/test_base.py
git commit -m "feat: add Predictor protocol and MatchPrediction" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Nivel 0 — Predictor uniforme

**Files:**
- Create: `oraculo/models/uniform.py`
- Test: `tests/test_uniform.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import pytest

from oraculo.models.uniform import UniformPredictor


def test_name():
    assert UniformPredictor().name == "uniform"


def test_returns_thirds():
    pred = UniformPredictor().predict("Argentina", "Francia")
    assert pred.p_home == pytest.approx(1 / 3)
    assert pred.p_draw == pytest.approx(1 / 3)
    assert pred.p_away == pytest.approx(1 / 3)


def test_ignores_teams():
    a = UniformPredictor().predict("Brasil", "San Marino").probs
    b = UniformPredictor().predict("San Marino", "Brasil").probs
    assert a == b
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_uniform.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.models.uniform'`.

- [ ] **Step 3: Escribir la implementación mínima**

`oraculo/models/uniform.py`:

```python
from __future__ import annotations

from oraculo.models.base import MatchPrediction


class UniformPredictor:
    """Nivel 0: el oloráculo. No sabe nada de fútbol; 1/3 a cada resultado."""

    name = "uniform"

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date=None,
    ) -> MatchPrediction:
        return MatchPrediction(p_home=1 / 3, p_draw=1 / 3, p_away=1 / 3)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_uniform.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/models/uniform.py tests/test_uniform.py
git commit -m "feat: add uniform baseline predictor (level 0)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Métricas (Brier, RPS, log-loss)

**Files:**
- Create: `oraculo/evaluate/__init__.py` (vacío)
- Create: `oraculo/evaluate/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Escribir el test que falla**

Valores calculados a mano. Para `p=(0.5,0.3,0.2)` con resultado `home`:
Brier = (0.5-1)²+(0.3)²+(0.2)² = 0.38 ·
RPS = ½·[(0.5-1)²+(0.8-1)²] = ½·(0.25+0.04) = 0.145 ·
log-loss = -ln(0.5) = 0.6931.

```python
import math

import pytest

from oraculo.evaluate.metrics import brier_score, rps, log_loss

P = (0.5, 0.3, 0.2)


def test_brier_home():
    assert brier_score(P, "home") == pytest.approx(0.38)


def test_rps_home():
    assert rps(P, "home") == pytest.approx(0.145)


def test_log_loss_home():
    assert log_loss(P, "home") == pytest.approx(-math.log(0.5))


def test_uniform_metrics_home():
    u = (1 / 3, 1 / 3, 1 / 3)
    assert brier_score(u, "home") == pytest.approx(2 / 3)
    assert rps(u, "home") == pytest.approx(5 / 18)
    assert log_loss(u, "home") == pytest.approx(-math.log(1 / 3))


def test_rps_perfect_prediction_is_zero():
    assert rps((1.0, 0.0, 0.0), "home") == pytest.approx(0.0)
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.evaluate.metrics'`.

- [ ] **Step 3: Escribir la implementación mínima**

`oraculo/evaluate/metrics.py`:

```python
from __future__ import annotations

import math

from oraculo.models.base import OUTCOMES

Probs = tuple[float, float, float]


def _onehot(outcome: str) -> tuple[float, ...]:
    return tuple(1.0 if o == outcome else 0.0 for o in OUTCOMES)


def brier_score(probs: Probs, outcome: str) -> float:
    o = _onehot(outcome)
    return sum((p - oi) ** 2 for p, oi in zip(probs, o))


def rps(probs: Probs, outcome: str) -> float:
    """Ranked Probability Score para resultados ordenados (home < draw < away)."""
    o = _onehot(outcome)
    cum_p = 0.0
    cum_o = 0.0
    total = 0.0
    for i in range(len(OUTCOMES) - 1):
        cum_p += probs[i]
        cum_o += o[i]
        total += (cum_p - cum_o) ** 2
    return total / (len(OUTCOMES) - 1)


def log_loss(probs: Probs, outcome: str, *, eps: float = 1e-15) -> float:
    idx = OUTCOMES.index(outcome)
    p = min(max(probs[idx], eps), 1 - eps)
    return -math.log(p)
```

No olvidar crear `oraculo/evaluate/__init__.py` vacío.

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/evaluate/__init__.py oraculo/evaluate/metrics.py tests/test_metrics.py
git commit -m "feat: add Brier, RPS and log-loss metrics" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Harness de backtest

**Files:**
- Create: `oraculo/evaluate/backtest.py`
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Escribir el test que falla**

```python
import datetime

import pytest

from oraculo.match import Match
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest, EvalResult


def _m(d, hg, ag):
    return Match(
        date=datetime.date(2022, 1, d),
        home="A", away="B",
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=False,
    )


def test_empty_raises():
    with pytest.raises(ValueError):
        backtest(UniformPredictor(), [])


def test_uniform_over_two_home_wins():
    matches = [_m(1, 2, 0), _m(2, 3, 1)]  # ambos resultado "home"
    res = backtest(UniformPredictor(), matches)
    assert isinstance(res, EvalResult)
    assert res.n_matches == 2
    assert res.brier == pytest.approx(2 / 3)
    assert res.rps == pytest.approx(5 / 18)
    assert res.log_loss == pytest.approx(__import__("math").log(3))
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_backtest.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'oraculo.evaluate.backtest'`.

- [ ] **Step 3: Escribir la implementación mínima**

`oraculo/evaluate/backtest.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from oraculo.match import Match
from oraculo.models.base import Predictor
from oraculo.evaluate.metrics import brier_score, rps, log_loss


@dataclass
class EvalResult:
    n_matches: int
    brier: float
    rps: float
    log_loss: float


def backtest(predictor: Predictor, matches: Iterable[Match]) -> EvalResult:
    """Evalúa un predictor sobre partidos jugados, en orden cronológico.

    Cada predictor es responsable de usar solo datos previos a `on_date`.
    """
    ordered = sorted(matches, key=lambda m: m.date)
    if not ordered:
        raise ValueError("no hay partidos para evaluar")

    bs = rp = ll = 0.0
    for m in ordered:
        pred = predictor.predict(m.home, m.away, neutral=m.neutral, on_date=m.date)
        probs = pred.probs
        bs += brier_score(probs, m.outcome)
        rp += rps(probs, m.outcome)
        ll += log_loss(probs, m.outcome)

    n = len(ordered)
    return EvalResult(n_matches=n, brier=bs / n, rps=rp / n, log_loss=ll / n)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_backtest.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/evaluate/backtest.py tests/test_backtest.py
git commit -m "feat: add walk-forward backtest harness" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Script de baseline (la vara, contra datos reales)

**Files:**
- Create: `scripts/run_baseline.py`

- [ ] **Step 1: Escribir el script**

`scripts/run_baseline.py`:

```python
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
```

- [ ] **Step 2: Correr el script**

Run: `.\.venv\Scripts\python.exe scripts\run_baseline.py`
Expected: imprime las tres métricas sobre 40000+ partidos. RPS debería rondar ~0.22–0.24 (la vara: cualquier nivel posterior tiene que bajar este número).

- [ ] **Step 3: Correr toda la suite de tests**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS — todos los tests de las Tasks 2-8 en verde.

- [ ] **Step 4: Commit**

```powershell
git add scripts/run_baseline.py
git commit -m "feat: add uniform baseline run script" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite.
- `scripts\run_baseline.py` imprime Brier/RPS/log-loss del uniforme sobre los datos reales.
- Hay un valor de RPS de referencia anotado para comparar los próximos niveles.

Siguiente: **Plan 2 — ranking FIFA + Elo propio + calibración.**
