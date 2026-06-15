import datetime
import math

import pytest

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel


def _m(home, away, hg, ag, *, neutral=True, d=1):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=neutral,
    )


def test_unseen_teams_predict_baseline_goals():
    cfg = PoissonConfig(baseline=math.log(1.3), home_adv=0.0)
    model = PoissonModel(cfg)
    pred = model.predict("A", "B", neutral=True)
    assert pred.xg_home == pytest.approx(1.3)
    assert pred.xg_away == pytest.approx(1.3)


def test_predict_returns_valid_distribution_and_matrix():
    model = PoissonModel()
    pred = model.predict("A", "B")
    assert pred.p_home + pred.p_draw + pred.p_away == pytest.approx(1.0)
    assert pred.xg_home is not None and pred.xg_away is not None
    assert pred.score_matrix is not None
    assert pred.score_matrix.shape == (model.config.max_goals + 1, model.config.max_goals + 1)


def test_observing_goals_raises_attack():
    model = PoissonModel()
    base_xg = model.predict("A", "B", neutral=True).xg_home
    for d in range(1, 8):
        model.observe(_m("A", "B", 4, 0, neutral=True, d=d))
    new_xg = model.predict("A", "B", neutral=True).xg_home
    assert new_xg > base_xg


def test_strong_attacker_more_likely_to_win():
    model = PoissonModel()
    for d in range(1, 8):
        model.observe(_m("A", "B", 4, 0, neutral=True, d=d))
    pred = model.predict("A", "B", neutral=True)
    assert pred.p_home > pred.p_away


def test_reset_clears_strengths():
    model = PoissonModel()
    model.observe(_m("A", "B", 3, 0))
    model.reset()
    assert model.attack == {} and model.defense == {}
