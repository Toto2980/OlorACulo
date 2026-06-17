"""Formaciones del Mundial 2026 vía Fotmob (JSON interna, gratis, sin API key).
Endpoints no documentados:
  - lista por fecha:  https://www.fotmob.com/api/data/matches?date=YYYYMMDD
  - detalle:          https://www.fotmob.com/api/data/matchDetails?matchId={id}

`content.lineup.lineupType` == "standard" => XI confirmado; "predicted" => probable.
Trae además `content.weather` (temperatura/viento/lluvia) para el pilar de contexto.

Diseño defensivo: User-Agent de navegador, cache por partido, y ante cualquier
error/estructura inesperada -> None (la app degrada, nunca rompe). NO toca la
predicción Poisson: las formaciones solo enriquecen el texto."""
from __future__ import annotations

import datetime
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from oraculo.live.lineups import TeamLineup
from oraculo.live.names import apifootball_to_canonical

FOTMOB_BASE = "https://www.fotmob.com/api/data"
DEFAULT_CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass(frozen=True)
class FotmobLineups:
    home: TeamLineup
    away: TeamLineup
    confirmed: bool
    weather: Optional[dict] = None


def _team_lineup(side: dict) -> TeamLineup:
    name = apifootball_to_canonical(side.get("name") or side.get("teamName") or "")
    xi = [
        (str(p.get("shirtNumber") or "?"), p.get("name") or "?")
        for p in (side.get("starters") or [])
    ]
    return TeamLineup(team=name, formation=side.get("formation"), start_xi=xi)


def parse_fotmob_lineups(details_raw: dict) -> Optional[FotmobLineups]:
    """Parsea la respuesta de matchDetails. None si no hay lineup."""
    lu = (details_raw or {}).get("content", {}).get("lineup") or {}
    home, away = lu.get("homeTeam"), lu.get("awayTeam")
    if not home or not away:
        return None
    weather = (details_raw or {}).get("content", {}).get("weather")
    return FotmobLineups(
        home=_team_lineup(home),
        away=_team_lineup(away),
        confirmed=(lu.get("lineupType") == "standard"),
        weather=weather,
    )


def find_fotmob_match_id(matches_raw: dict, home_canon: str, away_canon: str) -> Optional[int]:
    """Busca el matchId de Fotmob de un cruce del Mundial por nombres canónicos."""
    want = {home_canon, away_canon}
    for league in (matches_raw or {}).get("leagues", []):
        if "World Cup" not in (league.get("name") or ""):
            continue
        for m in league.get("matches", []):
            h = apifootball_to_canonical((m.get("home") or {}).get("name", ""))
            a = apifootball_to_canonical((m.get("away") or {}).get("name", ""))
            if {h, a} == want:
                return m.get("id")
    return None


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (URLs fijas de Fotmob)
        return json.loads(resp.read().decode("utf-8"))


class FotmobClient:
    """Cliente Fotmob con cache local. Ante cualquier error -> None."""

    def __init__(self, *, cache_dir: Path = DEFAULT_CACHE, ttl_seconds: int = 300) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, name: str, url: str) -> Optional[dict]:
        path = self.cache_dir / f"fotmob_{name}.json"
        if path.exists() and (time.time() - path.stat().st_mtime) <= self.ttl_seconds:
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            data = _http_get_json(url)
        except Exception:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            return None
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def lineups_for(
        self, home_canon: str, away_canon: str, date: datetime.date
    ) -> Optional[FotmobLineups]:
        ymd = date.strftime("%Y%m%d")
        matches = self._get(f"matches_{ymd}", f"{FOTMOB_BASE}/matches?date={ymd}")
        if not matches:
            return None
        mid = find_fotmob_match_id(matches, home_canon, away_canon)
        if mid is None:
            return None
        details = self._get(f"match_{mid}", f"{FOTMOB_BASE}/matchDetails?matchId={mid}")
        if not details:
            return None
        return parse_fotmob_lineups(details)
