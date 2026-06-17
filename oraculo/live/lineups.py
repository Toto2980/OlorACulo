"""Formaciones/alineaciones desde API-Football (api-sports.io). Fuente gratis
(100 req/día) con XI + dibujo (`fixtures/lineups`). Las formaciones oficiales
entran ~T-30 antes del partido.

Diseño defensivo: sin API key, sin match o ante cualquier error -> devuelve None
(nunca rompe la app). NO altera la predicción Poisson; solo enriquece el texto."""
from __future__ import annotations

import datetime
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from oraculo.live.names import apifootball_to_canonical

BASE_URL = "https://v3.football.api-sports.io"
WC_LEAGUE = 1
WC_SEASON = 2026
DEFAULT_CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "cache"


@dataclass(frozen=True)
class TeamLineup:
    team: str                       # canónico
    formation: Optional[str]
    start_xi: list[tuple[str, str]]  # [(posición, nombre)]


def parse_lineups(raw: dict) -> dict[str, TeamLineup]:
    """raw = respuesta de /fixtures/lineups. Devuelve {equipo_canónico: TeamLineup}."""
    out: dict[str, TeamLineup] = {}
    for entry in (raw or {}).get("response", []):
        name = apifootball_to_canonical((entry.get("team") or {}).get("name", ""))
        xi = [
            (p.get("player", {}).get("pos") or "?", p.get("player", {}).get("name") or "?")
            for p in (entry.get("startXI") or [])
        ]
        out[name] = TeamLineup(team=name, formation=entry.get("formation"), start_xi=xi)
    return out


def find_fixture_id(
    fixtures_raw: dict, home_canon: str, away_canon: str, date: datetime.date
) -> Optional[int]:
    """Resuelve el fixture id de API-Football por nombres canónicos + fecha."""
    for entry in (fixtures_raw or {}).get("response", []):
        teams = entry.get("teams") or {}
        h = apifootball_to_canonical((teams.get("home") or {}).get("name", ""))
        a = apifootball_to_canonical((teams.get("away") or {}).get("name", ""))
        raw_date = (entry.get("fixture") or {}).get("date", "")
        try:
            d = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if d == date and {h, a} == {home_canon, away_canon}:
            return (entry.get("fixture") or {}).get("id")
    return None


def _http_get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"x-apisports-key": token})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (URL fija de la API)
        return json.loads(resp.read().decode("utf-8"))


class LineupClient:
    """Cliente API-Football con cache local. Sin token o ante error -> None."""

    def __init__(
        self,
        token: Optional[str],
        *,
        cache_dir: Path = DEFAULT_CACHE,
        ttl_seconds: int = 600,
    ) -> None:
        self.token = token
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, name: str) -> Path:
        return self.cache_dir / f"apifootball_{name}.json"

    def _get(self, name: str, url: str, *, ttl: int) -> Optional[dict]:
        path = self._cache_path(name)
        if path.exists() and (time.time() - path.stat().st_mtime) <= ttl:
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            data = _http_get_json(url, self.token)  # type: ignore[arg-type]
        except Exception:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            return None
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def lineups_for(
        self, home_canon: str, away_canon: str, date: datetime.date
    ) -> Optional[tuple[TeamLineup, TeamLineup]]:
        """(lineup_home, lineup_away) o None si no hay key/datos."""
        if not self.token:
            return None
        fixtures = self._get(
            "fixtures_wc", f"{BASE_URL}/fixtures?league={WC_LEAGUE}&season={WC_SEASON}", ttl=86400
        )
        if not fixtures:
            return None
        fid = find_fixture_id(fixtures, home_canon, away_canon, date)
        if fid is None:
            return None
        raw = self._get(f"lineups_{fid}", f"{BASE_URL}/fixtures/lineups?fixture={fid}", ttl=self.ttl_seconds)
        if not raw:
            return None
        parsed = parse_lineups(raw)
        home_lu, away_lu = parsed.get(home_canon), parsed.get(away_canon)
        if home_lu is None or away_lu is None:
            return None
        return home_lu, away_lu
