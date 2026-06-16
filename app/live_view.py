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
