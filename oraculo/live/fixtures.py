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
    referee: Optional[str] = None
    referee_country: Optional[str] = None

    @property
    def is_finished(self) -> bool:
        return self.status == "FINISHED"

    @property
    def has_score(self) -> bool:
        """Finalizado Y con marcador numérico. La API puede dar un partido
        FINISHED/AWARDED con fullTime null; en ese caso no hay marcador que puntuar."""
        return self.is_finished and self.home_goals is not None and self.away_goals is not None

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


def _referee(raw: list | None) -> tuple[Optional[str], Optional[str]]:
    """Del array `referees` toma el árbitro principal (type REFEREE) o el primero."""
    refs = raw or []
    if not refs:
        return None, None
    main = next((r for r in refs if r.get("type") == "REFEREE"), refs[0])
    return main.get("name"), main.get("nationality")


def parse_fixtures(raw: dict) -> list[Fixture]:
    out: list[Fixture] = []
    for m in raw.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        ref_name, ref_country = _referee(m.get("referees"))
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
                referee=ref_name,
                referee_country=ref_country,
            )
        )
    return out
