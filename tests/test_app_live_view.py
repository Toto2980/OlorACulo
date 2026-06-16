import datetime
import json
from pathlib import Path

from oraculo.live.fixtures import Fixture, parse_fixtures
from app.live_view import group_by_phase, upcoming_rows, finished_rows


def _fixture(fid, status, hg, ag):
    return Fixture(
        id=fid, stage="GROUP_STAGE", group="A", home="Argentina", away="Brazil",
        kickoff_utc=datetime.datetime(2026, 6, 16, tzinfo=datetime.timezone.utc),
        status=status, home_goals=hg, away_goals=ag,
    )

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
    # y los equipos por separado para mostrarlos traducidos
    assert all("home" in r and "away" in r for r in rows)


def test_finished_rows_only_finished():
    rows = finished_rows(_fixtures())
    assert [r["id"] for r in rows] == [1001]
    assert rows[0]["marcador"] == "2–0"


def test_finished_rows_excluye_finalizados_sin_marcador():
    """Un partido FINISHED/AWARDED sin goles no debe entrar (rompería el scoring)."""
    rows = finished_rows([
        _fixture(1, "FINISHED", 2, 1),
        _fixture(2, "FINISHED", None, None),
    ])
    assert [r["id"] for r in rows] == [1]
