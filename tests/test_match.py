import datetime
from oraculo.match import Match


def _match(hg, ag):
    return Match(
        date=datetime.date(2022, 11, 20),
        home="A", away="B",
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=False,
    )


def test_outcome_home_win():
    assert _match(2, 0).outcome == "home"


def test_outcome_away_win():
    assert _match(0, 1).outcome == "away"


def test_outcome_draw():
    assert _match(1, 1).outcome == "draw"
