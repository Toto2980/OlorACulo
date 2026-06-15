# Oráculo Mundial 2026 — Plan 2: Elo propio + calibración

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar un modelo Elo calculado desde `results.csv`, convertirlo a probabilidades 1-X-2 con el modelo Davidson, evaluarlo walk-forward, y calibrar sus parámetros (K, ventaja de localía, ν) minimizando RPS — para batir la vara del uniforme (RPS 0.2399).

**Architecture:** Matemática pura de Elo en `oraculo/ratings/elo.py` (sin estado, fácil de testear). Un `EloModel` con estado en `oraculo/models/elo.py` que mantiene el diccionario de ratings, implementa el protocolo `Predictor` y además expone `observe()`/`reset()` para el backtest streaming. Un evaluador walk-forward genérico en `oraculo/evaluate/walk_forward.py` (predecir-luego-observar, con período de warmup). Calibración por grid search en `oraculo/calibrate/elo.py`.

**Tech Stack:** Python 3.11+, stdlib `math`/`itertools`, pytest. Reusa `Match`, `MatchPrediction`, métricas y `EvalResult` de la Fase 1.

**Decomposición:** Plan 2 de la serie. La Fase 1 (cimientos) ya está completa: existen `oraculo/match.py`, `oraculo/ingest/results.py`, `oraculo/models/base.py` (con `OUTCOMES`, `MatchPrediction`, protocolo `Predictor` donde `on_date` es la fecha de corte), `oraculo/models/uniform.py`, `oraculo/evaluate/metrics.py` (`brier_score`, `rps`, `log_loss`), `oraculo/evaluate/backtest.py` (`backtest`, `EvalResult`). Vara actual: uniforme RPS=0.2399 sobre 49.417 partidos.

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Paths relativos a esa carpeta.

**Convenciones (Windows/PowerShell):**
- Correr python/pytest SIEMPRE con `.\.venv\Scripts\python.exe` (nunca `python` pelado).
- Commits con doble `-m` para el trailer de coautoría.

**Fundamento matemático (referencia para todas las tasks):**
- Expectativa Elo: `We = 1 / (1 + 10^(-Δ/400))`, donde `Δ` = diferencia de rating efectiva (incluye ventaja de localía).
- Multiplicador por margen (World Football Elo): `G=1` si |margen|≤1, `G=1.5` si =2, `G=(11+|margen|)/8` si ≥3.
- Actualización: `R_home += K·G·(W − We)`, `R_away -= K·G·(W − We)`, con `W` = 1 (gana local) / 0.5 (empate) / 0 (pierde).
- Conversión a 1-X-2 (modelo Davidson, 1970): con `γ = 10^(Δ/400)` y `ν ≥ 0` el parámetro de empate:
  `P(local) = γ/D`, `P(empate) = ν·√γ/D`, `P(visit) = 1/D`, con `D = γ + 1 + ν·√γ`. Suma exactamente 1.

---

## Task 1: Matemática pura de Elo

**Files:**
- Create: `oraculo/ratings/__init__.py` (EMPTY)
- Create: `oraculo/ratings/elo.py`
- Test: `tests/test_elo_math.py`

- [ ] **Step 1: Write the failing test** `tests/test_elo_math.py`:

```python
import pytest

from oraculo.ratings.elo import expected_score, goal_multiplier, update_ratings


def test_expected_score_even():
    assert expected_score(0.0) == pytest.approx(0.5)


def test_expected_score_400_diff():
    # 400 puntos de ventaja ~ 10:1 en expectativa
    assert expected_score(400.0) == pytest.approx(1 / 1.1)


def test_goal_multiplier():
    assert goal_multiplier(0) == 1.0
    assert goal_multiplier(1) == 1.0
    assert goal_multiplier(-1) == 1.0
    assert goal_multiplier(2) == 1.5
    assert goal_multiplier(3) == pytest.approx(14 / 8)
    assert goal_multiplier(4) == pytest.approx(15 / 8)


def test_update_even_draw_no_change():
    # ratings iguales, neutral, empate -> no cambia nada
    new_h, new_a = update_ratings(1500, 1500, 1, 1, k=20, home_adv=65, neutral=True)
    assert new_h == pytest.approx(1500)
    assert new_a == pytest.approx(1500)


def test_update_zero_sum():
    new_h, new_a = update_ratings(1500, 1500, 2, 0, k=20, home_adv=0, neutral=True)
    assert (new_h - 1500) == pytest.approx(-(new_a - 1500))


def test_update_upset_moves_more_than_expected_win():
    # local fuerte (1800) vs débil (1500), cancha neutral
    # si el favorito gana por 1 -> cambio chico
    fav_win_h, _ = update_ratings(1800, 1500, 1, 0, k=20, home_adv=0, neutral=True)
    # si el débil da el batacazo -> cambio grande para el local (pierde mucho)
    upset_h, _ = update_ratings(1800, 1500, 0, 1, k=20, home_adv=0, neutral=True)
    assert abs(upset_h - 1800) > abs(fav_win_h - 1800)
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.ratings.elo'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_elo_math.py -v`
Expected: FAIL (collection error, module not found).

- [ ] **Step 3: Create `oraculo/ratings/__init__.py` EMPTY, then implement `oraculo/ratings/elo.py`:**

```python
from __future__ import annotations

import math


def expected_score(rating_diff: float) -> float:
    """Expectativa Elo (incluye medio empate) para una diferencia de rating efectiva."""
    return 1.0 / (1.0 + 10 ** (-rating_diff / 400.0))


def goal_multiplier(margin: int) -> float:
    """Multiplicador por margen de victoria (estilo World Football Elo)."""
    m = abs(margin)
    if m <= 1:
        return 1.0
    if m == 2:
        return 1.5
    return (11 + m) / 8.0


def update_ratings(
    r_home: float,
    r_away: float,
    home_goals: int,
    away_goals: int,
    *,
    k: float,
    home_adv: float,
    neutral: bool = False,
) -> tuple[float, float]:
    """Devuelve (nuevo_rating_local, nuevo_rating_visitante) tras un partido."""
    dr = r_home - r_away + (0.0 if neutral else home_adv)
    we = expected_score(dr)
    if home_goals > away_goals:
        w = 1.0
    elif home_goals < away_goals:
        w = 0.0
    else:
        w = 0.5
    g = goal_multiplier(home_goals - away_goals)
    delta = k * g * (w - we)
    return r_home + delta, r_away - delta


def davidson_probs(rating_diff: float, nu: float) -> tuple[float, float, float]:
    """Probabilidades (local, empate, visitante) via modelo Davidson.

    `nu` >= 0 controla la frecuencia de empates (nu=0 -> sin empates).
    `rating_diff` es la diferencia efectiva (ya incluye la ventaja de localía).
    """
    gamma = 10 ** (rating_diff / 400.0)
    root = math.sqrt(gamma)
    denom = gamma + 1.0 + nu * root
    p_home = gamma / denom
    p_draw = nu * root / denom
    p_away = 1.0 / denom
    return p_home, p_draw, p_away
```

(Nota: `davidson_probs` se incluye acá porque es matemática pura de rating→probabilidad; se testea en la Task 2.)

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_elo_math.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/ratings/__init__.py oraculo/ratings/elo.py tests/test_elo_math.py
git commit -m "feat: add pure Elo math (expected score, goal multiplier, update)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Conversión Davidson a probabilidades 1-X-2

**Files:**
- Modify: `oraculo/ratings/elo.py` (la función `davidson_probs` YA fue creada en la Task 1; acá solo se agregan sus tests)
- Test: `tests/test_davidson.py`

- [ ] **Step 1: Write the failing test** `tests/test_davidson.py`:

```python
import pytest

from oraculo.ratings.elo import davidson_probs


def test_sums_to_one():
    for dr in (-300.0, -50.0, 0.0, 75.0, 500.0):
        p_home, p_draw, p_away = davidson_probs(dr, nu=0.6)
        assert p_home + p_draw + p_away == pytest.approx(1.0)


def test_even_teams_symmetric():
    p_home, p_draw, p_away = davidson_probs(0.0, nu=0.6)
    assert p_home == pytest.approx(p_away)
    assert p_draw == pytest.approx(0.6 / 2.6)
    assert p_home == pytest.approx(1.0 / 2.6)


def test_nu_zero_means_no_draws():
    p_home, p_draw, p_away = davidson_probs(120.0, nu=0.0)
    assert p_draw == pytest.approx(0.0)
    assert p_home + p_away == pytest.approx(1.0)


def test_positive_diff_favors_home():
    p_home, _, p_away = davidson_probs(200.0, nu=0.6)
    assert p_home > p_away
```

- [ ] **Step 2: Run it, confirm it PASSES** (la función ya existe de la Task 1):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_davidson.py -v`
Expected: PASS (4 passed). Si alguno falla, revisar la implementación de `davidson_probs` en `oraculo/ratings/elo.py` contra la fórmula del header.

- [ ] **Step 3: (No hay implementación nueva — `davidson_probs` se hizo en la Task 1.)**

- [ ] **Step 4: Commit:**

```powershell
git add tests/test_davidson.py
git commit -m "test: cover Davidson 1X2 probability conversion" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: EloModel (predictor con estado)

**Files:**
- Create: `oraculo/models/elo.py`
- Test: `tests/test_elo_model.py`

- [ ] **Step 1: Write the failing test** `tests/test_elo_model.py`:

```python
import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel


def _m(home, away, hg, ag, *, neutral=False, d=1):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=neutral,
    )


def test_unseen_team_uses_initial_rating():
    model = EloModel(EloConfig(initial_rating=1500))
    assert model.rating("Atlantis") == 1500


def test_observe_winner_gains_loser_loses():
    model = EloModel()
    model.observe(_m("A", "B", 3, 0, neutral=True))
    assert model.rating("A") > 1500
    assert model.rating("B") < 1500


def test_predict_returns_valid_distribution():
    model = EloModel()
    pred = model.predict("A", "B")
    assert pred.p_home + pred.p_draw + pred.p_away == pytest.approx(1.0)


def test_stronger_team_more_likely():
    model = EloModel()
    # A le gana seguido a B -> A sube
    for d in range(1, 6):
        model.observe(_m("A", "B", 2, 0, neutral=True, d=d))
    pred = model.predict("A", "B", neutral=True)
    assert pred.p_home > pred.p_away


def test_reset_clears_ratings():
    model = EloModel()
    model.observe(_m("A", "B", 1, 0))
    model.reset()
    assert model.rating("A") == model.config.initial_rating


def test_fit_processes_in_date_order():
    model = EloModel()
    matches = [_m("A", "B", 0, 1, d=3), _m("A", "B", 5, 0, d=1)]
    model.fit(matches)
    # tras procesar ambos en orden de fecha, A jugó dos partidos; rating definido
    assert "A" in model.ratings and "B" in model.ratings
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.models.elo'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_elo_model.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `oraculo/models/elo.py`:**

```python
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.ratings.elo import davidson_probs, update_ratings


@dataclass
class EloConfig:
    k: float = 20.0
    home_adv: float = 65.0
    nu: float = 0.6
    initial_rating: float = 1500.0


class EloModel:
    """Nivel 2: Elo calculado desde resultados. Implementa el protocolo Predictor
    y además expone observe()/reset() para el backtest walk-forward."""

    name = "elo"

    def __init__(self, config: Optional[EloConfig] = None) -> None:
        self.config = config or EloConfig()
        self.ratings: dict[str, float] = {}

    def reset(self) -> None:
        self.ratings = {}

    def rating(self, team: str) -> float:
        return self.ratings.get(team, self.config.initial_rating)

    def observe(self, match: Match) -> None:
        new_home, new_away = update_ratings(
            self.rating(match.home),
            self.rating(match.away),
            match.home_goals,
            match.away_goals,
            k=self.config.k,
            home_adv=self.config.home_adv,
            neutral=match.neutral,
        )
        self.ratings[match.home] = new_home
        self.ratings[match.away] = new_away

    def fit(self, matches: Iterable[Match]) -> "EloModel":
        for m in sorted(matches, key=lambda m: m.date):
            self.observe(m)
        return self

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date: datetime.date | None = None,
    ) -> MatchPrediction:
        dr = self.rating(home) - self.rating(away)
        if not neutral:
            dr += self.config.home_adv
        p_home, p_draw, p_away = davidson_probs(dr, self.config.nu)
        return MatchPrediction(p_home=p_home, p_draw=p_draw, p_away=p_away)
```

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_elo_model.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/models/elo.py tests/test_elo_model.py
git commit -m "feat: add stateful EloModel predictor (level 2)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Evaluador walk-forward (para modelos con estado)

**Files:**
- Create: `oraculo/evaluate/walk_forward.py`
- Test: `tests/test_walk_forward.py`

- [ ] **Step 1: Write the failing test** `tests/test_walk_forward.py`:

```python
import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloModel
from oraculo.evaluate.backtest import EvalResult
from oraculo.evaluate.walk_forward import walk_forward


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def test_returns_eval_result():
    matches = [_m("A", "B", 1, 0, 1), _m("A", "B", 2, 1, 2)]
    res = walk_forward(EloModel(), matches)
    assert isinstance(res, EvalResult)
    assert res.n_matches == 2


def test_eval_from_filters_warmup():
    matches = [
        _m("A", "B", 1, 0, 1),
        _m("A", "B", 1, 0, 2),
        _m("A", "B", 1, 0, 3),
    ]
    res = walk_forward(EloModel(), matches, eval_from=datetime.date(2020, 1, 2))
    # solo se evalúan los partidos del 2 y 3 de enero (2), el del 1 es warmup
    assert res.n_matches == 2


def test_empty_eval_window_raises():
    matches = [_m("A", "B", 1, 0, 1)]
    with pytest.raises(ValueError):
        walk_forward(EloModel(), matches, eval_from=datetime.date(2021, 1, 1))


def test_predicts_before_observing():
    # El primer partido evaluado siempre se predice con ratings iniciales (iguales),
    # asi que para cancha neutral p_home == p_away en ese primer partido.
    matches = [_m("A", "B", 5, 0, 1)]
    res = walk_forward(EloModel(), matches)
    # con un solo partido evaluado desde estado inicial, RPS es el de teams parejos
    # (no 0): confirmamos simplemente que produjo una metrica finita > 0
    assert res.rps > 0
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.evaluate.walk_forward'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_walk_forward.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `oraculo/evaluate/walk_forward.py`:**

```python
from __future__ import annotations

import datetime
from typing import Iterable, Protocol

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.evaluate.metrics import brier_score, rps, log_loss
from oraculo.evaluate.backtest import EvalResult


class StatefulModel(Protocol):
    """Modelo que aprende incrementalmente: predice y luego observa cada partido."""

    def predict(
        self,
        home: str,
        away: str,
        *,
        neutral: bool = False,
        on_date: datetime.date | None = None,
    ) -> MatchPrediction: ...

    def observe(self, match: Match) -> None: ...

    def reset(self) -> None: ...


def walk_forward(
    model: StatefulModel,
    matches: Iterable[Match],
    *,
    eval_from: datetime.date | None = None,
) -> EvalResult:
    """Backtest walk-forward: por cada partido en orden cronológico, predecir con el
    estado previo y luego observar el resultado real (sin fuga de información).

    Solo se acumulan métricas para partidos con fecha >= eval_from; los anteriores
    sirven de warmup. Si eval_from es None, se evalúan todos.
    """
    ordered = sorted(matches, key=lambda m: m.date)
    model.reset()

    bs = rp = ll = 0.0
    n = 0
    for m in ordered:
        if eval_from is None or m.date >= eval_from:
            probs = model.predict(m.home, m.away, neutral=m.neutral, on_date=m.date).probs
            bs += brier_score(probs, m.outcome)
            rp += rps(probs, m.outcome)
            ll += log_loss(probs, m.outcome)
            n += 1
        model.observe(m)

    if n == 0:
        raise ValueError("no hay partidos para evaluar en el rango dado")
    return EvalResult(n_matches=n, brier=bs / n, rps=rp / n, log_loss=ll / n)
```

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_walk_forward.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/evaluate/walk_forward.py tests/test_walk_forward.py
git commit -m "feat: add walk-forward evaluator for stateful models" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Calibración por grid search

**Files:**
- Create: `oraculo/calibrate/__init__.py` (EMPTY)
- Create: `oraculo/calibrate/elo.py`
- Test: `tests/test_calibrate_elo.py`

- [ ] **Step 1: Write the failing test** `tests/test_calibrate_elo.py`:

```python
import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel
from oraculo.evaluate.walk_forward import walk_forward
from oraculo.calibrate.elo import calibrate_elo, CalibrationResult


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def _matches():
    # A le gana sistematicamente a B
    return [_m("A", "B", 2, 0, d) for d in range(1, 11)]


def test_returns_calibration_result():
    res = calibrate_elo(
        _matches(),
        k_values=[20.0],
        home_adv_values=[0.0],
        nu_values=[0.6],
    )
    assert isinstance(res, CalibrationResult)
    assert isinstance(res.config, EloConfig)


def test_picks_grid_point_with_lowest_rps():
    matches = _matches()
    grid_nu = [0.0, 0.6, 2.0]
    res = calibrate_elo(
        matches,
        k_values=[20.0],
        home_adv_values=[0.0],
        nu_values=grid_nu,
    )
    # el RPS reportado debe coincidir con el walk_forward de la config elegida
    expected = walk_forward(EloModel(res.config), matches)
    assert res.rps == pytest.approx(expected.rps)
    # y debe ser el minimo sobre los puntos del grid
    best_manual = min(
        walk_forward(EloModel(EloConfig(k=20.0, home_adv=0.0, nu=nu)), matches).rps
        for nu in grid_nu
    )
    assert res.rps == pytest.approx(best_manual)


def test_empty_grid_raises():
    with pytest.raises(ValueError):
        calibrate_elo(_matches(), k_values=[], home_adv_values=[0.0], nu_values=[0.6])
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.calibrate.elo'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calibrate_elo.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Create `oraculo/calibrate/__init__.py` EMPTY, then implement `oraculo/calibrate/elo.py`:**

```python
from __future__ import annotations

import datetime
import itertools
from dataclasses import dataclass
from typing import Optional, Sequence

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel
from oraculo.evaluate.walk_forward import walk_forward


@dataclass
class CalibrationResult:
    config: EloConfig
    rps: float


def calibrate_elo(
    matches: Sequence[Match],
    *,
    k_values: Sequence[float],
    home_adv_values: Sequence[float],
    nu_values: Sequence[float],
    eval_from: datetime.date | None = None,
) -> CalibrationResult:
    """Grid search: devuelve la EloConfig que minimiza el RPS walk-forward."""
    matches = list(matches)
    best: Optional[CalibrationResult] = None
    for k, home_adv, nu in itertools.product(k_values, home_adv_values, nu_values):
        cfg = EloConfig(k=k, home_adv=home_adv, nu=nu)
        res = walk_forward(EloModel(cfg), matches, eval_from=eval_from)
        if best is None or res.rps < best.rps:
            best = CalibrationResult(config=cfg, rps=res.rps)
    if best is None:
        raise ValueError("el grid de calibración está vacío")
    return best
```

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calibrate_elo.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/calibrate/__init__.py oraculo/calibrate/elo.py tests/test_calibrate_elo.py
git commit -m "feat: add Elo grid-search calibration" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Scripts — comparar Elo contra la vara y calibrar

**Files:**
- Create: `scripts/run_elo.py`
- Create: `scripts/calibrate_elo.py`

- [ ] **Step 1: Write `scripts/run_elo.py`:**

```python
"""Compara el Elo (config por defecto) contra el uniforme sobre la MISMA ventana
de evaluación (partidos desde EVAL_FROM; lo anterior es warmup del Elo)."""
from __future__ import annotations

import datetime
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.models.elo import EloModel
from oraculo.evaluate.backtest import backtest
from oraculo.evaluate.walk_forward import walk_forward

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"
EVAL_FROM = datetime.date(2010, 1, 1)


def main() -> None:
    matches = load_results(DATA)
    eval_set = [m for m in matches if m.date >= EVAL_FROM]

    uni = backtest(UniformPredictor(), eval_set)
    elo = walk_forward(EloModel(), matches, eval_from=EVAL_FROM)

    print(f"Ventana de evaluación: desde {EVAL_FROM} ({uni.n_matches} partidos)")
    print(f"  Uniforme  RPS: {uni.rps:.4f}  Brier: {uni.brier:.4f}  LogLoss: {uni.log_loss:.4f}")
    print(f"  Elo       RPS: {elo.rps:.4f}  Brier: {elo.brier:.4f}  LogLoss: {elo.log_loss:.4f}")
    delta = uni.rps - elo.rps
    print(f"  Mejora de RPS del Elo sobre la vara: {delta:+.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it:**

Run: `.\.venv\Scripts\python.exe scripts\run_elo.py`
Expected: imprime ambas métricas sobre la misma ventana. El RPS del Elo debe ser **menor** que el del uniforme (mejora positiva). Anotar los números.

- [ ] **Step 3: Write `scripts/calibrate_elo.py`:**

```python
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
```

- [ ] **Step 4: Run it:**

Run: `.\.venv\Scripts\python.exe scripts\calibrate_elo.py`
Expected: imprime la mejor config y su RPS. El RPS calibrado debe ser ≤ al del Elo por defecto y claramente menor que la vara. Anotar la config ganadora (estos números alimentan la Fase 3 y el Monte Carlo).

- [ ] **Step 5: Run the FULL suite y commit:**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests (Fase 1 + Fase 2) en verde.

```powershell
git add scripts/run_elo.py scripts/calibrate_elo.py
git commit -m "feat: add Elo-vs-baseline comparison and calibration scripts" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite (Fase 1 + Fase 2).
- `scripts\run_elo.py` muestra que el Elo (config por defecto) tiene **RPS menor** que el uniforme sobre la misma ventana.
- `scripts\calibrate_elo.py` reporta la mejor config (K, home_adv, ν) y su RPS, anotada para usar en fases siguientes.

Siguiente: **Plan 3 — modelo de goles Poisson + corrección Dixon-Coles.**
