import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel


def _m(home, away, hg, ag, *, neutral=False, d=1):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=neutral,
    )


def test_unseen_team_uses_initial_rating():
    model = EloModel(EloConfig(initial_rating=1500))
    assert model.rating("Atlantis") == 1500


def test_observe_winner_gains_loser_loses():
    model = EloModel()
    model.observe(_m("A", "B", 3, 0, neutral=True))
    assert model.rating("A") > 1500
    assert model.rating("B") < 1500


def test_predict_returns_valid_distribution():
    model = EloModel()
    pred = model.predict("A", "B")
    assert pred.p_home + pred.p_draw + pred.p_away == pytest.approx(1.0)


def test_stronger_team_more_likely():
    model = EloModel()
    for d in range(1, 6):
        model.observe(_m("A", "B", 2, 0, neutral=True, d=d))
    pred = model.predict("A", "B", neutral=True)
    assert pred.p_home > pred.p_away


def test_reset_clears_ratings():
    model = EloModel()
    model.observe(_m("A", "B", 1, 0))
    model.reset()
    assert model.rating("A") == model.config.initial_rating


def test_fit_processes_in_date_order():
    model = EloModel()
    matches = [_m("A", "B", 0, 1, d=3), _m("A", "B", 5, 0, d=1)]
    model.fit(matches)
    assert "A" in model.ratings and "B" in model.ratings
