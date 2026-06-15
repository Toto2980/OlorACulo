# Oráculo Mundial 2026 — Plan 4a: Simulación de la fase de grupos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simular la fase de grupos del Mundial 2026 (12 grupos de 4, formato real) miles de veces con semilla fija, muestreando marcadores del modelo Poisson, para estimar por equipo P(sale 1º/2º/3º) y P(avanza a la siguiente ronda) — incluyendo los 8 mejores terceros.

**Architecture:** Config del torneo (grupos + semilla) en `data/wc2026.yaml`, cargada por `oraculo/tournament/config.py`. Simulación de un partido muestreando del `score_matrix` (`oraculo/tournament/group.py`), cómputo de tabla y orden con desempates (puntos → DG → GF → azar sembrado). Simulación de toda la fase de grupos con selección de mejores terceros (`oraculo/tournament/groupstage.py`). Agregador Monte Carlo con semilla fija (`oraculo/tournament/montecarlo.py`). Todo consume un modelo ya entrenado que devuelve `score_matrix` (el `PoissonModel`).

**Tech Stack:** Python 3.11+, numpy, **pyyaml** (nueva dependencia), pytest. Reusa `PoissonModel`, `MatchPrediction`, `load_results`.

**Decomposición:** Plan 4a de la serie. Fases 1-3 completas. El Plan 4b (llaves eliminatorias + P(campeón)) viene después. Esta fase entrega P(avanza de grupo) por equipo, ya útil.

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Paths relativos.

**Convenciones (Windows/PowerShell):** python/pytest con `.\.venv\Scripts\python.exe`; commits con doble `-m` para el trailer de coautoría.

**Decisiones de modelado (simplificaciones documentadas):**
- Partidos de grupo simulados como **neutrales** (el modelo no aplica ventaja de localía). La localía de anfitriones (México/EE.UU./Canadá) queda como refinamiento futuro.
- Desempates dentro del grupo: **puntos → diferencia de gol → goles a favor → azar sembrado**. Se omiten head-to-head y fair-play (igual que el video).
- Avanzan: **1º y 2º de cada grupo (24) + los 8 mejores terceros** (ranking de los 12 terceros por puntos → DG → GF → azar).
- **Semilla fija** desde `wc2026.yaml` (filosofía del video: las predicciones solo cambian si cambian los datos).
- El Mundial ya arrancó (11/06/2026): este simulador corre el torneo **desde cero**; fijar partidos ya jugados es un refinamiento posterior.

**Nombres de equipos:** deben coincidir con el dataset histórico (martj42). Ya verificado: 46/48 coinciden tal cual; los dos ajustes son **"Czech Republic"** (no "Czechia") y **"Curaçao"** (con cedilla).

---

## Task 1: Config del torneo + `wc2026.yaml` + validación de nombres

**Files:**
- Modify: `pyproject.toml` (agregar `pyyaml` a dependencies)
- Create: `oraculo/tournament/__init__.py` (EMPTY)
- Create: `oraculo/tournament/config.py`
- Create: `data/wc2026.yaml`
- Test: `tests/test_wc_config.py`
- Test: `tests/test_wc2026_teams.py` (integración: valida contra el dataset real)

- [ ] **Step 1: Agregar pyyaml a `pyproject.toml`** — cambiar la línea de dependencies:

```toml
dependencies = ["pandas", "numpy", "pyyaml"]
```

Luego reinstalar: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`
Expected: instala PyYAML sin errores.

- [ ] **Step 2: Crear `data/wc2026.yaml`** (nombres ya alineados al dataset histórico):

```yaml
seed: 2026
groups:
  A: [Mexico, South Africa, South Korea, Czech Republic]
  B: [Canada, Bosnia and Herzegovina, Qatar, Switzerland]
  C: [Brazil, Morocco, Haiti, Scotland]
  D: [United States, Paraguay, Australia, Turkey]
  E: [Germany, Curaçao, Ivory Coast, Ecuador]
  F: [Netherlands, Japan, Sweden, Tunisia]
  G: [Belgium, Egypt, Iran, New Zealand]
  H: [Spain, Cape Verde, Saudi Arabia, Uruguay]
  I: [France, Senegal, Iraq, Norway]
  J: [Argentina, Algeria, Austria, Jordan]
  K: [Portugal, DR Congo, Uzbekistan, Colombia]
  L: [England, Croatia, Ghana, Panama]
```

- [ ] **Step 3: Write failing test `tests/test_wc_config.py`** (usa un fixture chico, no el real):

```python
from pathlib import Path

from oraculo.tournament.config import load_config, WorldCupConfig

FIXTURE = Path(__file__).parent / "fixtures" / "wc_test.yaml"


def _write_fixture():
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        "seed: 7\n"
        "groups:\n"
        "  A: [Argentina, Brazil, Chile, Peru]\n"
        "  B: [France, Spain, Italy, Germany]\n",
        encoding="utf-8",
    )


def test_loads_seed_and_groups():
    _write_fixture()
    cfg = load_config(FIXTURE)
    assert isinstance(cfg, WorldCupConfig)
    assert cfg.seed == 7
    assert cfg.groups["A"] == ["Argentina", "Brazil", "Chile", "Peru"]
    assert len(cfg.groups) == 2


def test_teams_flattens_all_groups():
    _write_fixture()
    cfg = load_config(FIXTURE)
    assert len(cfg.teams) == 8
    assert "Italy" in cfg.teams
```

- [ ] **Step 4: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.config'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_wc_config.py -v`

- [ ] **Step 5: Create `oraculo/tournament/__init__.py` EMPTY, then implement `oraculo/tournament/config.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class WorldCupConfig:
    seed: int
    groups: dict[str, list[str]]

    @property
    def teams(self) -> list[str]:
        return [team for teams in self.groups.values() for team in teams]


def load_config(path: str | Path) -> WorldCupConfig:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    groups = {name: list(teams) for name, teams in data["groups"].items()}
    return WorldCupConfig(seed=int(data["seed"]), groups=groups)
```

- [ ] **Step 6: Run, confirm 2 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_wc_config.py -v`

- [ ] **Step 7: Write integration test `tests/test_wc2026_teams.py`** (valida que los 48 equipos existen en el dataset histórico):

```python
from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.tournament.config import load_config

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"


def test_all_wc2026_teams_exist_in_history():
    matches = load_results(DATA)
    known = {m.home for m in matches} | {m.away for m in matches}
    cfg = load_config(WC)
    missing = [t for t in cfg.teams if t not in known]
    assert missing == [], f"equipos sin datos históricos: {missing}"


def test_twelve_groups_of_four():
    cfg = load_config(WC)
    assert len(cfg.groups) == 12
    assert all(len(teams) == 4 for teams in cfg.groups.values())
    assert len(cfg.teams) == 48
```

- [ ] **Step 8: Run, confirm 2 passed** (requiere `data/results.csv`, ya descargado):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_wc2026_teams.py -v`
Expected: PASS. Si `test_all_wc2026_teams_exist_in_history` falla, imprime los equipos faltantes — corregir su grafía en `wc2026.yaml` para que matchee el dataset.

- [ ] **Step 9: Commit:**

```powershell
git add pyproject.toml oraculo/tournament/__init__.py oraculo/tournament/config.py data/wc2026.yaml tests/test_wc_config.py tests/test_wc2026_teams.py tests/fixtures/wc_test.yaml
git commit -m "feat: add WC2026 tournament config (groups + seed) with team-name validation" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Muestreo de marcadores y simulación de un partido

**Files:**
- Create: `oraculo/tournament/group.py`
- Test: `tests/test_match_sim.py`

- [ ] **Step 1: Write failing test `tests/test_match_sim.py`:**

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.group import sample_scoreline, simulate_match


def _matrix_concentrated(i, j, n=11):
    m = np.zeros((n, n))
    m[i, j] = 1.0
    return m


def test_sample_scoreline_picks_only_nonzero_cell():
    rng = np.random.default_rng(0)
    m = _matrix_concentrated(2, 3)
    for _ in range(5):
        assert sample_scoreline(m, rng) == (2, 3)


class _FakeModel:
    def __init__(self, matrix):
        self.matrix = matrix
        ph, pd, pa = outcome_probs(matrix)
        self._probs = (ph, pd, pa)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def test_simulate_match_uses_model_matrix():
    rng = np.random.default_rng(0)
    model = _FakeModel(_matrix_concentrated(1, 0))
    assert simulate_match(model, "A", "B", rng, neutral=True) == (1, 0)
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.group'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_sim.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/group.py`** (incluye también `compute_standings`/`rank_group`/`simulate_group`, que se testean en la Task 3):

```python
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from oraculo.models.base import MatchPrediction


def sample_scoreline(matrix: np.ndarray, rng: np.random.Generator) -> tuple[int, int]:
    """Muestrea (goles_local, goles_visit) de una matriz de resultados normalizada."""
    flat = matrix.ravel()
    idx = int(rng.choice(flat.size, p=flat))
    cols = matrix.shape[1]
    return idx // cols, idx % cols


def simulate_match(model, home: str, away: str, rng: np.random.Generator, *, neutral: bool = True) -> tuple[int, int]:
    """Predice con el modelo y muestrea un marcador concreto."""
    pred: MatchPrediction = model.predict(home, away, neutral=neutral)
    return sample_scoreline(pred.score_matrix, rng)


@dataclass
class TeamRecord:
    team: str
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def compute_standings(teams, results) -> dict[str, TeamRecord]:
    """results: iterable de (home, away, home_goals, away_goals). Devuelve tabla por equipo."""
    table = {t: TeamRecord(t) for t in teams}
    for home, away, hg, ag in results:
        table[home].goals_for += hg
        table[home].goals_against += ag
        table[away].goals_for += ag
        table[away].goals_against += hg
        if hg > ag:
            table[home].points += 3
        elif hg < ag:
            table[away].points += 3
        else:
            table[home].points += 1
            table[away].points += 1
    return table


def rank_group(table: dict[str, TeamRecord], rng: np.random.Generator) -> list[TeamRecord]:
    """Ordena por puntos -> DG -> GF -> azar sembrado (rompe empates irresolubles)."""
    return sorted(
        table.values(),
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, rng.random()),
    )


def simulate_group(model, teams, rng: np.random.Generator) -> list[TeamRecord]:
    """Juega todos contra todos (cancha neutral) y devuelve los 4 equipos rankeados."""
    results = []
    for home, away in itertools.combinations(teams, 2):
        hg, ag = simulate_match(model, home, away, rng, neutral=True)
        results.append((home, away, hg, ag))
    return rank_group(compute_standings(teams, results), rng)
```

- [ ] **Step 4: Run, confirm 2 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_sim.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/group.py tests/test_match_sim.py
git commit -m "feat: add scoreline sampling and match simulation" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Tabla del grupo y orden con desempates

**Files:**
- Modify: `oraculo/tournament/group.py` (`compute_standings`/`rank_group`/`simulate_group` YA creadas en la Task 2; acá solo tests)
- Test: `tests/test_group_standings.py`

- [ ] **Step 1: Write failing test `tests/test_group_standings.py`:**

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.group import compute_standings, rank_group, simulate_group


def test_standings_points_and_goals():
    teams = ["A", "B", "C", "D"]
    results = [
        ("A", "B", 2, 0),  # A gana
        ("A", "C", 1, 1),  # empate
        ("A", "D", 3, 0),  # A gana
        ("B", "C", 0, 0),
        ("B", "D", 1, 0),
        ("C", "D", 2, 2),
    ]
    table = compute_standings(teams, results)
    assert table["A"].points == 7      # 2 victorias + 1 empate
    assert table["A"].goals_for == 6
    assert table["A"].goals_against == 1
    assert table["A"].goal_diff == 5


def test_rank_orders_by_points_then_gd():
    teams = ["A", "B", "C", "D"]
    results = [
        ("A", "B", 1, 0),
        ("A", "C", 1, 0),
        ("A", "D", 1, 0),
        ("B", "C", 5, 0),  # B con mejor DG que C/D
        ("B", "D", 0, 0),
        ("C", "D", 0, 0),
    ]
    table = compute_standings(teams, results)
    ranked = rank_group(table, np.random.default_rng(0))
    assert ranked[0].team == "A"   # 9 pts
    assert ranked[1].team == "B"   # 4 pts, +5 DG


class _FakeModel:
    def __init__(self, matrix):
        self.matrix = matrix
        self._probs = outcome_probs(matrix)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def test_simulate_group_returns_four_ranked_teams():
    m = np.zeros((11, 11))
    m[1, 1] = 1.0  # todos empatan 1-1 -> desempate por azar
    model = _FakeModel(m)
    ranked = simulate_group(model, ["A", "B", "C", "D"], np.random.default_rng(1))
    assert len(ranked) == 4
    assert {r.team for r in ranked} == {"A", "B", "C", "D"}
```

- [ ] **Step 2: Run, confirm it PASSES** (las funciones ya existen de la Task 2):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_group_standings.py -v`
Expected: PASS (3 passed). Si algo falla, revisar `compute_standings`/`rank_group` contra el header.

- [ ] **Step 3: (No hay implementación nueva — se hizo en la Task 2.)**

- [ ] **Step 4: Commit:**

```powershell
git add tests/test_group_standings.py
git commit -m "test: cover group standings and tiebreak ranking" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Simulación de toda la fase de grupos (con mejores terceros)

**Files:**
- Create: `oraculo/tournament/groupstage.py`
- Test: `tests/test_groupstage.py`

- [ ] **Step 1: Write failing test `tests/test_groupstage.py`:**

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage, GroupStageResult


class _StrengthModel:
    """Modelo falso: cada equipo tiene una 'fuerza' (goles esperados). Marcador =
    redondeo determinista via matriz concentrada en (round(lh), round(la))."""

    def __init__(self, strength):
        self.strength = strength

    def predict(self, home, away, *, neutral=False, on_date=None):
        lh = self.strength.get(home, 1.0)
        la = self.strength.get(away, 1.0)
        m = np.zeros((11, 11))
        m[int(round(lh)), int(round(la))] = 1.0
        ph, pd, pa = outcome_probs(m)
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=m)


def _config():
    # 12 grupos de 4 con equipos T0..T47; fuerzas decrecientes para que el orden sea claro
    groups = {}
    names = [f"T{i}" for i in range(48)]
    for gi in range(12):
        letter = chr(ord("A") + gi)
        groups[letter] = names[gi * 4:(gi + 1) * 4]
    return WorldCupConfig(seed=1, groups=groups)


def test_returns_result_with_standings_and_advancing():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}  # el primero de cada grupo es el más fuerte
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    assert isinstance(res, GroupStageResult)
    assert len(res.standings) == 12
    assert all(len(v) == 4 for v in res.standings.values())


def test_advancing_count_is_24_plus_8():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    # 2 por grupo (24) + 8 mejores terceros = 32
    assert len(res.advancing) == 32


def test_top_two_always_advance():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    for ranked in res.standings.values():
        assert ranked[0].team in res.advancing
        assert ranked[1].team in res.advancing
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.groupstage'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_groupstage.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/groupstage.py`:**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.group import TeamRecord, simulate_group


@dataclass
class GroupStageResult:
    standings: dict[str, list[TeamRecord]]
    advancing: set[str]


def simulate_group_stage(
    model, config: WorldCupConfig, rng: np.random.Generator
) -> GroupStageResult:
    """Simula los 12 grupos; avanzan 1º y 2º de cada uno + los 8 mejores terceros."""
    standings: dict[str, list[TeamRecord]] = {}
    advancing: set[str] = set()
    thirds: list[TeamRecord] = []

    for group, teams in config.groups.items():
        ranked = simulate_group(model, teams, rng)
        standings[group] = ranked
        advancing.add(ranked[0].team)
        advancing.add(ranked[1].team)
        thirds.append(ranked[2])

    best_thirds = sorted(
        thirds,
        key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, rng.random()),
    )[:8]
    for record in best_thirds:
        advancing.add(record.team)

    return GroupStageResult(standings=standings, advancing=advancing)
```

- [ ] **Step 4: Run, confirm 3 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_groupstage.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/groupstage.py tests/test_groupstage.py
git commit -m "feat: simulate full group stage with best-thirds qualification" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Agregador Monte Carlo de la fase de grupos

**Files:**
- Create: `oraculo/tournament/montecarlo.py`
- Test: `tests/test_montecarlo_groups.py`

- [ ] **Step 1: Write failing test `tests/test_montecarlo_groups.py`:**

```python
import numpy as np
import pytest

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.montecarlo import run_group_stage_mc


class _FakeModel:
    """Marcador siempre 1-1 -> todo se define por azar sembrado."""

    def __init__(self):
        self.matrix = np.zeros((11, 11))
        self.matrix[1, 1] = 1.0
        self._probs = outcome_probs(self.matrix)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def _config():
    groups = {chr(ord("A") + gi): [f"T{gi}_{k}" for k in range(4)] for gi in range(12)}
    return WorldCupConfig(seed=2026, groups=groups)


def test_position_probabilities_sum_to_one_per_team():
    res = run_group_stage_mc(_FakeModel(), _config(), n_iter=200)
    for team, probs in res.items():
        total = probs["1st"] + probs["2nd"] + probs["3rd"] + probs["4th"]
        assert total == pytest.approx(1.0)  # cada equipo termina en exactamente una posición por iteración


def test_advance_probability_in_range():
    res = run_group_stage_mc(_FakeModel(), _config(), n_iter=200)
    for probs in res.values():
        assert 0.0 <= probs["advance"] <= 1.0


def test_deterministic_with_seed():
    a = run_group_stage_mc(_FakeModel(), _config(), n_iter=100)
    b = run_group_stage_mc(_FakeModel(), _config(), n_iter=100)
    assert a == b  # misma semilla (config.seed) -> mismo resultado
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.montecarlo'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_montecarlo_groups.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/montecarlo.py`:**

```python
from __future__ import annotations

import numpy as np

from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage

_POSITIONS = ("1st", "2nd", "3rd", "4th")


def run_group_stage_mc(
    model, config: WorldCupConfig, *, n_iter: int
) -> dict[str, dict[str, float]]:
    """Corre n_iter simulaciones de la fase de grupos (semilla fija desde config.seed)
    y devuelve, por equipo, las probabilidades de cada posición y de avanzar."""
    rng = np.random.default_rng(config.seed)
    counts = {
        team: {"1st": 0, "2nd": 0, "3rd": 0, "4th": 0, "advance": 0}
        for team in config.teams
    }

    for _ in range(n_iter):
        result = simulate_group_stage(model, config, rng)
        for ranked in result.standings.values():
            for position, record in enumerate(ranked):
                counts[record.team][_POSITIONS[position]] += 1
        for team in result.advancing:
            counts[team]["advance"] += 1

    return {
        team: {key: value / n_iter for key, value in tallies.items()}
        for team, tallies in counts.items()
    }
```

- [ ] **Step 4: Run, confirm 3 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_montecarlo_groups.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/montecarlo.py tests/test_montecarlo_groups.py
git commit -m "feat: add seeded Monte Carlo aggregator for the group stage" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Script — correr la simulación de grupos con el Poisson

**Files:**
- Create: `scripts/run_group_stage.py`

- [ ] **Step 1: Write `scripts/run_group_stage.py`:**

```python
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
```

- [ ] **Step 2: Run it (entrena el Poisson sobre ~49k partidos y corre 10k simulaciones; puede tardar unos minutos):**

Run: `.\.venv\Scripts\python.exe scripts\run_group_stage.py`
Expected: imprime los 12 grupos con P(avanza) por equipo. Sanity check: los favoritos (Argentina, Francia, España, Brasil, Inglaterra...) deberían tener P(avanza) alta (>70%). Anotar resultados llamativos.

- [ ] **Step 3: Run the FULL suite and commit:**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests (Fases 1+2+3+4a) en verde.

```powershell
git add scripts/run_group_stage.py
git commit -m "feat: add group-stage Monte Carlo run script" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite (Fases 1-4a).
- `test_wc2026_teams.py` confirma que los 48 equipos matchean el dataset histórico.
- `scripts\run_group_stage.py` imprime P(avanza de grupo) por equipo, con los favoritos arriba (sanity check).

Siguiente: **Plan 4b — llaves eliminatorias (R32→final) + P(campeón)**, que consume el conjunto de 32 clasificados.
