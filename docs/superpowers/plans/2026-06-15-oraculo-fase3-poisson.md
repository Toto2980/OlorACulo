# Oráculo Mundial 2026 — Plan 3: Poisson + Dixon-Coles

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar un modelo de goles: cada equipo tiene ataque y defensa (ratings incrementales tipo Elo pero para goles) que dan los goles esperados λ de cada lado; con eso se arma una matriz de resultados Poisson con la corrección de bajos marcadores de Dixon-Coles, de la que salen las probabilidades 1-X-2 **y** la `score_matrix` que necesitará el Monte Carlo. Calibrar y batir al Elo (RPS 0.1745).

**Architecture:** Matemática pura en `oraculo/ratings/poisson.py` (pmf de Poisson, corrección τ de Dixon-Coles, goles esperados, matriz de resultados, probabilidades 1-X-2). Un `PoissonModel` con estado en `oraculo/models/poisson.py` que mantiene diccionarios de ataque/defensa, los actualiza por descenso de gradiente sobre la log-verosimilitud Poisson en cada partido (`observe`), y predice poblando `xg_home`/`xg_away`/`score_matrix` de `MatchPrediction`. Reusa el `walk_forward` y la calibración por grid de la Fase 2.

**Tech Stack:** Python 3.11+, numpy (ya es dependencia), stdlib `math`/`itertools`, pytest.

**Decomposición:** Plan 3 de la serie. Fases 1 y 2 completas. Existe: `oraculo/match.py`, `oraculo/models/base.py` (`MatchPrediction` con campos `xg_home`/`xg_away`/`score_matrix`; protocolo `Predictor`), `oraculo/models/elo.py` (patrón de modelo con estado: `observe`/`predict`/`fit`/`reset`, implementa Predictor), `oraculo/evaluate/walk_forward.py` (`walk_forward(model, matches, *, eval_from)`, protocolo `StatefulModel`), `oraculo/evaluate/backtest.py` (`backtest`, `EvalResult`), `oraculo/calibrate/elo.py` (patrón de grid search). Vara: uniforme RPS 0.2391; Elo calibrado RPS 0.1745 (ventana desde 2010, 15.829 partidos).

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Paths relativos.

**Convenciones (Windows/PowerShell):**
- python/pytest SIEMPRE con `.\.venv\Scripts\python.exe` (nunca `python` pelado).
- Commits con doble `-m` para el trailer de coautoría.

**Fundamento matemático (referencia para todas las tasks):**
- Goles esperados (log-lineal, estilo Dixon-Coles): `log(λ_local) = base + ventaja_localía + ataque[local] − defensa[visit]`; `log(λ_visit) = base + ataque[visit] − defensa[local]`. En cancha neutral la ventaja de localía es 0.
- Actualización online (SGD sobre la log-verosimilitud Poisson, gradiente `(y−λ)` por el log-link): con `e_local = goles_local − λ_local`, `e_visit = goles_visit − λ_visit` y tasa `lr`:
  `ataque[local] += lr·e_local`; `defensa[visit] −= lr·e_local`; `ataque[visit] += lr·e_visit`; `defensa[local] −= lr·e_visit`.
- Matriz de resultados: `P(local=i, visit=j) = Poisson(i;λ_local)·Poisson(j;λ_visit)·τ(i,j)`, con la corrección Dixon-Coles `τ`:
  `τ(0,0)=1−λ_local·λ_visit·ρ`, `τ(0,1)=1+λ_local·ρ`, `τ(1,0)=1+λ_visit·ρ`, `τ(1,1)=1−ρ`, y `τ=1` en el resto. La matriz se normaliza para que sume 1.
- De la matriz: `P(local)=Σ_{i>j}`, `P(empate)=Σ_{i=j}`, `P(visit)=Σ_{i<j}`.

---

## Task 1: Matemática pura de Poisson y Dixon-Coles

**Files:**
- Create: `oraculo/ratings/poisson.py`
- Test: `tests/test_poisson_math.py`

- [ ] **Step 1: Write the failing test** `tests/test_poisson_math.py`:

```python
import math

import pytest

from oraculo.ratings.poisson import poisson_pmf, dc_tau, expected_goals


def test_poisson_pmf_known_values():
    assert poisson_pmf(0, 1.0) == pytest.approx(math.exp(-1.0))
    assert poisson_pmf(1, 2.0) == pytest.approx(math.exp(-2.0) * 2.0)
    assert poisson_pmf(2, 1.5) == pytest.approx(math.exp(-1.5) * 1.5 ** 2 / 2)


def test_dc_tau_corrections():
    lh, la, rho = 1.5, 1.2, -0.1
    assert dc_tau(0, 0, lh, la, rho) == pytest.approx(1 - lh * la * rho)
    assert dc_tau(0, 1, lh, la, rho) == pytest.approx(1 + lh * rho)
    assert dc_tau(1, 0, lh, la, rho) == pytest.approx(1 + la * rho)
    assert dc_tau(1, 1, lh, la, rho) == pytest.approx(1 - rho)


def test_dc_tau_identity_elsewhere():
    assert dc_tau(2, 3, 1.5, 1.2, -0.1) == 1.0
    assert dc_tau(0, 2, 1.5, 1.2, -0.1) == 1.0


def test_expected_goals_neutral_baseline():
    base = math.log(1.3)
    lh, la = expected_goals(0.0, 0.0, 0.0, 0.0, baseline=base, home_adv=0.3, neutral=True)
    assert lh == pytest.approx(1.3)
    assert la == pytest.approx(1.3)


def test_expected_goals_home_advantage():
    base = math.log(1.3)
    lh, la = expected_goals(0.0, 0.0, 0.0, 0.0, baseline=base, home_adv=0.3, neutral=False)
    assert lh == pytest.approx(1.3 * math.exp(0.3))
    assert la == pytest.approx(1.3)


def test_expected_goals_attack_raises_lambda():
    base = math.log(1.3)
    lh, _ = expected_goals(0.5, 0.0, 0.0, 0.0, baseline=base, home_adv=0.0, neutral=True)
    assert lh == pytest.approx(1.3 * math.exp(0.5))
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.ratings.poisson'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_poisson_math.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `oraculo/ratings/poisson.py`** (incluye también `score_matrix` y `outcome_probs`, que se testean en la Task 2):

```python
from __future__ import annotations

import math

import numpy as np


def poisson_pmf(k: int, lam: float) -> float:
    """Probabilidad de k eventos para una Poisson de media lam."""
    return math.exp(-lam) * lam ** k / math.factorial(k)


def dc_tau(i: int, j: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Corrección Dixon-Coles para marcadores bajos."""
    if i == 0 and j == 0:
        return 1.0 - lam_home * lam_away * rho
    if i == 0 and j == 1:
        return 1.0 + lam_home * rho
    if i == 1 and j == 0:
        return 1.0 + lam_away * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def expected_goals(
    att_home: float,
    def_home: float,
    att_away: float,
    def_away: float,
    *,
    baseline: float,
    home_adv: float,
    neutral: bool = False,
) -> tuple[float, float]:
    """Goles esperados (λ_local, λ_visit) a partir de ataque/defensa de cada equipo."""
    eta_home = baseline + att_home - def_away + (0.0 if neutral else home_adv)
    eta_away = baseline + att_away - def_home
    return math.exp(eta_home), math.exp(eta_away)


def score_matrix(
    lam_home: float,
    lam_away: float,
    *,
    rho: float,
    max_goals: int = 10,
) -> np.ndarray:
    """Matriz normalizada P(local=i, visit=j) con corrección Dixon-Coles."""
    home_pmf = np.array([poisson_pmf(i, lam_home) for i in range(max_goals + 1)])
    away_pmf = np.array([poisson_pmf(j, lam_away) for j in range(max_goals + 1)])
    m = np.outer(home_pmf, away_pmf)
    m[0, 0] *= 1.0 - lam_home * lam_away * rho
    m[0, 1] *= 1.0 + lam_home * rho
    m[1, 0] *= 1.0 + lam_away * rho
    m[1, 1] *= 1.0 - rho
    return m / m.sum()


def outcome_probs(matrix: np.ndarray) -> tuple[float, float, float]:
    """(P(local), P(empate), P(visit)) a partir de la matriz de resultados."""
    home = float(np.tril(matrix, -1).sum())  # i > j
    draw = float(np.trace(matrix))           # i == j
    away = float(np.triu(matrix, 1).sum())   # i < j
    return home, draw, away
```

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_poisson_math.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/ratings/poisson.py tests/test_poisson_math.py
git commit -m "feat: add Poisson/Dixon-Coles pure math (pmf, tau, expected goals)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Matriz de resultados y probabilidades 1-X-2

**Files:**
- Modify: `oraculo/ratings/poisson.py` (`score_matrix` y `outcome_probs` YA fueron creadas en la Task 1; acá solo se agregan tests)
- Test: `tests/test_score_matrix.py`

- [ ] **Step 1: Write the failing test** `tests/test_score_matrix.py`:

```python
import pytest

from oraculo.ratings.poisson import score_matrix, outcome_probs


def test_matrix_sums_to_one():
    m = score_matrix(1.5, 1.2, rho=-0.05, max_goals=10)
    assert m.sum() == pytest.approx(1.0)


def test_matrix_shape():
    m = score_matrix(1.5, 1.2, rho=-0.05, max_goals=8)
    assert m.shape == (9, 9)


def test_outcome_probs_sum_to_one():
    m = score_matrix(1.7, 1.1, rho=-0.05, max_goals=10)
    p_home, p_draw, p_away = outcome_probs(m)
    assert p_home + p_draw + p_away == pytest.approx(1.0)


def test_equal_lambdas_symmetric_when_no_correction():
    m = score_matrix(1.4, 1.4, rho=0.0, max_goals=10)
    p_home, p_draw, p_away = outcome_probs(m)
    assert p_home == pytest.approx(p_away)
    assert p_draw > 0


def test_higher_home_lambda_favors_home():
    m = score_matrix(2.2, 0.8, rho=-0.05, max_goals=10)
    p_home, _, p_away = outcome_probs(m)
    assert p_home > p_away
```

- [ ] **Step 2: Run it, confirm it PASSES** (las funciones ya existen de la Task 1):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_score_matrix.py -v`
Expected: PASS (5 passed). Si algo falla, revisar `score_matrix`/`outcome_probs` en `oraculo/ratings/poisson.py` contra el header.

- [ ] **Step 3: (No hay implementación nueva — se hizo en la Task 1.)**

- [ ] **Step 4: Commit:**

```powershell
git add tests/test_score_matrix.py
git commit -m "test: cover score matrix and 1X2 outcome probabilities" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: PoissonModel (predictor de goles con estado)

**Files:**
- Create: `oraculo/models/poisson.py`
- Test: `tests/test_poisson_model.py`

- [ ] **Step 1: Write the failing test** `tests/test_poisson_model.py`:

```python
import datetime
import math

import pytest

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel


def _m(home, away, hg, ag, *, neutral=True, d=1):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=neutral,
    )


def test_unseen_teams_predict_baseline_goals():
    cfg = PoissonConfig(baseline=math.log(1.3), home_adv=0.0)
    model = PoissonModel(cfg)
    pred = model.predict("A", "B", neutral=True)
    assert pred.xg_home == pytest.approx(1.3)
    assert pred.xg_away == pytest.approx(1.3)


def test_predict_returns_valid_distribution_and_matrix():
    model = PoissonModel()
    pred = model.predict("A", "B")
    assert pred.p_home + pred.p_draw + pred.p_away == pytest.approx(1.0)
    assert pred.xg_home is not None and pred.xg_away is not None
    assert pred.score_matrix is not None
    assert pred.score_matrix.shape == (model.config.max_goals + 1, model.config.max_goals + 1)


def test_observing_goals_raises_attack():
    model = PoissonModel()
    base_xg = model.predict("A", "B", neutral=True).xg_home
    for d in range(1, 8):
        model.observe(_m("A", "B", 4, 0, neutral=True, d=d))
    new_xg = model.predict("A", "B", neutral=True).xg_home
    assert new_xg > base_xg


def test_strong_attacker_more_likely_to_win():
    model = PoissonModel()
    for d in range(1, 8):
        model.observe(_m("A", "B", 4, 0, neutral=True, d=d))
    pred = model.predict("A", "B", neutral=True)
    assert pred.p_home > pred.p_away


def test_reset_clears_strengths():
    model = PoissonModel()
    model.observe(_m("A", "B", 3, 0))
    model.reset()
    assert model.attack == {} and model.defense == {}
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.models.poisson'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_poisson_model.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `oraculo/models/poisson.py`:**

```python
from __future__ import annotations

import datetime
import math
from dataclasses import dataclass
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import expected_goals, outcome_probs, score_matrix


@dataclass
class PoissonConfig:
    lr: float = 0.05
    baseline: float = math.log(1.3)
    home_adv: float = 0.25
    rho: float = -0.05
    max_goals: int = 10
    initial_strength: float = 0.0


class PoissonModel:
    """Nivel 4: modelo de goles. Ataque/defensa incrementales -> λ por lado ->
    matriz Poisson con corrección Dixon-Coles. Implementa Predictor y expone
    observe()/reset() para el walk-forward.

    `predict` usa los ratings ACTUALES; `on_date` no se usa internamente (el
    walk_forward garantiza no-fuga prediciendo antes de observar; para predicción
    en vivo, llamar a `fit` con los partidos previos al corte)."""

    name = "poisson"

    def __init__(self, config: Optional[PoissonConfig] = None) -> None:
        self.config = config or PoissonConfig()
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}

    def reset(self) -> None:
        self.attack = {}
        self.defense = {}

    def _att(self, team: str) -> float:
        return self.attack.get(team, self.config.initial_strength)

    def _def(self, team: str) -> float:
        return self.defense.get(team, self.config.initial_strength)

    def _expected(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        return expected_goals(
            self._att(home),
            self._def(home),
            self._att(away),
            self._def(away),
            baseline=self.config.baseline,
            home_adv=self.config.home_adv,
            neutral=neutral,
        )

    def observe(self, match: Match) -> None:
        lam_home, lam_away = self._expected(match.home, match.away, match.neutral)
        e_home = match.home_goals - lam_home
        e_away = match.away_goals - lam_away
        lr = self.config.lr
        # leer todos los valores originales antes de mutar (cada uno se toca una vez)
        self.attack[match.home] = self._att(match.home) + lr * e_home
        self.defense[match.away] = self._def(match.away) - lr * e_home
        self.attack[match.away] = self._att(match.away) + lr * e_away
        self.defense[match.home] = self._def(match.home) - lr * e_away

    def fit(self, matches: Iterable[Match]) -> "PoissonModel":
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
        lam_home, lam_away = self._expected(home, away, neutral)
        matrix = score_matrix(
            lam_home, lam_away, rho=self.config.rho, max_goals=self.config.max_goals
        )
        p_home, p_draw, p_away = outcome_probs(matrix)
        return MatchPrediction(
            p_home=p_home,
            p_draw=p_draw,
            p_away=p_away,
            xg_home=lam_home,
            xg_away=lam_away,
            score_matrix=matrix,
        )
```

(Nota: `field` no se usa; no lo importes si tu linter se queja — la lista de imports de arriba es referencia, dejá solo lo que uses.)

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_poisson_model.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/models/poisson.py tests/test_poisson_model.py
git commit -m "feat: add stateful PoissonModel goal predictor (level 4)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Calibración del Poisson por grid search

**Files:**
- Create: `oraculo/calibrate/poisson.py`
- Test: `tests/test_calibrate_poisson.py`

- [ ] **Step 1: Write the failing test** `tests/test_calibrate_poisson.py`:

```python
import datetime

import pytest

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.walk_forward import walk_forward
from oraculo.calibrate.poisson import calibrate_poisson, PoissonCalibrationResult


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def _matches():
    return [_m("A", "B", 3, 0, d) for d in range(1, 13)]


def test_returns_result():
    res = calibrate_poisson(
        _matches(),
        lr_values=[0.05],
        baseline_values=[0.26],
        home_adv_values=[0.0],
        rho_values=[-0.05],
    )
    assert isinstance(res, PoissonCalibrationResult)
    assert isinstance(res.config, PoissonConfig)


def test_picks_lowest_rps():
    matches = _matches()
    lr_grid = [0.02, 0.08, 0.2]
    res = calibrate_poisson(
        matches,
        lr_values=lr_grid,
        baseline_values=[0.26],
        home_adv_values=[0.0],
        rho_values=[-0.05],
    )
    expected = walk_forward(PoissonModel(res.config), matches)
    assert res.rps == pytest.approx(expected.rps)
    best_manual = min(
        walk_forward(
            PoissonModel(PoissonConfig(lr=lr, baseline=0.26, home_adv=0.0, rho=-0.05)),
            matches,
        ).rps
        for lr in lr_grid
    )
    assert res.rps == pytest.approx(best_manual)


def test_empty_grid_raises():
    with pytest.raises(ValueError):
        calibrate_poisson(
            _matches(),
            lr_values=[],
            baseline_values=[0.26],
            home_adv_values=[0.0],
            rho_values=[-0.05],
        )
```

- [ ] **Step 2: Run it, confirm it FAILS** (`ModuleNotFoundError: No module named 'oraculo.calibrate.poisson'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calibrate_poisson.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `oraculo/calibrate/poisson.py`:**

```python
from __future__ import annotations

import datetime
import itertools
from dataclasses import dataclass
from typing import Optional, Sequence

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.walk_forward import walk_forward


@dataclass
class PoissonCalibrationResult:
    config: PoissonConfig
    rps: float


def calibrate_poisson(
    matches: Sequence[Match],
    *,
    lr_values: Sequence[float],
    baseline_values: Sequence[float],
    home_adv_values: Sequence[float],
    rho_values: Sequence[float],
    eval_from: datetime.date | None = None,
) -> PoissonCalibrationResult:
    """Grid search: devuelve la PoissonConfig que minimiza el RPS walk-forward."""
    match_list = list(matches)
    best: Optional[PoissonCalibrationResult] = None
    for lr, baseline, home_adv, rho in itertools.product(
        lr_values, baseline_values, home_adv_values, rho_values
    ):
        cfg = PoissonConfig(lr=lr, baseline=baseline, home_adv=home_adv, rho=rho)
        res = walk_forward(PoissonModel(cfg), match_list, eval_from=eval_from)
        if best is None or res.rps < best.rps:
            best = PoissonCalibrationResult(config=cfg, rps=res.rps)
    if best is None:
        raise ValueError("el grid de calibración está vacío")
    return best
```

- [ ] **Step 4: Run it, confirm tests pass:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calibrate_poisson.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/calibrate/poisson.py tests/test_calibrate_poisson.py
git commit -m "feat: add Poisson grid-search calibration" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Scripts — comparar Poisson contra Elo y la vara, y calibrar

**Files:**
- Create: `scripts/run_poisson.py`
- Create: `scripts/calibrate_poisson.py`

- [ ] **Step 1: Write `scripts/run_poisson.py`:**

```python
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
```

- [ ] **Step 2: Run it:**

Run: `.\.venv\Scripts\python.exe scripts\run_poisson.py`
Expected: imprime las tres métricas. El Poisson (default) debería tener RPS competitivo con el Elo (probablemente cerca; el default sin calibrar puede no ganarle todavía). Anotar los números. Puede tardar algunos segundos (arma una matriz por partido evaluado).

- [ ] **Step 3: Write `scripts/calibrate_poisson.py`:**

```python
"""Calibra el Poisson por grid search minimizando RPS walk-forward, e imprime la
mejor config y su comparación con la vara y el Elo."""
from __future__ import annotations

import datetime
import math
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest
from oraculo.calibrate.poisson import calibrate_poisson

DATA = Path(__file__).resolve().parent.parent / "data" / "results.csv"
EVAL_FROM = datetime.date(2010, 1, 1)

LR_VALUES = [0.03, 0.06, 0.1]
BASELINE_VALUES = [math.log(1.3)]
HOME_ADV_VALUES = [0.2, 0.3]
RHO_VALUES = [-0.1, -0.05, 0.0]


def main() -> None:
    matches = load_results(DATA)
    eval_set = [m for m in matches if m.date >= EVAL_FROM]
    uni = backtest(UniformPredictor(), eval_set)

    n_configs = len(LR_VALUES) * len(BASELINE_VALUES) * len(HOME_ADV_VALUES) * len(RHO_VALUES)
    print(f"Calibrando Poisson sobre {n_configs} configs (puede tardar varios minutos)...")
    best = calibrate_poisson(
        matches,
        lr_values=LR_VALUES,
        baseline_values=BASELINE_VALUES,
        home_adv_values=HOME_ADV_VALUES,
        rho_values=RHO_VALUES,
        eval_from=EVAL_FROM,
    )

    c = best.config
    print(f"Vara uniforme  RPS: {uni.rps:.4f}")
    print(f"Mejor Poisson  RPS: {best.rps:.4f}  "
          f"(lr={c.lr}, baseline={c.baseline:.4f}, home_adv={c.home_adv}, rho={c.rho})")
    print(f"Mejora sobre la vara: {uni.rps - best.rps:+.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it (BE PATIENT — 18 configs, cada una arma matrices sobre la ventana de evaluación; puede tardar varios minutos. No lo mates antes de tiempo):**

Run: `.\.venv\Scripts\python.exe scripts\calibrate_poisson.py`
Expected: imprime la mejor config y su RPS. Debería quedar claramente por debajo de la vara (0.2391) y competir con el Elo calibrado (0.1745). Anotar la config ganadora.

- [ ] **Step 5: Run the FULL suite and commit:**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests (Fases 1+2+3) en verde.

```powershell
git add scripts/run_poisson.py scripts/calibrate_poisson.py
git commit -m "feat: add Poisson-vs-Elo-vs-baseline comparison and calibration scripts" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite (Fases 1+2+3).
- `scripts\run_poisson.py` muestra las métricas de Poisson junto a Elo y la vara sobre la misma ventana.
- `scripts\calibrate_poisson.py` reporta la mejor config (lr, home_adv, rho) y su RPS, anotada.
- El `PoissonModel` puebla `xg_home`/`xg_away`/`score_matrix` — lo que necesita el Monte Carlo de la Fase 4.

Siguiente: **Plan 4 — simulador Monte Carlo del Mundial 2026 + config `wc2026.yaml`.**
