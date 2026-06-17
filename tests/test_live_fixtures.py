import datetime
import json
from pathlib import Path

from oraculo.live.fixtures import Fixture, parse_fixtures, phase_label, normalize_status

SAMPLE = Path(__file__).parent / "fixtures" / "wc_matches_sample.json"


def _raw():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_parse_returns_fixture_per_match():
    fixtures = parse_fixtures(_raw())
    assert len(fixtures) == 4
    assert all(isinstance(f, Fixture) for f in fixtures)


def test_parse_finished_match_has_score_and_outcome():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 1001)
    assert f.home == "Mexico"
    assert f.away == "South Africa"
    assert f.status == "FINISHED"
    assert f.is_finished
    assert (f.home_goals, f.away_goals) == (2, 0)
    assert f.kickoff_utc == datetime.datetime(2026, 6, 11, 19, 0, tzinfo=datetime.timezone.utc)


def test_parse_canonicalizes_names_and_normalizes_status():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 1002)
    # "Czechia" (API) -> "Czech Republic" (canónico del dataset)
    assert f.away == "Czech Republic"
    assert f.home == "South Korea"   # la API ya usa este nombre
    assert f.group == "A"
    assert f.status == "SCHEDULED"   # normalizado desde "TIMED"
    assert f.home_goals is None


def test_parse_unresolved_teams_become_none():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 1003)
    assert f.home is None and f.away is None
    assert f.stage == "LAST_32"
    assert not f.resolved


def test_parse_referee_desde_el_payload():
    raw = {
        "matches": [
            {
                "id": 9100,
                "stage": "GROUP_STAGE",
                "group": "GROUP_A",
                "homeTeam": {"name": "Argentina"},
                "awayTeam": {"name": "Brazil"},
                "utcDate": "2026-06-20T19:00:00Z",
                "status": "TIMED",
                "score": {"fullTime": {"home": None, "away": None}},
                "referees": [
                    {"name": "Wilton Sampaio", "type": "REFEREE", "nationality": "Brazil"},
                    {"name": "Otro", "type": "ASSISTANT_REFEREE_N1", "nationality": "Brazil"},
                ],
            }
        ]
    }
    f = parse_fixtures(raw)[0]
    assert f.referee == "Wilton Sampaio"
    assert f.referee_country == "Brazil"


def test_parse_referee_ausente_es_none():
    raw = {
        "matches": [
            {
                "id": 9101,
                "stage": "GROUP_STAGE",
                "homeTeam": {"name": "Argentina"},
                "awayTeam": {"name": "Brazil"},
                "utcDate": "2026-06-20T19:00:00Z",
                "status": "TIMED",
                "score": {"fullTime": {"home": None, "away": None}},
                "referees": [],
            }
        ]
    }
    f = parse_fixtures(raw)[0]
    assert f.referee is None and f.referee_country is None


def test_has_score_true_para_finalizado_con_goles():
    f = next(f for f in parse_fixtures(_raw()) if f.id == 1001)
    assert f.is_finished and f.has_score


def test_has_score_false_para_finalizado_sin_marcador():
    """AWARDED o un FINISHED con fullTime null: is_finished True pero sin goles."""
    raw = {
        "matches": [
            {
                "id": 9001,
                "stage": "GROUP_STAGE",
                "group": "GROUP_A",
                "homeTeam": {"name": "Mexico"},
                "awayTeam": {"name": "Canada"},
                "utcDate": "2026-06-12T19:00:00Z",
                "status": "AWARDED",
                "score": {"fullTime": {"home": None, "away": None}},
            }
        ]
    }
    f = parse_fixtures(raw)[0]
    assert f.is_finished           # AWARDED -> FINISHED
    assert f.home_goals is None
    assert not f.has_score


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
