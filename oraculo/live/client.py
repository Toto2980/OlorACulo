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
