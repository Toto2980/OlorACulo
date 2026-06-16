# OlorACulo — Seguimiento en vivo + verificación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir OlorACulo en un dashboard del Mundial 2026 en curso con resultados reales, cuadro por fase, predicción detallada por partido, readiness pre-partido (T-60/30/15) y verificación predicho-vs-real con métricas en vivo.

**Architecture:** Capa `live/` (cliente API con cache + parser de fixtures + readiness puro), `report/` (match report riguroso + extras), `verify/` (predictor congelado anti-leakage + scoring + log), y UI Streamlit reestructurada en 5 pestañas con charts Altair reutilizables. Dos fuentes: API real (cuadro/verificación) + Monte Carlo existente (probabilidades a futuro).

**Tech Stack:** Python 3.11, `urllib.request` (stdlib, sin nuevas deps), Streamlit, Altair, NumPy, pandas, pytest. API: football-data.org (free tier, competición `WC`).

**Spec:** `docs/superpowers/specs/2026-06-16-oloraculo-live-verificacion-design.md`

**Convención del repo:** correr tests con `.\.venv\Scripts\python.exe -m pytest`. Todos los commits en la rama `feat/live-tracking-verificacion`.

---

## FASE L0 — Preparación

> **✅ RESULTADO Task 1 (confirmado 2026-06-16):** football-data.org free tier **SÍ cubre** el Mundial 2026 (`/competitions/WC`): 48 equipos, 104 partidos, temporada 2026, fases `GROUP_STAGE, LAST_32, LAST_16, QUARTER_FINALS, SEMI_FINALS, THIRD_PLACE, FINAL`. Status reales: `TIMED/IN_PLAY/PAUSED/FINISHED/POSTPONED` (→ normalizados en `fixtures.normalize_status`). Solo 4 nombres difieren del dataset (ver `_OVERRIDES` en Task 4). Cruces de eliminatorias vienen con `homeTeam.name=null` hasta definirse. **No hace falta fallback a API-Football.** Task 1 ya ejecutada.

### Task 1: Confirmar cobertura de la API (exploratorio, sin código de producción) — ✅ HECHA

**Objetivo:** Verificar que el free tier de football-data.org cubra el Mundial 2026 antes de escribir el cliente.

- [ ] **Step 1: Obtener una API key gratis**

Registrarse en https://www.football-data.org/client/register (gratis). Copiar el token.

- [ ] **Step 2: Probar el endpoint de partidos del Mundial**

Run (reemplazar `TOKEN`):
```bash
curl -s -H "X-Auth-Token: TOKEN" "https://api.football-data.org/v4/competitions/WC/matches" | python -m json.tool | head -60
```
Expected: JSON con clave `matches`, cada uno con `id`, `utcDate`, `status`, `stage`, `group`, `homeTeam.name`, `awayTeam.name`, `score.fullTime.home/away`.

- [ ] **Step 3: Anotar los nombres reales de equipos que devuelve la API**

Run:
```bash
curl -s -H "X-Auth-Token: TOKEN" "https://api.football-data.org/v4/competitions/WC/teams" | python -c "import sys,json; print('\n'.join(sorted(t['name'] for t in json.load(sys.stdin)['teams'])))"
```
Guardar la lista: se usa en Task 4 para el alias map.

- [ ] **Step 4: Decisión**

Si `WC` cubre el Mundial 2026 → seguir con football-data.org.
Si NO (free tier desactualizado / sin 2026) → fallback API-Football (api-sports.io, free tier vía RapidAPI): cambia solo `client.py` (URL + headers) y los nombres del alias map; el resto del plan no cambia.

**No hay commit en esta task** (es exploratoria).

---

### Task 2: Esqueleto de paquetes + gitignore + secrets

**Files:**
- Create: `oraculo/live/__init__.py` (vacío)
- Create: `oraculo/report/__init__.py` (vacío)
- Create: `oraculo/verify/__init__.py` (vacío)
- Create: `.streamlit/secrets.toml.example`
- Modify: `.gitignore`

- [ ] **Step 1: Crear los `__init__.py` vacíos**

Crear los tres archivos vacíos listados arriba.

- [ ] **Step 2: Crear `.streamlit/secrets.toml.example`**

```toml
# Copiá este archivo a .streamlit/secrets.toml y poné tu token de football-data.org.
# secrets.toml está gitignored: NUNCA se commitea la key real.
FOOTBALL_DATA_TOKEN = "pegá-tu-token-acá"
```

- [ ] **Step 3: Ampliar `.gitignore`**

Agregar al final de `.gitignore`:
```
.streamlit/secrets.toml
data/cache/
data/predictions_log.json
```

- [ ] **Step 4: Commit**

```bash
git add oraculo/live/__init__.py oraculo/report/__init__.py oraculo/verify/__init__.py .streamlit/secrets.toml.example .gitignore
git commit -m "chore: esqueleto de paquetes live/report/verify + secrets example"
```

---

## FASE L1 — Capa live

### Task 3: Modelo de dominio `Fixture` + etiquetas de fase

**Files:**
- Create: `oraculo/live/fixtures.py`
- Test: `tests/test_live_fixtures.py`
- Create: `tests/fixtures/wc_matches_sample.json`

- [ ] **Step 1: Crear el JSON de ejemplo (forma football-data.org)**

Crear `tests/fixtures/wc_matches_sample.json` (forma e ids reales confirmados en Task 1; nombres y status tal cual los devuelve football-data.org):
```json
{
  "matches": [
    {
      "id": 537327,
      "utcDate": "2026-06-11T19:00:00Z",
      "status": "FINISHED",
      "stage": "GROUP_STAGE",
      "group": "GROUP_A",
      "homeTeam": {"name": "Mexico"},
      "awayTeam": {"name": "South Africa"},
      "score": {"fullTime": {"home": 2, "away": 0}}
    },
    {
      "id": 537328,
      "utcDate": "2026-06-12T02:00:00Z",
      "status": "TIMED",
      "stage": "GROUP_STAGE",
      "group": "GROUP_A",
      "homeTeam": {"name": "South Korea"},
      "awayTeam": {"name": "Czechia"},
      "score": {"fullTime": {"home": null, "away": null}}
    },
    {
      "id": 537417,
      "utcDate": "2026-06-28T19:00:00Z",
      "status": "TIMED",
      "stage": "LAST_32",
      "group": null,
      "homeTeam": {"name": null},
      "awayTeam": {"name": null},
      "score": {"fullTime": {"home": null, "away": null}}
    }
  ]
}
```

- [ ] **Step 2: Escribir el test que falla**

Crear `tests/test_live_fixtures.py`:
```python
import datetime
import json
from pathlib import Path

from oraculo.live.fixtures import Fixture, parse_fixtures, phase_label, normalize_status

SAMPLE = Path(__file__).parent / "fixtures" / "wc_matches_sample.json"


def _raw():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_parse_returns_fixture_per_match():
    fixtures = parse_fixtures(_raw())
    assert len(fixtures) == 3
    assert all(isinstance(f, Fixture) for f in fixtures)


def test_parse_finished_match_has_score_and_outcome():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 537327)
    assert f.home == "Mexico"
    assert f.away == "South Africa"
    assert f.status == "FINISHED"
    assert f.is_finished
    assert (f.home_goals, f.away_goals) == (2, 0)
    assert f.kickoff_utc == datetime.datetime(2026, 6, 11, 19, 0, tzinfo=datetime.timezone.utc)


def test_parse_canonicalizes_names_and_normalizes_status():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 537328)
    # "Czechia" (API) -> "Czech Republic" (canónico del dataset)
    assert f.away == "Czech Republic"
    assert f.home == "South Korea"   # la API ya usa este nombre
    assert f.group == "A"
    assert f.status == "SCHEDULED"   # normalizado desde "TIMED"
    assert f.home_goals is None


def test_parse_unresolved_teams_become_none():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 537417)
    assert f.home is None and f.away is None
    assert f.stage == "LAST_32"
    assert not f.resolved


def test_normalize_status_maps_api_vocabulary():
    assert normalize_status("TIMED") == "SCHEDULED"
    assert normalize_status("IN_PLAY") == "LIVE"
    assert normalize_status("PAUSED") == "LIVE"
    assert normalize_status("FINISHED") == "FINISHED"
    assert normalize_status("POSTPONED") == "POSTPONED"


def test_phase_label_maps_stages():
    assert phase_label("GROUP_STAGE") == "Grupos"
    assert phase_label("LAST_32") == "16vos"
    assert phase_label("LAST_16") == "8vos"
    assert phase_label("FINAL") == "Final"
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_fixtures.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.live.fixtures`.

- [ ] **Step 4: Implementar `oraculo/live/fixtures.py`**

```python
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from oraculo.live.names import to_canonical

# football-data.org stage -> etiqueta de fase de OlorACulo
PHASE_LABELS: dict[str, str] = {
    "GROUP_STAGE": "Grupos",
    "LAST_32": "16vos",
    "LAST_16": "8vos",
    "QUARTER_FINALS": "4tos",
    "SEMI_FINALS": "Semis",
    "THIRD_PLACE": "3er puesto",
    "FINAL": "Final",
}

# Orden canónico de fases (para ordenar el cuadro)
PHASE_ORDER: tuple[str, ...] = (
    "GROUP_STAGE", "LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL",
)

# Vocabulario de status real de football-data.org -> 4 estados canónicos de OlorACulo.
_STATUS_MAP: dict[str, str] = {
    "FINISHED": "FINISHED",
    "AWARDED": "FINISHED",
    "IN_PLAY": "LIVE",
    "PAUSED": "LIVE",
    "SCHEDULED": "SCHEDULED",
    "TIMED": "SCHEDULED",
    "POSTPONED": "POSTPONED",
    "SUSPENDED": "POSTPONED",
    "CANCELLED": "POSTPONED",
}


def phase_label(stage: str) -> str:
    return PHASE_LABELS.get(stage, stage)


def normalize_status(raw: str) -> str:
    return _STATUS_MAP.get(raw, "SCHEDULED")


@dataclass(frozen=True)
class Fixture:
    id: int
    stage: str
    group: Optional[str]
    home: Optional[str]
    away: Optional[str]
    kickoff_utc: datetime.datetime
    status: str
    home_goals: Optional[int]
    away_goals: Optional[int]

    @property
    def is_finished(self) -> bool:
        return self.status == "FINISHED"

    @property
    def resolved(self) -> bool:
        return self.home is not None and self.away is not None


def _name(team: dict | None) -> Optional[str]:
    if not team or team.get("name") is None:
        return None
    return to_canonical(team["name"])


def _group(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # "GROUP_J" -> "J"
    return raw.replace("GROUP_", "").strip() or None


def _parse_dt(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_fixtures(raw: dict) -> list[Fixture]:
    out: list[Fixture] = []
    for m in raw.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        out.append(
            Fixture(
                id=int(m["id"]),
                stage=str(m.get("stage", "")),
                group=_group(m.get("group")),
                home=_name(m.get("homeTeam")),
                away=_name(m.get("awayTeam")),
                kickoff_utc=_parse_dt(m["utcDate"]),
                status=normalize_status(str(m.get("status", "SCHEDULED"))),
                home_goals=ft.get("home"),
                away_goals=ft.get("away"),
            )
        )
    return out
```

- [ ] **Step 5: Correr el test (todavía falla por `names`)**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_fixtures.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.live.names` → se resuelve en Task 4. Continuar a Task 4 antes de commitear.

---

### Task 4: Alias map de nombres (API ↔ canónico)

**Files:**
- Create: `oraculo/live/names.py`
- Test: `tests/test_live_names.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_live_names.py`:
```python
from pathlib import Path

from oraculo.live.names import to_canonical, ALIASES
from oraculo.tournament.config import load_config

WC = Path(__file__).resolve().parent.parent / "data" / "wc2026.yaml"


def test_known_api_spellings_map_to_canonical():
    assert to_canonical("Bosnia-Herzegovina") == "Bosnia and Herzegovina"
    assert to_canonical("Cape Verde Islands") == "Cape Verde"
    assert to_canonical("Congo DR") == "DR Congo"
    assert to_canonical("Czechia") == "Czech Republic"


def test_identity_for_already_canonical():
    assert to_canonical("Argentina") == "Argentina"
    assert to_canonical("South Korea") == "South Korea"  # la API ya usa este nombre


def test_unknown_name_falls_back_to_itself():
    assert to_canonical("Atlantis") == "Atlantis"


def test_all_48_wc_teams_are_covered():
    teams = set(load_config(WC).teams)
    covered = set(ALIASES.values())
    missing = teams - covered
    assert not missing, f"equipos del Mundial sin entrada en ALIASES: {sorted(missing)}"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_names.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.live.names`.

- [ ] **Step 3: Implementar `oraculo/live/names.py`**

Nota: las claves "spelling API → canónico" se ajustan con la lista real obtenida en Task 1, Step 3. Los valores deben cubrir los 48 nombres canónicos de `wc2026.yaml`. Identidad para los que ya coinciden.

```python
from __future__ import annotations

# Equipos canónicos del Mundial 2026 (deben coincidir con data/wc2026.yaml).
_CANONICAL = [
    "Mexico", "South Africa", "South Korea", "Czech Republic",
    "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
    "Brazil", "Morocco", "Haiti", "Scotland",
    "United States", "Paraguay", "Australia", "Turkey",
    "Germany", "Curaçao", "Ivory Coast", "Ecuador",
    "Netherlands", "Japan", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    "France", "Senegal", "Iraq", "Norway",
    "Argentina", "Algeria", "Austria", "Jordan",
    "Portugal", "DR Congo", "Uzbekistan", "Colombia",
    "England", "Croatia", "Ghana", "Panama",
]

# Spellings de la API que difieren del canónico (CONFIRMADO con /competitions/WC/teams en Task 1).
# Solo 4 difieren; el resto coincide (South Korea, United States, Turkey, Ivory Coast, Curaçao ya OK).
_OVERRIDES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
}

# Mapa final: identidad para cada canónico + overrides de la API.
ALIASES: dict[str, str] = {name: name for name in _CANONICAL}
ALIASES.update(_OVERRIDES)


def to_canonical(api_name: str) -> str:
    return ALIASES.get(api_name, api_name)
```

- [ ] **Step 4: Correr ambos tests (names + fixtures)**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_names.py tests/test_live_fixtures.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add oraculo/live/names.py oraculo/live/fixtures.py tests/test_live_names.py tests/test_live_fixtures.py tests/fixtures/wc_matches_sample.json
git commit -m "feat(live): Fixture domain model + parser + alias map de nombres"
```

---

### Task 5: Readiness pre-partido (T-60/30/15) + checks de verificación

**Files:**
- Create: `oraculo/live/schedule.py`
- Test: `tests/test_live_schedule.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_live_schedule.py`:
```python
import datetime

from oraculo.live.fixtures import Fixture
from oraculo.live.schedule import Readiness, readiness, verification_checks

UTC = datetime.timezone.utc


def _ko(hours_from_now: float, now: datetime.datetime) -> datetime.datetime:
    return now + datetime.timedelta(hours=hours_from_now)


def _fx(**kw):
    base = dict(
        id=1, stage="GROUP_STAGE", group="A", home="Argentina", away="Brazil",
        kickoff_utc=datetime.datetime(2026, 6, 20, 19, 0, tzinfo=UTC),
        status="SCHEDULED", home_goals=None, away_goals=None,
    )
    base.update(kw)
    return Fixture(**base)


def test_readiness_far_away():
    now = datetime.datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    assert readiness(now, _ko(9, now)) == Readiness.LEJOS


def test_readiness_t60_t30_t15():
    now = datetime.datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
    assert readiness(now, now + datetime.timedelta(minutes=50)) == Readiness.T60
    assert readiness(now, now + datetime.timedelta(minutes=25)) == Readiness.T30
    assert readiness(now, now + datetime.timedelta(minutes=10)) == Readiness.T15


def test_readiness_live_and_final_use_status():
    now = datetime.datetime(2026, 6, 20, 19, 30, tzinfo=UTC)
    assert readiness(now, now - datetime.timedelta(minutes=5), status="LIVE") == Readiness.EN_VIVO
    assert readiness(now, now - datetime.timedelta(hours=3), status="FINISHED") == Readiness.FINAL


def test_verification_checks_all_ok():
    checks = verification_checks(_fx())
    assert all(c.ok for c in checks)
    assert {c.label for c in checks} >= {"Fixture confirmado", "Rivales resueltos", "No postergado"}


def test_verification_flags_postponed_and_unresolved():
    checks = verification_checks(_fx(status="POSTPONED", home=None))
    by_label = {c.label: c.ok for c in checks}
    assert by_label["No postergado"] is False
    assert by_label["Rivales resueltos"] is False
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_schedule.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.live.schedule`.

- [ ] **Step 3: Implementar `oraculo/live/schedule.py`**

```python
from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from oraculo.live.fixtures import Fixture


class Readiness(str, Enum):
    LEJOS = "LEJOS"
    T60 = "T60"
    T30 = "T30"
    T15 = "T15"
    EN_VIVO = "EN_VIVO"
    FINAL = "FINAL"


# Etiqueta legible para la UI.
READINESS_LABEL: dict[Readiness, str] = {
    Readiness.LEJOS: "Próximamente",
    Readiness.T60: "Predicción generada (T-60)",
    Readiness.T30: "Info re-verificada (T-30)",
    Readiness.T15: "Lockeado y listo (T-15)",
    Readiness.EN_VIVO: "En vivo",
    Readiness.FINAL: "Finalizado",
}


def readiness(
    now: datetime.datetime,
    kickoff: datetime.datetime,
    *,
    status: str | None = None,
) -> Readiness:
    if status == "FINISHED":
        return Readiness.FINAL
    if status == "LIVE":
        return Readiness.EN_VIVO
    minutes = (kickoff - now).total_seconds() / 60.0
    if minutes <= 0:
        return Readiness.EN_VIVO
    if minutes <= 15:
        return Readiness.T15
    if minutes <= 30:
        return Readiness.T30
    if minutes <= 60:
        return Readiness.T60
    return Readiness.LEJOS


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool


def verification_checks(fixture: Fixture) -> list[Check]:
    return [
        Check("Fixture confirmado", fixture.status in ("SCHEDULED", "LIVE", "FINISHED")),
        Check("Fecha/hora presente", fixture.kickoff_utc is not None),
        Check("No postergado", fixture.status != "POSTPONED"),
        Check("Rivales resueltos", fixture.resolved),
    ]
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_schedule.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/live/schedule.py tests/test_live_schedule.py
git commit -m "feat(live): readiness pre-partido (T-60/30/15) + checks de verificación"
```

---

### Task 6: Cliente de la API con cache local + modo offline

**Files:**
- Create: `oraculo/live/client.py`
- Test: `tests/test_live_client.py`

- [ ] **Step 1: Escribir el test que falla**

El test NO toca la red: monkeypatchea el fetch crudo y verifica el cacheo (TTL) y el fallback offline.

Crear `tests/test_live_client.py`:
```python
import json

import pytest

from oraculo.live import client as cl


def test_get_matches_fetches_and_caches(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, token):
        calls["n"] += 1
        return {"matches": [{"id": 1}]}

    monkeypatch.setattr(cl, "_http_get_json", fake_fetch)
    c = cl.LiveClient(token="x", cache_dir=tmp_path, ttl_seconds=999)

    a = c.get_matches()
    b = c.get_matches()  # segunda llamada: usa cache, no re-fetch
    assert a == b == {"matches": [{"id": 1}]}
    assert calls["n"] == 1
    assert (tmp_path / "matches.json").exists()


def test_offline_uses_stale_cache_when_fetch_fails(tmp_path, monkeypatch):
    (tmp_path / "matches.json").write_text(json.dumps({"matches": [{"id": 9}]}), encoding="utf-8")

    def boom(url, token):
        raise OSError("sin internet")

    monkeypatch.setattr(cl, "_http_get_json", boom)
    # ttl=0 fuerza el re-fetch, que falla -> debe caer al cache viejo
    c = cl.LiveClient(token="x", cache_dir=tmp_path, ttl_seconds=0)
    assert c.get_matches() == {"matches": [{"id": 9}]}


def test_raises_when_no_token_and_no_cache(tmp_path, monkeypatch):
    def boom(url, token):
        raise OSError("sin internet")

    monkeypatch.setattr(cl, "_http_get_json", boom)
    c = cl.LiveClient(token=None, cache_dir=tmp_path, ttl_seconds=0)
    with pytest.raises(cl.LiveDataError):
        c.get_matches()
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_client.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.live.client`.

- [ ] **Step 3: Implementar `oraculo/live/client.py`**

```python
from __future__ import annotations

import datetime
import json
import time
import urllib.request
from pathlib import Path
from typing import Optional

BASE_URL = "https://api.football-data.org/v4/competitions/WC"
DEFAULT_CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "cache"


class LiveDataError(RuntimeError):
    """No se pudo obtener data ni de la API ni del cache."""


def _http_get_json(url: str, token: Optional[str]) -> dict:
    headers = {"X-Auth-Token": token} if token else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (URL fija de la API)
        return json.loads(resp.read().decode("utf-8"))


class LiveClient:
    """Cliente football-data.org con cache local (TTL) y modo offline.

    Si la API falla y hay cache (aunque esté vencido), devuelve el cache.
    Si no hay ninguna de las dos, levanta LiveDataError."""

    def __init__(
        self,
        token: Optional[str],
        *,
        cache_dir: Path = DEFAULT_CACHE,
        ttl_seconds: int = 60,
    ) -> None:
        self.token = token
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.fetched_at: Optional[datetime.datetime] = None

    def _cache_path(self, name: str) -> Path:
        return self.cache_dir / f"{name}.json"

    def _fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age <= self.ttl_seconds

    def _read_cache(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        self.fetched_at = datetime.datetime.fromtimestamp(
            path.stat().st_mtime, tz=datetime.timezone.utc
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def _get(self, name: str, url: str) -> dict:
        path = self._cache_path(name)
        if self._fresh(path):
            return self._read_cache(path)  # type: ignore[return-value]
        try:
            data = _http_get_json(url, self.token)
        except Exception:
            cached = self._read_cache(path)
            if cached is not None:
                return cached
            raise LiveDataError(f"sin API ni cache para {name}")
        path.write_text(json.dumps(data), encoding="utf-8")
        self.fetched_at = datetime.datetime.now(tz=datetime.timezone.utc)
        return data

    def get_matches(self) -> dict:
        return self._get("matches", f"{BASE_URL}/matches")

    def get_standings(self) -> dict:
        return self._get("standings", f"{BASE_URL}/standings")
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_live_client.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/live/client.py tests/test_live_client.py
git commit -m "feat(live): cliente football-data.org con cache TTL y modo offline"
```

---

## FASE L2 — Report + Verify

### Task 7: Predictor congelado (anti-leakage)

**Files:**
- Create: `oraculo/verify/predictor.py`
- Test: `tests/test_verify_predictor.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_verify_predictor.py`:
```python
import datetime

from oraculo.match import Match
from oraculo.verify.predictor import WC_CUTOFF, frozen_poisson


def _m(year, month, day, hg, ag):
    return Match(
        date=datetime.date(year, month, day),
        home="Argentina", away="Brazil", home_goals=hg, away_goals=ag,
        tournament="FIFA World Cup", neutral=True,
    )


def test_cutoff_default_is_wc_start():
    assert WC_CUTOFF == datetime.date(2026, 6, 11)


def test_frozen_model_ignores_matches_on_or_after_cutoff():
    pre = [_m(2025, 1, 1, 3, 0), _m(2025, 6, 1, 2, 0)]
    post = [_m(2026, 6, 12, 0, 5)]  # un partido del Mundial que NO debe influir
    only_pre = frozen_poisson(pre)
    with_post = frozen_poisson(pre + post)
    # las predicciones deben ser idénticas: el partido post-cutoff fue descartado
    a = only_pre.predict("Argentina", "Brazil", neutral=True)
    b = with_post.predict("Argentina", "Brazil", neutral=True)
    assert a.probs == b.probs
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_predictor.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.verify.predictor`.

- [ ] **Step 3: Implementar `oraculo/verify/predictor.py`**

```python
from __future__ import annotations

import datetime
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel

# Inicio del Mundial 2026: las predicciones se congelan a datos previos a esta fecha.
WC_CUTOFF = datetime.date(2026, 6, 11)

# Misma config calibrada que usa la app.
_DEFAULT = PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)


def frozen_poisson(
    matches: Iterable[Match],
    *,
    cutoff: datetime.date = WC_CUTOFF,
    config: Optional[PoissonConfig] = None,
) -> PoissonModel:
    """Poisson entrenado SOLO con partidos anteriores al corte → toda predicción
    del Mundial es out-of-sample y determinista."""
    pre = [m for m in matches if m.date < cutoff]
    return PoissonModel(config or _DEFAULT).fit(pre)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_predictor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/verify/predictor.py tests/test_verify_predictor.py
git commit -m "feat(verify): predictor Poisson congelado al inicio del Mundial (anti-leakage)"
```

---

### Task 8: Match report detallado (riguroso + extras)

**Files:**
- Create: `oraculo/report/match_report.py`
- Test: `tests/test_match_report.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_match_report.py`:
```python
import numpy as np

from oraculo.report.match_report import (
    MatchReport,
    btts_prob,
    over_prob,
    build_match_report,
)
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.match import Match
import datetime


def test_btts_and_over_on_known_matrix():
    m = np.zeros((3, 3))
    m[0, 0] = 0.25  # 0-0
    m[1, 0] = 0.25  # 1-0
    m[1, 1] = 0.25  # 1-1
    m[2, 2] = 0.25  # 2-2 (over 2.5)
    # BTTS = casos donde ambos > 0 = (1,1)+(2,2) = 0.5
    assert abs(btts_prob(m) - 0.5) < 1e-9
    # over 2.5 = total >= 3 = solo (2,2) = 0.25
    assert abs(over_prob(m, line=2.5) - 0.25) < 1e-9


def _model():
    matches = [
        Match(datetime.date(2024, 1, d), "Argentina", "Brazil", 2, 1, "Friendly", True)
        for d in range(1, 6)
    ]
    return PoissonModel(PoissonConfig(lr=0.05)).fit(matches)


def test_build_match_report_shape():
    r = build_match_report(_model(), "Argentina", "Brazil", neutral=True)
    assert isinstance(r, MatchReport)
    assert abs(r.p_home + r.p_draw + r.p_away - 1.0) < 1e-6
    assert 0.0 <= r.btts <= 1.0
    assert 0.0 <= r.over25 <= 1.0
    assert len(r.top_scores) == 5
    # extras especulativos presentes y marcados
    assert r.speculative.top_scorer_team in ("Argentina", "Brazil")
    assert "–" in r.speculative.cards_band
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_report.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.report.match_report`.

- [ ] **Step 3: Implementar `oraculo/report/match_report.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services import top_scorelines


@dataclass
class Speculative:
    """Extras NO rigurosos (no salen del modelo Poisson). Marcar en la UI como estimación."""
    top_scorer_team: str
    cards_band: str


@dataclass
class MatchReport:
    home: str
    away: str
    p_home: float
    p_draw: float
    p_away: float
    xg_home: float
    xg_away: float
    top_scores: list[tuple[tuple[int, int], float]]
    btts: float
    over25: float
    speculative: Speculative


def btts_prob(matrix: np.ndarray) -> float:
    """P(ambos marcan) = 1 - P(local=0) - P(visit=0) + P(0,0)."""
    p_home0 = float(matrix[0, :].sum())
    p_away0 = float(matrix[:, 0].sum())
    return 1.0 - p_home0 - p_away0 + float(matrix[0, 0])


def over_prob(matrix: np.ndarray, line: float = 2.5) -> float:
    """P(total de goles > line)."""
    threshold = int(line) + 1  # 2.5 -> total >= 3
    total = 0.0
    rows, cols = matrix.shape
    for i in range(rows):
        for j in range(cols):
            if i + j >= threshold:
                total += float(matrix[i, j])
    return total


def _cards_band(p_home: float, p_draw: float, p_away: float) -> str:
    """Heurística: cuanto más parejo el cruce, mayor la banda de tarjetas estimada."""
    spread = max(p_home, p_draw, p_away)
    if spread < 0.40:
        return "4–6"
    if spread < 0.55:
        return "3–5"
    return "2–4"


def build_match_report(model, home: str, away: str, *, neutral: bool = True) -> MatchReport:
    pred = model.predict(home, away, neutral=neutral)
    matrix = pred.score_matrix
    top_scorer = home if (pred.xg_home or 0) >= (pred.xg_away or 0) else away
    return MatchReport(
        home=home,
        away=away,
        p_home=pred.p_home,
        p_draw=pred.p_draw,
        p_away=pred.p_away,
        xg_home=float(pred.xg_home) if pred.xg_home is not None else 0.0,
        xg_away=float(pred.xg_away) if pred.xg_away is not None else 0.0,
        top_scores=top_scorelines(matrix, 5),
        btts=btts_prob(matrix),
        over25=over_prob(matrix, 2.5),
        speculative=Speculative(
            top_scorer_team=top_scorer,
            cards_band=_cards_band(pred.p_home, pred.p_draw, pred.p_away),
        ),
    )
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_report.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/report/match_report.py tests/test_match_report.py
git commit -m "feat(report): match report detallado (1X2, marcadores, xG, BTTS, O/U) + extras"
```

---

### Task 9: Scoring de verificación (predicho vs real)

**Files:**
- Create: `oraculo/verify/scoring.py`
- Test: `tests/test_verify_scoring.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_verify_scoring.py`:
```python
from oraculo.verify.scoring import (
    actual_outcome,
    score_match,
    aggregate,
    calibration_bins,
)


def test_actual_outcome():
    assert actual_outcome(2, 0) == "home"
    assert actual_outcome(1, 1) == "draw"
    assert actual_outcome(0, 3) == "away"


def test_score_match_hit_and_metrics():
    # predijo local (0.7) y ganó local -> acierto
    s = score_match(fixture_id=1, probs=(0.7, 0.2, 0.1), home_goals=2, away_goals=0)
    assert s.outcome_pred == "home"
    assert s.outcome_actual == "home"
    assert s.hit is True
    assert s.brier >= 0.0 and s.rps >= 0.0


def test_score_match_miss():
    s = score_match(fixture_id=2, probs=(0.6, 0.3, 0.1), home_goals=0, away_goals=1)
    assert s.outcome_pred == "home"
    assert s.outcome_actual == "away"
    assert s.hit is False


def test_aggregate_counts_and_means():
    scores = [
        score_match(1, (0.7, 0.2, 0.1), 2, 0),  # hit
        score_match(2, (0.6, 0.3, 0.1), 0, 1),  # miss
    ]
    summ = aggregate(scores)
    assert summ.n == 2
    assert summ.hit_rate == 0.5
    assert summ.mean_brier > 0.0
    assert summ.mean_rps > 0.0


def test_calibration_bins_groups_predictions():
    # pares (prob_predicha_de_local, ganó_local?)
    pairs = [(0.9, True), (0.85, True), (0.2, False), (0.1, False)]
    bins = calibration_bins(pairs, n_bins=2)
    assert len(bins) == 2
    # cada bin: (centro, prob_media_predicha, frecuencia_real, n)
    low, high = bins[0], bins[1]
    assert low.n == 2 and high.n == 2
    assert high.observed == 1.0   # los dos de prob alta ganaron
    assert low.observed == 0.0    # los dos de prob baja no
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_scoring.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.verify.scoring`.

- [ ] **Step 3: Implementar `oraculo/verify/scoring.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from oraculo.evaluate.metrics import brier_score, rps
from oraculo.models.base import OUTCOMES

Probs = tuple[float, float, float]


def actual_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


@dataclass
class MatchScore:
    fixture_id: int
    probs: Probs
    outcome_pred: str
    outcome_actual: str
    hit: bool
    brier: float
    rps: float


def score_match(fixture_id: int, probs: Probs, home_goals: int, away_goals: int) -> MatchScore:
    actual = actual_outcome(home_goals, away_goals)
    pred = OUTCOMES[max(range(3), key=lambda i: probs[i])]
    return MatchScore(
        fixture_id=fixture_id,
        probs=probs,
        outcome_pred=pred,
        outcome_actual=actual,
        hit=(pred == actual),
        brier=brier_score(probs, actual),
        rps=rps(probs, actual),
    )


@dataclass
class Summary:
    n: int
    hit_rate: float
    mean_brier: float
    mean_rps: float


def aggregate(scores: list[MatchScore]) -> Summary:
    n = len(scores)
    if n == 0:
        return Summary(0, 0.0, 0.0, 0.0)
    return Summary(
        n=n,
        hit_rate=sum(s.hit for s in scores) / n,
        mean_brier=sum(s.brier for s in scores) / n,
        mean_rps=sum(s.rps for s in scores) / n,
    )


@dataclass
class CalibrationBin:
    center: float
    predicted: float
    observed: float
    n: int


def calibration_bins(pairs: list[tuple[float, bool]], n_bins: int = 5) -> list[CalibrationBin]:
    """pairs: (prob predicha de un evento, si ocurrió). Devuelve n_bins ordenados."""
    edges = [i / n_bins for i in range(n_bins + 1)]
    out: list[CalibrationBin] = []
    for b in range(n_bins):
        lo, hi = edges[b], edges[b + 1]
        chunk = [(p, occ) for p, occ in pairs if (lo <= p < hi) or (b == n_bins - 1 and p == hi)]
        n = len(chunk)
        predicted = sum(p for p, _ in chunk) / n if n else 0.0
        observed = sum(1 for _, occ in chunk if occ) / n if n else 0.0
        out.append(CalibrationBin(center=(lo + hi) / 2, predicted=predicted, observed=observed, n=n))
    return out
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_scoring.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/verify/scoring.py tests/test_verify_scoring.py
git commit -m "feat(verify): scoring predicho-vs-real (acierto, Brier, RPS) + calibración"
```

---

### Task 10: Bitácora de predicciones (log JSON)

**Files:**
- Create: `oraculo/verify/log.py`
- Test: `tests/test_verify_log.py`

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_verify_log.py`:
```python
import datetime

from oraculo.verify.log import append_snapshot, load_log


def test_append_and_load(tmp_path):
    path = tmp_path / "predictions_log.json"
    now = datetime.datetime(2026, 6, 20, 18, 0, tzinfo=datetime.timezone.utc)
    append_snapshot(path, fixture_id=1, probs=(0.7, 0.2, 0.1), top_score=(2, 0), now=now)
    log = load_log(path)
    assert "1" in log
    assert log["1"]["p_home"] == 0.7
    assert log["1"]["top_score"] == [2, 0]


def test_append_is_idempotent_per_fixture(tmp_path):
    path = tmp_path / "predictions_log.json"
    append_snapshot(path, 1, (0.7, 0.2, 0.1), (2, 0))
    append_snapshot(path, 1, (0.1, 0.2, 0.7), (0, 2))  # no debe pisar el primero
    log = load_log(path)
    assert log["1"]["p_home"] == 0.7


def test_load_missing_returns_empty(tmp_path):
    assert load_log(tmp_path / "nope.json") == {}
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_log.py -v`
Expected: FAIL con `ModuleNotFoundError: oraculo.verify.log`.

- [ ] **Step 3: Implementar `oraculo/verify/log.py`**

```python
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Optional

Probs = tuple[float, float, float]


def load_log(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def append_snapshot(
    path: str | Path,
    fixture_id: int,
    probs: Probs,
    top_score: tuple[int, int],
    *,
    now: Optional[datetime.datetime] = None,
) -> None:
    """Registra el snapshot de una predicción la PRIMERA vez que se ve el fixture.
    Idempotente por fixture_id (no pisa el snapshot original)."""
    p = Path(path)
    log = load_log(p)
    key = str(fixture_id)
    if key in log:
        return
    ts = (now or datetime.datetime.now(tz=datetime.timezone.utc)).isoformat()
    log[key] = {
        "timestamp": ts,
        "p_home": probs[0],
        "p_draw": probs[1],
        "p_away": probs[2],
        "top_score": list(top_score),
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(log, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_verify_log.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add oraculo/verify/log.py tests/test_verify_log.py
git commit -m "feat(verify): bitácora de snapshots de predicciones (idempotente por fixture)"
```

---

## FASE L3 — UI

### Task 11: Componentes de charts reutilizables

**Files:**
- Create: `app/charts.py`
- Test: `tests/test_app_charts.py`

- [ ] **Step 1: Escribir el test que falla**

Los charts Altair se testean por construcción (no rendering): que devuelvan un `alt.Chart` sin romper.

Crear `tests/test_app_charts.py`:
```python
import pandas as pd
import altair as alt

from app.charts import win_prob_bar, ranking_bar, calibration_chart


def test_win_prob_bar_builds():
    ch = win_prob_bar("Argentina", "Brazil", 0.6, 0.25, 0.15)
    assert isinstance(ch, alt.LayerChart) or isinstance(ch, alt.Chart)


def test_ranking_bar_builds():
    df = pd.DataFrame({"Equipo": ["A", "B"], "Valor": [10, 5]})
    ch = ranking_bar(df, value="Valor", title="x")
    assert isinstance(ch, alt.Chart) or hasattr(ch, "to_dict")


def test_calibration_chart_builds():
    df = pd.DataFrame({"predicted": [0.2, 0.8], "observed": [0.1, 0.9], "n": [3, 4]})
    ch = calibration_chart(df)
    assert hasattr(ch, "to_dict")
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_charts.py -v`
Expected: FAIL con `ModuleNotFoundError: app.charts`.

- [ ] **Step 3: Implementar `app/charts.py`**

```python
from __future__ import annotations

import altair as alt
import pandas as pd

# Paleta "Álbum '86" (alineada con streamlit_app.py)
GREEN = "#3c7a4e"
ORANGE = "#e8a33d"
MUTED = "#c9bfa3"
INK = "#2b2b2b"


def win_prob_bar(home: str, away: str, p_home: float, p_draw: float, p_away: float) -> alt.Chart:
    df = pd.DataFrame(
        {
            "Resultado": [f"Gana {home}", "Empate", f"Gana {away}"],
            "Probabilidad": [p_home, p_draw, p_away],
            "orden": [0, 1, 2],
        }
    )
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Probabilidad:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(
                    domain=[f"Gana {home}", "Empate", f"Gana {away}"],
                    range=[GREEN, MUTED, ORANGE],
                ),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            order=alt.Order("orden:Q"),
            tooltip=["Resultado", alt.Tooltip("Probabilidad:Q", format=".1%")],
        )
        .properties(height=84)
    )


def ranking_bar(df: pd.DataFrame, *, value: str, title: str, label: str = "Equipo") -> alt.Chart:
    bars = (
        alt.Chart(df)
        .mark_bar(color=GREEN, cornerRadiusEnd=5)
        .encode(
            x=alt.X(f"{value}:Q", title=title),
            y=alt.Y(f"{label}:N", sort="-x", title=None),
            tooltip=[alt.Tooltip(f"{value}:Q", format=".1f")],
        )
    )
    text = bars.mark_text(align="left", dx=4, color=INK, fontWeight="bold").encode(
        text=alt.Text(f"{value}:Q", format=".1f")
    )
    return (bars + text).properties(height=30 * len(df) + 40)


def calibration_chart(df: pd.DataFrame) -> alt.LayerChart:
    """df: columnas predicted, observed, n. Dibuja la curva vs la diagonal ideal."""
    diag = (
        alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]}))
        .mark_line(strokeDash=[5, 5], color=MUTED)
        .encode(x="x:Q", y="y:Q")
    )
    pts = (
        alt.Chart(df)
        .mark_circle(color=ORANGE, size=120)
        .encode(
            x=alt.X("predicted:Q", title="Probabilidad predicha", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("observed:Q", title="Frecuencia real", scale=alt.Scale(domain=[0, 1])),
            size=alt.Size("n:Q", legend=None),
            tooltip=["predicted", "observed", "n"],
        )
    )
    return (diag + pts).properties(height=300)
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_charts.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/charts.py tests/test_app_charts.py
git commit -m "feat(app): componentes Altair reutilizables (win bar, ranking, calibración)"
```

---

### Task 12: Capa de vista live (glue cacheado para Streamlit)

**Files:**
- Create: `app/live_view.py`
- Test: `tests/test_app_live_view.py`

Esta capa agrupa fixtures por fase y arma las filas que la UI consume. Funciones puras (sin `st`), testeables.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_app_live_view.py`:
```python
import datetime
import json
from pathlib import Path

from oraculo.live.fixtures import parse_fixtures
from app.live_view import group_by_phase, upcoming_rows, finished_rows

SAMPLE = Path(__file__).parent / "fixtures" / "wc_matches_sample.json"
NOW = datetime.datetime(2026, 6, 15, 12, 0, tzinfo=datetime.timezone.utc)


def _fixtures():
    return parse_fixtures(json.loads(SAMPLE.read_text(encoding="utf-8")))


def test_group_by_phase_orders_phases():
    grouped = group_by_phase(_fixtures())
    labels = list(grouped.keys())
    assert labels[0] == "Grupos"
    assert "Semis" in labels


def test_upcoming_rows_excludes_finished():
    rows = upcoming_rows(_fixtures(), now=NOW)
    ids = {r["id"] for r in rows}
    assert 1001 not in ids        # FINISHED
    assert 1002 in ids            # SCHEDULED futuro
    # cada fila trae estado de readiness legible
    assert all("estado" in r for r in rows)


def test_finished_rows_only_finished():
    rows = finished_rows(_fixtures())
    assert [r["id"] for r in rows] == [1001]
    assert rows[0]["marcador"] == "2–0"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_live_view.py -v`
Expected: FAIL con `ModuleNotFoundError: app.live_view`.

- [ ] **Step 3: Implementar `app/live_view.py`**

```python
from __future__ import annotations

import datetime
from collections import OrderedDict

from oraculo.live.fixtures import Fixture, PHASE_ORDER, phase_label
from oraculo.live.schedule import READINESS_LABEL, readiness, verification_checks


def group_by_phase(fixtures: list[Fixture]) -> "OrderedDict[str, list[Fixture]]":
    order = {stage: i for i, stage in enumerate(PHASE_ORDER)}
    grouped: dict[str, list[Fixture]] = {}
    for f in fixtures:
        grouped.setdefault(phase_label(f.stage), []).append(f)
    return OrderedDict(
        sorted(grouped.items(), key=lambda kv: order.get(_stage_for_label(kv[0]), 99))
    )


def _stage_for_label(label: str) -> str:
    for stage in PHASE_ORDER:
        if phase_label(stage) == label:
            return stage
    return label


def _matchup(f: Fixture) -> str:
    return f"{f.home or '¿?'} vs {f.away or '¿?'}"


def upcoming_rows(fixtures: list[Fixture], *, now: datetime.datetime) -> list[dict]:
    rows: list[dict] = []
    for f in sorted(fixtures, key=lambda x: x.kickoff_utc):
        if f.is_finished:
            continue
        state = readiness(now, f.kickoff_utc, status=f.status)
        rows.append(
            {
                "id": f.id,
                "fase": phase_label(f.stage),
                "partido": _matchup(f),
                "kickoff": f.kickoff_utc,
                "estado": READINESS_LABEL[state],
                "checks": verification_checks(f),
            }
        )
    return rows


def finished_rows(fixtures: list[Fixture]) -> list[dict]:
    rows: list[dict] = []
    for f in sorted(fixtures, key=lambda x: x.kickoff_utc):
        if not f.is_finished:
            continue
        rows.append(
            {
                "id": f.id,
                "fase": phase_label(f.stage),
                "partido": _matchup(f),
                "marcador": f"{f.home_goals}–{f.away_goals}",
                "home": f.home,
                "away": f.away,
                "home_goals": f.home_goals,
                "away_goals": f.away_goals,
            }
        )
    return rows
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_live_view.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/live_view.py tests/test_app_live_view.py
git commit -m "feat(app): live_view — agrupar por fase + filas de próximos/finalizados"
```

---

### Task 13: Integrar pestañas En vivo / Cuadro / Verificación en la app

**Files:**
- Modify: `app/streamlit_app.py` (agregar imports, 3 pestañas nuevas, helper de token + cliente cacheado)

Esta task no tiene test unitario (es UI Streamlit); se valida corriendo la app (Step 5).

- [ ] **Step 1: Agregar imports y recursos cacheados**

En `app/streamlit_app.py`, después de los imports existentes (tras `from app.flags import with_flag`), agregar:
```python
import datetime as _dt

from oraculo.live.client import LiveClient, LiveDataError
from oraculo.live.fixtures import parse_fixtures
from oraculo.verify.predictor import frozen_poisson
from oraculo.report.match_report import build_match_report
from oraculo.verify.scoring import score_match, aggregate, calibration_bins
from app.live_view import group_by_phase, upcoming_rows, finished_rows
from app.charts import win_prob_bar, ranking_bar, calibration_chart
```

Después de `def get_config()` (zona de `@st.cache_resource`), agregar:
```python
@st.cache_resource
def get_frozen():
    return frozen_poisson(get_matches())


def _token():
    try:
        return st.secrets["FOOTBALL_DATA_TOKEN"]
    except Exception:
        import os
        return os.environ.get("FOOTBALL_DATA_TOKEN")


@st.cache_data(ttl=60)
def get_fixtures():
    client = LiveClient(_token())
    raw = client.get_matches()
    return parse_fixtures(raw), client.fetched_at
```

- [ ] **Step 2: Ampliar la barra de pestañas**

Reemplazar el bloque de `st.tabs([...])` existente por:
```python
tab_live, tab_bracket, tab_match, tab_cup, tab_verify = st.tabs(
    ["🔴  En vivo", "🗺️  Cuadro", "⚽  Partido", "🏆  Mundial", "🎯  Verificación"]
)
```
(Las pestañas previas Equipos/Métricas se reemplazan; el contenido de "Métricas" pasa a "Verificación" en Step 4. La de "Equipos" se elimina — su comparación de ratings es secundaria; si la querés conservar, movela como expander dentro de "Partido".)

- [ ] **Step 3: Implementar pestaña "En vivo"**

Agregar (antes del bloque `with tab_match:`):
```python
with tab_live:
    st.subheader("Partidos del Mundial en vivo")
    try:
        fixtures, fetched_at = get_fixtures()
    except LiveDataError:
        st.error("Sin datos: configurá FOOTBALL_DATA_TOKEN en .streamlit/secrets.toml.")
        fixtures, fetched_at = [], None

    if fetched_at:
        st.caption(f"Datos al {fetched_at:%Y-%m-%d %H:%M UTC}")

    if fixtures:
        now = _dt.datetime.now(tz=_dt.timezone.utc)
        st.markdown("#### ⏱️ Próximos")
        for r in upcoming_rows(fixtures, now=now)[:8]:
            cols = st.columns([4, 3, 3])
            cols[0].markdown(f"**{r['partido']}**  ·  _{r['fase']}_")
            cols[1].markdown(f"🕒 {r['kickoff']:%d/%m %H:%M} UTC")
            cols[2].markdown(f"🔖 {r['estado']}")
            ok = sum(c.ok for c in r["checks"])
            cols[2].caption(f"Verificación: {ok}/{len(r['checks'])} checks")

        st.markdown("#### ✅ Resultados recientes (real vs predicho)")
        model = get_frozen()
        for r in finished_rows(fixtures)[-8:]:
            pred = model.predict(r["home"], r["away"], neutral=True)
            s = score_match(r["id"], pred.probs, r["home_goals"], r["away_goals"])
            mark = "✅" if s.hit else "❌"
            st.markdown(
                f"<div class='scoreline'>{mark} {with_flag(r['home'])} "
                f"<b>{r['marcador']}</b> {with_flag(r['away'])} · "
                f"predicho: {s.outcome_pred} · RPS {s.rps:.3f}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Cuando haya partidos cargados, aparecen acá con su predicción.")
```

- [ ] **Step 4: Implementar pestañas "Cuadro" y "Verificación"**

Agregar (después del bloque `with tab_cup:` existente):
```python
with tab_bracket:
    st.subheader("El cuadro, fase por fase")
    try:
        fixtures, _ = get_fixtures()
    except LiveDataError:
        fixtures = []
    if fixtures:
        model = get_frozen()
        for fase, fs in group_by_phase(fixtures).items():
            st.markdown(f"### {fase}")
            for f in sorted(fs, key=lambda x: x.kickoff_utc):
                if not f.resolved:
                    st.markdown(f"<div class='scoreline'>⏳ Por definirse</div>", unsafe_allow_html=True)
                    continue
                pred = model.predict(f.home, f.away, neutral=True)
                if f.is_finished:
                    s = score_match(f.id, pred.probs, f.home_goals, f.away_goals)
                    mark = "✅" if s.hit else "❌"
                    st.markdown(
                        f"<div class='scoreline'>{mark} {with_flag(f.home)} "
                        f"<b>{f.home_goals}–{f.away_goals}</b> {with_flag(f.away)} "
                        f"· predicho {s.outcome_pred}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    fav = f.home if pred.p_home >= pred.p_away else f.away
                    st.markdown(
                        f"<div class='scoreline'>🔮 {with_flag(f.home)} vs {with_flag(f.away)} "
                        f"· favorito: <b>{fav}</b> "
                        f"({max(pred.p_home, pred.p_away) * 100:.0f}%)</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("El cuadro se arma con los fixtures de la API.")

with tab_verify:
    st.subheader("¿Cuánto le acierta el oráculo?")
    st.markdown(
        '<p class="caption">Métricas sobre los partidos YA jugados del Mundial. '
        'El modelo está congelado al inicio del torneo (sin data leakage).</p>',
        unsafe_allow_html=True,
    )
    try:
        fixtures, _ = get_fixtures()
    except LiveDataError:
        fixtures = []
    model = get_frozen()
    scores = []
    home_pairs = []
    for f in finished_rows(fixtures):
        pred = model.predict(f["home"], f["away"], neutral=True)
        scores.append(score_match(f["id"], pred.probs, f["home_goals"], f["away_goals"]))
        home_pairs.append((pred.p_home, f["home_goals"] > f["away_goals"]))

    if scores:
        summ = aggregate(scores)
        c1, c2, c3 = st.columns(3)
        c1.metric("Aciertos 1X2", f"{summ.hit_rate * 100:.0f}%")
        c2.metric("Brier medio", f"{summ.mean_brier:.3f}")
        c3.metric("RPS medio", f"{summ.mean_rps:.3f}")
        import pandas as _pd
        bins = calibration_bins(home_pairs, n_bins=5)
        cdf = _pd.DataFrame(
            [{"predicted": b.predicted, "observed": b.observed, "n": b.n} for b in bins if b.n]
        )
        if not cdf.empty:
            st.markdown("#### Calibración (P(gana local) predicha vs real)")
            st.altair_chart(calibration_chart(cdf), use_container_width=True)
    else:
        st.info("Todavía no hay partidos jugados para verificar.")

    st.divider()
    st.markdown("#### Backtest histórico (walk-forward desde 2010)")
    if st.button("Revisar el álbum 📖", type="primary"):
        with st.spinner("Backtesteando uniforme, Elo y Poisson..."):
            metrics = model_metrics()
        mdf = pd.DataFrame([{"Modelo": k, **v} for k, v in metrics.items()]).sort_values("RPS")
        st.altair_chart(
            ranking_bar(mdf.rename(columns={"Modelo": "Equipo"}), value="RPS", title="RPS (menor = mejor)"),
            use_container_width=True,
        )
        st.dataframe(
            mdf.style.format({"RPS": "{:.4f}", "Brier": "{:.4f}", "LogLoss": "{:.4f}"}),
            hide_index=True, use_container_width=True,
        )
```

Eliminar los bloques `with tab_teams:` y `with tab_metrics:` antiguos (su rol lo cubren Cuadro/Verificación). Mantener intacto `with tab_cup:`.

- [ ] **Step 5: Enriquecer la pestaña "Partido" con el match report detallado**

Dentro de `with tab_match:`, después del bloque de "Marcadores más probables" existente (el `for (i, j), p in top_scorelines(...)`), agregar:
```python
    report = build_match_report(model, home, away, neutral=neutral)
    st.markdown("**Mercados derivados**")
    d1, d2 = st.columns(2)
    d1.metric("Ambos marcan (BTTS)", f"{report.btts * 100:.0f}%")
    d2.metric("Over 2.5 goles", f"{report.over25 * 100:.0f}%")
    st.markdown(
        f"<div class='caption'>⚠️ Estimación (no sale del modelo): "
        f"favorito a convertir <b>{report.speculative.top_scorer_team}</b> · "
        f"tarjetas estimadas {report.speculative.cards_band}.</div>",
        unsafe_allow_html=True,
    )
```

- [ ] **Step 6: Verificación manual (correr la app)**

Run: `.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py`
Expected: la app abre en http://localhost:8501 con 5 pestañas. Sin token, "En vivo"/"Cuadro"/"Verificación" muestran el mensaje de configurar el token (no crashean). "Partido" muestra los mercados derivados + extras; "Mundial" sigue funcionando.

- [ ] **Step 7: Correr toda la suite**

Run: `.\.venv\Scripts\python.exe -m pytest`
Expected: PASS (95 originales + los nuevos).

- [ ] **Step 8: Commit**

```bash
git add app/streamlit_app.py
git commit -m "feat(app): pestañas En vivo / Cuadro / Verificación + Partido enriquecido"
```

---

## FASE L4 — Pulido profesional

### Task 14: README + smoke test de imports + verificación final

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Test: `tests/test_smoke.py` (agregar import de los módulos nuevos)

- [ ] **Step 1: Ampliar el smoke test**

En `tests/test_smoke.py`, agregar una función:
```python
def test_new_live_modules_import():
    import oraculo.live.client
    import oraculo.live.fixtures
    import oraculo.live.names
    import oraculo.live.schedule
    import oraculo.report.match_report
    import oraculo.verify.predictor
    import oraculo.verify.scoring
    import oraculo.verify.log
    import app.charts
    import app.live_view
```

- [ ] **Step 2: Correr el smoke test**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke.py -v`
Expected: PASS.

- [ ] **Step 3: Documentar setup de la key en README**

Agregar a `README.md` una sección:
```markdown
## Datos en vivo del Mundial 2026

1. Conseguí una API key gratis en https://www.football-data.org/client/register
2. Copiá `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y pegá tu token
   (o exportá `FOOTBALL_DATA_TOKEN`).
3. Corré la app: las pestañas **En vivo**, **Cuadro** y **Verificación** se llenan solas.

Sin token, la app igual funciona con el histórico (Partido, Mundial) y usa el
último cache disponible en `data/cache/` (modo offline).
```

- [ ] **Step 4: Actualizar CLAUDE.md**

En `CLAUDE.md`, en "Estructura clave", agregar bajo `oraculo/`:
```
  live/                    # client (API+cache), names, fixtures, schedule (readiness)
  report/match_report.py   # 1X2, marcadores, xG, BTTS, O/U + extras especulativos
  verify/                  # predictor congelado, scoring, log de predicciones
```
Y bajo `app/`:
```
  charts.py                # componentes Altair reutilizables
  live_view.py             # agrupar fixtures por fase + filas próximos/finalizados
```
En "Pendientes opcionales", borrar la línea "Fijar partidos ya jugados del Mundial en curso" (ya resuelto).

- [ ] **Step 5: Verificación final completa**

Run: `.\.venv\Scripts\python.exe -m pytest`
Expected: PASS (toda la suite).

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md tests/test_smoke.py
git commit -m "docs: setup de datos en vivo + smoke test de módulos nuevos"
```

---

## Self-Review (cobertura spec → tasks)

| Requisito de la spec | Task(s) |
|----------------------|---------|
| API gratuita con key + cache + offline | 1, 6 |
| Alias de nombres API↔canónico (48 equipos) | 4 |
| Modelo `Fixture` + parser | 3 |
| Readiness T-60/30/15 + checks de verificación | 5 |
| Predicción detallada (riguroso + extras) | 8 |
| Anti-leakage (predictor congelado) | 7 |
| Scoring predicho-vs-real + calibración | 9 |
| Bitácora de predicciones | 10 |
| UI: En vivo · Cuadro (por fase) · Verificación | 12, 13 |
| Charts profesionales reutilizables | 11 |
| Cuadro Grupos/16vos/8vos/4tos/Semis/Final | 3 (PHASE_LABELS), 12, 13 |
| Errores/offline + banner timestamp | 6, 13 |
| Seguridad de la key | 2, 14 |
| Mantener 95 tests verdes | 13 (Step 6), 14 (Step 5) |

**Notas de integración (decisiones lockeadas):**
- Sin nuevas dependencias: cliente con `urllib.request` (stdlib).
- `MatchPrediction.probs` = `(p_home, p_draw, p_away)`; `score_match` recibe esa tupla.
- `score_matrix` por defecto es 11×11 (max_goals=10); `btts_prob`/`over_prob` recorren la matriz sin asumir tamaño.
- Pestañas "Equipos" y "Métricas" viejas se reemplazan; el backtest histórico se conserva dentro de "Verificación".
