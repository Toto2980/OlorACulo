# Oráculo Mundial 2026 — Plan 4b: Eliminatorias + P(campeón)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar la simulación del Mundial: a partir de los 32 clasificados de la fase de grupos, simular el cuadro de eliminación directa (32avos → octavos → cuartos → semi → final) con semilla fija, y obtener por equipo P(llega a cada ronda) y **P(campeón)**.

**Architecture:** Plantilla de cuadro fija (`oraculo/tournament/bracket.py`) que mapea posiciones de grupo (ganador/segundo/mejor-tercero) a los 16 cruces de 32avos. Simulación de partido eliminatorio con penales ponderados (`oraculo/tournament/knockout.py`). Simulación de torneo completo + agregador Monte Carlo (`oraculo/tournament/tournament.py`). Reusa la fase de grupos (`simulate_group_stage`), el muestreo de marcadores (`sample_scoreline`) y el `PoissonModel`.

**Tech Stack:** Python 3.11+, numpy, pytest. Reusa todo lo de las Fases 1-4a.

**Decomposición:** Plan 4b, último de la Fase 4. Fases 1-4a completas. Esto cierra el predictor end-to-end.

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Paths relativos.

**Convenciones (Windows/PowerShell):** python/pytest con `.\.venv\Scripts\python.exe`; commits con doble `-m` para el trailer de coautoría.

**Decisiones de modelado (simplificaciones documentadas):**
- **Cuadro fijo** (plantilla en `bracket.py`) en vez de la tabla combinatoria oficial de terceros de FIFA. Respeta la estructura de single-elimination y no cruza dos equipos del mismo grupo en 32avos por construcción (salvo coincidencias raras vía terceros). Documentado como simplificación.
- Partidos de eliminación: **neutrales**; empate → **penales** decididos por moneda ponderada `p_local/(p_local+p_visit)` del modelo.
- Semilla fija (la del `wc2026.yaml`) para todo el torneo.

---

## Task 1: Exponer los mejores terceros rankeados en el resultado de grupos

**Files:**
- Modify: `oraculo/tournament/groupstage.py` (agregar campo `best_thirds` a `GroupStageResult` y poblarlo)
- Test: `tests/test_groupstage_thirds.py`

- [ ] **Step 1: Write the failing test** `tests/test_groupstage_thirds.py`:

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.group import TeamRecord
from oraculo.tournament.groupstage import simulate_group_stage


class _StrengthModel:
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
    names = [f"T{i}" for i in range(48)]
    groups = {chr(ord("A") + gi): names[gi * 4:(gi + 1) * 4] for gi in range(12)}
    return WorldCupConfig(seed=1, groups=groups)


def test_best_thirds_has_eight_ranked_records():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    res = simulate_group_stage(_StrengthModel(strength), _config(), np.random.default_rng(1))
    assert len(res.best_thirds) == 8
    assert all(isinstance(r, TeamRecord) for r in res.best_thirds)


def test_best_thirds_all_advance_and_are_subset_of_advancing():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    res = simulate_group_stage(_StrengthModel(strength), _config(), np.random.default_rng(1))
    assert {r.team for r in res.best_thirds} <= res.advancing
```

- [ ] **Step 2: Run, confirm FAIL** (`AttributeError: 'GroupStageResult' object has no attribute 'best_thirds'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_groupstage_thirds.py -v`

- [ ] **Step 3: Modify `oraculo/tournament/groupstage.py`** — agregar el campo y poblarlo. El archivo completo queda así:

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
    best_thirds: list[TeamRecord]


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

    return GroupStageResult(standings=standings, advancing=advancing, best_thirds=best_thirds)
```

- [ ] **Step 4: Run, confirm pass** (también la suite previa de groupstage sigue verde):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_groupstage_thirds.py tests/test_groupstage.py -v`
Expected: PASS (5 passed — 2 nuevos + 3 previos).

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/groupstage.py tests/test_groupstage_thirds.py
git commit -m "feat: expose ranked best_thirds in GroupStageResult" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Partido de eliminación directa (con penales)

**Files:**
- Create: `oraculo/tournament/knockout.py`
- Test: `tests/test_knockout_match.py`

- [ ] **Step 1: Write the failing test** `tests/test_knockout_match.py`:

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.tournament.knockout import knockout_winner


class _FixedScore:
    """Devuelve siempre un marcador concentrado (hg, ag) y probs coherentes."""

    def __init__(self, hg, ag):
        self.m = np.zeros((11, 11))
        self.m[hg, ag] = 1.0
        # probs coherentes con un único marcador
        from oraculo.ratings.poisson import outcome_probs
        self._p = outcome_probs(self.m)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def test_home_win_returns_home():
    assert knockout_winner(_FixedScore(2, 0), "A", "B", np.random.default_rng(0)) == "A"


def test_away_win_returns_away():
    assert knockout_winner(_FixedScore(0, 3), "A", "B", np.random.default_rng(0)) == "B"


class _DrawThenStrength:
    """Marcador siempre 1-1 (empate), pero con probs 1-X-2 asimétricas para penales."""

    def __init__(self, p_home, p_draw, p_away):
        self.m = np.zeros((11, 11))
        self.m[1, 1] = 1.0
        self._p = (p_home, p_draw, p_away)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def test_draw_resolves_by_weighted_penalties_favoring_stronger():
    # local mucho más fuerte (p_home alto) -> gana penales casi siempre
    model = _DrawThenStrength(0.8, 0.15, 0.05)
    wins_a = sum(
        knockout_winner(model, "A", "B", np.random.default_rng(s)) == "A"
        for s in range(200)
    )
    assert wins_a > 150  # la mayoría para el más fuerte
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.knockout'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knockout_match.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/knockout.py`** (incluye también `simulate_knockout`, que se testea en la Task 4):

```python
from __future__ import annotations

import numpy as np

from oraculo.tournament.group import sample_scoreline

_KNOCKOUT_ROUNDS = ("R16", "QF", "SF", "Final", "Champion")


def knockout_winner(model, home: str, away: str, rng: np.random.Generator) -> str:
    """Simula un partido de eliminación (neutral). Empate -> penales ponderados
    por la fuerza relativa del modelo (p_local / (p_local + p_visit))."""
    pred = model.predict(home, away, neutral=True)
    hg, ag = sample_scoreline(pred.score_matrix, rng)
    if hg > ag:
        return home
    if ag > hg:
        return away
    denom = pred.p_home + pred.p_away
    p_home_pens = 0.5 if denom == 0 else pred.p_home / denom
    return home if rng.random() < p_home_pens else away


def simulate_knockout(model, r32_pairs, rng: np.random.Generator) -> dict[str, list[str]]:
    """Simula el cuadro completo desde 32avos. Devuelve, por ronda, la lista de
    equipos que LLEGARON a esa instancia. Claves: R32, R16, QF, SF, Final, Champion."""
    rounds: dict[str, list[str]] = {"R32": [team for pair in r32_pairs for team in pair]}
    pairs = list(r32_pairs)
    for name in _KNOCKOUT_ROUNDS:
        winners = [knockout_winner(model, home, away, rng) for home, away in pairs]
        rounds[name] = winners
        if len(winners) == 1:
            break
        pairs = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
    return rounds
```

- [ ] **Step 4: Run, confirm 3 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knockout_match.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/knockout.py tests/test_knockout_match.py
git commit -m "feat: add knockout match simulation with weighted penalties" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Plantilla de cuadro y resolución de cruces

**Files:**
- Create: `oraculo/tournament/bracket.py`
- Test: `tests/test_bracket.py`

- [ ] **Step 1: Write the failing test** `tests/test_bracket.py`:

```python
from oraculo.tournament.bracket import R32_TEMPLATE, resolve_bracket
from oraculo.tournament.group import TeamRecord
from oraculo.tournament.groupstage import GroupStageResult


def _fake_gsr():
    standings = {
        g: [TeamRecord(f"{g}1"), TeamRecord(f"{g}2"), TeamRecord(f"{g}3"), TeamRecord(f"{g}4")]
        for g in "ABCDEFGHIJKL"
    }
    best_thirds = [TeamRecord(f"Third{i}") for i in range(1, 9)]
    return GroupStageResult(standings=standings, advancing=set(), best_thirds=best_thirds)


def test_template_has_16_matches_and_32_distinct_slots():
    assert len(R32_TEMPLATE) == 16
    slots = [s for pair in R32_TEMPLATE for s in pair]
    assert len(slots) == 32
    assert len(set(slots)) == 32  # sin slots repetidos


def test_resolve_maps_slots_to_team_names():
    pairs = resolve_bracket(_fake_gsr())
    assert len(pairs) == 16
    # primer cruce de la plantilla: W_A vs R_B -> ("A1", "B2")
    assert pairs[0] == ("A1", "B2")
    # todos los nombres resueltos son strings no vacíos
    for a, b in pairs:
        assert isinstance(a, str) and isinstance(b, str) and a and b


def test_resolve_uses_best_thirds():
    pairs = resolve_bracket(_fake_gsr())
    resolved = {t for pair in pairs for t in pair}
    # los 8 terceros aparecen en el cuadro
    for i in range(1, 9):
        assert f"Third{i}" in resolved
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.bracket'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_bracket.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/bracket.py`:**

```python
from __future__ import annotations

from oraculo.tournament.groupstage import GroupStageResult

# Plantilla fija de 32avos (SIMPLIFICACIÓN de la tabla oficial de FIFA).
# Tokens: "W_<grupo>" = ganador, "R_<grupo>" = segundo, "T<n>" = n-ésimo mejor tercero.
# Construida para no cruzar ganador y segundo del mismo grupo en 32avos.
R32_TEMPLATE: list[tuple[str, str]] = [
    ("W_A", "R_B"),
    ("W_C", "R_D"),
    ("W_E", "T1"),
    ("W_G", "R_H"),
    ("W_I", "R_J"),
    ("W_K", "T2"),
    ("W_B", "R_A"),
    ("W_D", "R_C"),
    ("W_F", "T3"),
    ("W_H", "R_G"),
    ("W_J", "R_I"),
    ("W_L", "T4"),
    ("R_E", "T5"),
    ("R_F", "T6"),
    ("R_K", "T7"),
    ("R_L", "T8"),
]


def _resolve_slot(slot: str, gsr: GroupStageResult) -> str:
    kind = slot[0]
    if kind == "W":
        return gsr.standings[slot[2:]][0].team
    if kind == "R":
        return gsr.standings[slot[2:]][1].team
    if kind == "T":
        return gsr.best_thirds[int(slot[1:]) - 1].team
    raise ValueError(f"slot desconocido: {slot}")


def resolve_bracket(gsr: GroupStageResult) -> list[tuple[str, str]]:
    """Convierte la plantilla de slots en cruces concretos (nombres de equipos)."""
    return [(_resolve_slot(a, gsr), _resolve_slot(b, gsr)) for a, b in R32_TEMPLATE]
```

- [ ] **Step 4: Run, confirm 3 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_bracket.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/bracket.py tests/test_bracket.py
git commit -m "feat: add fixed R32 bracket template and slot resolution" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Tests del cuadro completo de eliminatorias

**Files:**
- Modify: `oraculo/tournament/knockout.py` (`simulate_knockout` YA creada en la Task 2; acá solo tests)
- Test: `tests/test_knockout_bracket.py`

- [ ] **Step 1: Write the failing test** `tests/test_knockout_bracket.py`:

```python
import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.knockout import simulate_knockout


class _StrengthModel:
    """El equipo con índice más bajo (T0 < T1 < ...) es más fuerte y siempre gana."""

    def _strength(self, team):
        return 100 - int(team[1:])  # T0 fuerte, T31 débil

    def predict(self, home, away, *, neutral=False, on_date=None):
        sh, sa = self._strength(home), self._strength(away)
        m = np.zeros((11, 11))
        if sh >= sa:
            m[3, 0] = 1.0
        else:
            m[0, 3] = 1.0
        ph, pd, pa = outcome_probs(m)
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=m)


def _bracket_32():
    teams = [f"T{i}" for i in range(32)]
    return [(teams[i], teams[i + 1]) for i in range(0, 32, 2)]


def test_round_sizes():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    assert len(rounds["R32"]) == 32
    assert len(rounds["R16"]) == 16
    assert len(rounds["QF"]) == 8
    assert len(rounds["SF"]) == 4
    assert len(rounds["Final"]) == 2
    assert len(rounds["Champion"]) == 1


def test_strongest_team_wins():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    # T0 es el más fuerte de todos -> campeón
    assert rounds["Champion"] == ["T0"]


def test_champion_reached_every_round():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    champ = rounds["Champion"][0]
    for r in ("R32", "R16", "QF", "SF", "Final"):
        assert champ in rounds[r]
```

- [ ] **Step 2: Run, confirm it PASSES** (`simulate_knockout` ya existe de la Task 2):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knockout_bracket.py -v`
Expected: PASS (3 passed). Si algo falla, revisar `simulate_knockout` contra el header de la Task 2.

- [ ] **Step 3: (No hay implementación nueva — se hizo en la Task 2.)**

- [ ] **Step 4: Commit:**

```powershell
git add tests/test_knockout_bracket.py
git commit -m "test: cover full knockout bracket simulation" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Torneo completo + agregador Monte Carlo

**Files:**
- Create: `oraculo/tournament/tournament.py`
- Test: `tests/test_tournament_mc.py`

- [ ] **Step 1: Write the failing test** `tests/test_tournament_mc.py`:

```python
import numpy as np
import pytest

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.tournament import simulate_tournament, run_tournament_mc


class _FakeModel:
    """Marcador 1-1 siempre -> todo se define por azar sembrado (grupos y penales)."""

    def __init__(self):
        self.m = np.zeros((11, 11))
        self.m[1, 1] = 1.0
        self._p = outcome_probs(self.m)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def _config():
    names = [f"T{i}" for i in range(48)]
    groups = {chr(ord("A") + gi): names[gi * 4:(gi + 1) * 4] for gi in range(12)}
    return WorldCupConfig(seed=2026, groups=groups)


def test_simulate_tournament_has_one_champion():
    rounds = simulate_tournament(_FakeModel(), _config(), np.random.default_rng(3))
    assert len(rounds["Champion"]) == 1
    assert len(rounds["R32"]) == 32


def test_mc_champion_probs_sum_to_one():
    probs = run_tournament_mc(_FakeModel(), _config(), n_iter=300)
    total = sum(p["Champion"] for p in probs.values())
    assert total == pytest.approx(1.0)


def test_mc_round_probabilities_monotonic():
    probs = run_tournament_mc(_FakeModel(), _config(), n_iter=300)
    # para cada equipo: P(R32) >= P(R16) >= P(QF) >= P(SF) >= P(Final) >= P(Champion)
    for p in probs.values():
        assert p["R32"] >= p["R16"] >= p["QF"] >= p["SF"] >= p["Final"] >= p["Champion"]


def test_mc_deterministic_with_seed():
    a = run_tournament_mc(_FakeModel(), _config(), n_iter=100)
    b = run_tournament_mc(_FakeModel(), _config(), n_iter=100)
    assert a == b
```

- [ ] **Step 2: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'oraculo.tournament.tournament'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tournament_mc.py -v`

- [ ] **Step 3: Implement `oraculo/tournament/tournament.py`:**

```python
from __future__ import annotations

import numpy as np

from oraculo.tournament.bracket import resolve_bracket
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage
from oraculo.tournament.knockout import simulate_knockout

ROUNDS = ("R32", "R16", "QF", "SF", "Final", "Champion")


def simulate_tournament(
    model, config: WorldCupConfig, rng: np.random.Generator
) -> dict[str, list[str]]:
    """Un torneo completo: fase de grupos -> cuadro -> eliminatorias.
    Devuelve, por ronda, la lista de equipos que llegaron."""
    gsr = simulate_group_stage(model, config, rng)
    r32_pairs = resolve_bracket(gsr)
    return simulate_knockout(model, r32_pairs, rng)


def run_tournament_mc(
    model, config: WorldCupConfig, *, n_iter: int
) -> dict[str, dict[str, float]]:
    """Corre n_iter torneos completos (semilla fija desde config.seed) y devuelve,
    por equipo, P(llega a cada ronda) y P(campeón)."""
    rng = np.random.default_rng(config.seed)
    counts = {team: {r: 0 for r in ROUNDS} for team in config.teams}
    for _ in range(n_iter):
        rounds = simulate_tournament(model, config, rng)
        for r in ROUNDS:
            for team in rounds[r]:
                counts[team][r] += 1
    return {
        team: {r: c / n_iter for r, c in tallies.items()}
        for team, tallies in counts.items()
    }
```

- [ ] **Step 4: Run, confirm 4 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tournament_mc.py -v`

- [ ] **Step 5: Commit:**

```powershell
git add oraculo/tournament/tournament.py tests/test_tournament_mc.py
git commit -m "feat: add full-tournament simulation and Monte Carlo aggregator" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Script — predecir el campeón del Mundial 2026

**Files:**
- Create: `scripts/run_world_cup.py`

- [ ] **Step 1: Write `scripts/run_world_cup.py`:**

```python
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
```

- [ ] **Step 2: Run it (entrena el Poisson y corre 10k torneos completos; puede tardar varios minutos — BE PATIENT, no lo mates antes de tiempo):**

Run: `.\.venv\Scripts\python.exe scripts\run_world_cup.py`
Expected: imprime el ranking de P(campeón). Sanity check: arriba deberían estar selecciones top (Argentina, Francia, España, Brasil, Inglaterra, Alemania, Portugal...) con P(campeón) de un dígito alto / dos dígitos bajos cada una (en un campo de 48, nadie debería superar ~20%). Anotar el TOP 10 completo y verbatim.

- [ ] **Step 3: Run the FULL suite and commit:**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests (Fases 1-4b) en verde.

```powershell
git add scripts/run_world_cup.py
git commit -m "feat: add full World Cup champion-prediction run script" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite (Fases 1-4b).
- `scripts\run_world_cup.py` imprime el ranking de P(campeón) del Mundial 2026, con selecciones top arriba (sanity check) y nadie con probabilidad absurda.
- El Oráculo responde por fin la pregunta original: **¿quién gana el Mundial?**

Siguiente (opcional, post-Fase 4): persistencia en SQLite (snapshots/evals), ingesta de resultados en vivo para fijar partidos ya jugados, capa Streamlit, extensión de lesiones, refinamientos de calibración/cuadro.
