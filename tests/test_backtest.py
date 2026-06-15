import datetime

import pytest

from oraculo.match import Match
from oraculo.models.uniform import UniformPredictor
from oraculo.evaluate.backtest import backtest, EvalResult


def _m(d, hg, ag):
    return Match(
        date=datetime.date(2022, 1, d),
        home="A", away="B",
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=False,
    )


def test_empty_raises():
    with pytest.raises(ValueError):
        backtest(UniformPredictor(), [])


def test_uniform_over_two_home_wins():
    matches = [_m(1, 2, 0), _m(2, 3, 1)]  # ambos resultado "home"
    res = backtest(UniformPredictor(), matches)
    assert isinstance(res, EvalResult)
    assert res.n_matches == 2
    assert res.brier == pytest.approx(2 / 3)
    assert res.rps == pytest.approx(5 / 18)
    assert res.log_loss == pytest.approx(__import__("math").log(3))
