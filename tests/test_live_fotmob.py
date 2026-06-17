import datetime

from oraculo.live.fotmob import (
    parse_fotmob_lineups,
    find_fotmob_match_id,
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
                    {"name": "Emiliano Martínez", "shirtNumber": 23},
                    {"name": "Lionel Messi", "shirtNumber": 10},
                ],
            },
            "awayTeam": {
                "name": "Algeria",
                "formation": "4-2-3-1",
                "starters": [{"name": "Oukidja", "shirtNumber": 16}],
            },
        },
        "weather": {"temperature": 23, "windSpeed": 3, "precipitation": 0, "relativeHumidity": 63},
    }
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
