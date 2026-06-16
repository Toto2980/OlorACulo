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
