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
