import datetime

from oraculo.live.fotmob import (
    parse_fotmob_lineups,
    find_fotmob_match_id,
    parse_player_profile,
    PlayerProfile,
    FotmobLineups,
    FotmobClient,
)


_DETAILS_CONFIRMED = {
    "content": {
        "lineup": {
            "lineupType": "standard",
            "homeTeam": {
                "name": "Argentina",
                "formation": "4-4-2",
                "starters": [
                    {"id": 268375, "name": "Emiliano Martínez", "shirtNumber": 23},
                    {"id": 19198, "name": "Lionel Messi", "shirtNumber": 10},
                ],
            },
            "awayTeam": {
                "name": "Algeria",
                "formation": "4-2-3-1",
                "starters": [{"id": 555, "name": "Oukidja", "shirtNumber": 16}],
            },
        },
        "weather": {"temperature": 23, "windSpeed": 3, "precipitation": 0, "relativeHumidity": 63},
    }
}


_PLAYER_OK = {
    "id": 268375,
    "name": "Emiliano Martínez",
    "primaryTeam": {"teamName": "Aston Villa"},
    "positionDescription": {"label": "Keeper"},
    "injuryInformation": None,
    "status": "active",
    "playerInformation": [{"title": "Age", "value": {"fallback": "33"}}],
    "mainLeague": {
        "leagueName": "Premier League",
        "season": "2025/2026",
        "stats": [{"title": "Rating", "value": 7.07}, {"title": "Matches", "value": 32}],
    },
}

_PLAYER_INJURED = {
    "id": 99,
    "name": "Lesionado",
    "primaryTeam": {"teamName": "Club X"},
    "positionDescription": {"label": "Forward"},
    "injuryInformation": {"injuryType": "Knee", "expectedReturn": "2026-07-01"},
    "status": "out",
    "playerInformation": [],
    "mainLeague": {"leagueName": "Liga", "season": "2025/2026", "stats": []},
}

_DETAILS_PREDICTED = {
    "content": {
        "lineup": {
            "lineupType": "predicted",
            "homeTeam": {"name": "England", "formation": "4-2-3-1", "starters": []},
            "awayTeam": {"name": "Croatia", "formation": "4-3-3", "starters": []},
        }
    }
}

_MATCHES = {
    "leagues": [
        {
            "id": 894799,
            "name": "World Cup Grp. J",
            "matches": [{"id": 4667812, "home": {"name": "Argentina"}, "away": {"name": "Algeria"}}],
        },
        {
            "id": 47,
            "name": "Premier League",
            "matches": [{"id": 999, "home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}}],
        },
    ]
}


def test_parse_lineups_confirmadas_con_formacion_xi_y_clima():
    res = parse_fotmob_lineups(_DETAILS_CONFIRMED)
    assert isinstance(res, FotmobLineups)
    assert res.confirmed is True
    assert res.home.team == "Argentina" and res.home.formation == "4-4-2"
    assert ("23", "Emiliano Martínez") in res.home.start_xi
    assert res.away.formation == "4-2-3-1"
    assert res.weather["temperature"] == 23


def test_parse_lineups_predichas_marca_confirmed_false():
    res = parse_fotmob_lineups(_DETAILS_PREDICTED)
    assert res is not None
    assert res.confirmed is False
    assert res.home.formation == "4-2-3-1"


def test_parse_lineups_sin_lineup_es_none():
    assert parse_fotmob_lineups({"content": {}}) is None


def test_find_match_id_solo_considera_ligas_del_mundial():
    assert find_fotmob_match_id(_MATCHES, "Argentina", "Algeria") == 4667812
    # Arsenal/Chelsea no es World Cup -> no match
    assert find_fotmob_match_id(_MATCHES, "Arsenal", "Chelsea") is None


def test_find_match_id_sin_match_es_none():
    assert find_fotmob_match_id(_MATCHES, "Spain", "France") is None


def test_client_degrada_a_none_si_no_encuentra_el_partido(monkeypatch, tmp_path):
    client = FotmobClient(cache_dir=tmp_path)
    # forzamos que la lista de partidos no traiga el cruce
    monkeypatch.setattr(client, "_get", lambda name, url: _MATCHES)
    assert client.lineups_for("Spain", "France", datetime.date(2026, 6, 17)) is None


def test_lineups_exponen_player_ids_para_encadenar_con_la_ficha():
    res = parse_fotmob_lineups(_DETAILS_CONFIRMED)
    assert res.player_ids["Lionel Messi"] == 19198
    assert res.player_ids["Emiliano Martínez"] == 268375


def test_parse_banco_desde_subs():
    raw = {
        "content": {
            "lineup": {
                "lineupType": "standard",
                "homeTeam": {
                    "name": "Argentina", "formation": "4-3-3",
                    "starters": [{"id": 1, "name": "A", "shirtNumber": 1}],
                    "subs": [{"id": 50, "name": "Suplente", "shirtNumber": 12}],
                },
                "awayTeam": {"name": "Brazil", "formation": "4-4-2", "starters": [], "subs": []},
            }
        }
    }
    res = parse_fotmob_lineups(raw)
    assert res.home.bench == (("12", "Suplente"),)
    assert res.player_ids["Suplente"] == 50  # los suplentes también encadenan a su ficha


def test_parse_player_profile_sano():
    p = parse_player_profile(_PLAYER_OK)
    assert isinstance(p, PlayerProfile)
    assert p.name == "Emiliano Martínez"
    assert p.team == "Aston Villa"
    assert p.position == "Keeper"
    assert p.age == "33"
    assert p.injured is False
    assert p.stats.get("Rating") == 7.07
    assert "Premier League" in (p.league or "")


def test_parse_player_profile_lesionado():
    p = parse_player_profile(_PLAYER_INJURED)
    assert p.injured is True
    assert "Knee" in (p.injury_note or "")


def test_parse_player_profile_vacio_es_none():
    assert parse_player_profile({}) is None


def test_client_player_profile_degrada_a_none(monkeypatch, tmp_path):
    client = FotmobClient(cache_dir=tmp_path)
    monkeypatch.setattr(client, "_get", lambda name, url: None)
    assert client.player_profile(123) is None
