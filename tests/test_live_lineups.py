import datetime

from oraculo.live.lineups import (
    TeamLineup,
    parse_lineups,
    find_fixture_id,
    LineupClient,
)


_LINEUPS_RAW = {
    "response": [
        {
            "team": {"id": 26, "name": "Argentina"},
            "formation": "4-3-3",
            "startXI": [
                {"player": {"name": "E. Martínez", "pos": "G"}},
                {"player": {"name": "N. Molina", "pos": "D"}},
                {"player": {"name": "L. Messi", "pos": "F"}},
            ],
        },
        {
            "team": {"id": 6, "name": "Brazil"},
            "formation": "4-2-3-1",
            "startXI": [
                {"player": {"name": "Alisson", "pos": "G"}},
                {"player": {"name": "Vinicius Jr", "pos": "F"}},
            ],
        },
    ]
}

_FIXTURES_RAW = {
    "response": [
        {
            "fixture": {"id": 111, "date": "2026-06-20T19:00:00+00:00"},
            "teams": {"home": {"name": "Argentina"}, "away": {"name": "Brazil"}},
        },
        {
            "fixture": {"id": 222, "date": "2026-06-21T16:00:00+00:00"},
            "teams": {"home": {"name": "USA"}, "away": {"name": "Korea Republic"}},
        },
    ]
}


def test_parse_lineups_devuelve_formacion_y_xi_por_equipo_canonico():
    out = parse_lineups(_LINEUPS_RAW)
    assert set(out) == {"Argentina", "Brazil"}
    arg = out["Argentina"]
    assert isinstance(arg, TeamLineup)
    assert arg.formation == "4-3-3"
    assert ("G", "E. Martínez") in arg.start_xi
    assert len(arg.start_xi) == 3


def test_find_fixture_id_mapea_por_nombre_canonico_y_fecha():
    # USA/Korea Republic deben mapearse a canónico
    fid = find_fixture_id(_FIXTURES_RAW, "United States", "South Korea", datetime.date(2026, 6, 21))
    assert fid == 222
    fid2 = find_fixture_id(_FIXTURES_RAW, "Argentina", "Brazil", datetime.date(2026, 6, 20))
    assert fid2 == 111


def test_find_fixture_id_sin_match_es_none():
    assert find_fixture_id(_FIXTURES_RAW, "Spain", "France", datetime.date(2026, 6, 20)) is None


def test_lineup_client_sin_token_no_rompe_y_devuelve_none(tmp_path):
    client = LineupClient(None, cache_dir=tmp_path)
    res = client.lineups_for("Argentina", "Brazil", datetime.date(2026, 6, 20))
    assert res is None


def test_parse_lineups_respuesta_vacia_es_dict_vacio():
    assert parse_lineups({"response": []}) == {}
