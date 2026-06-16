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
