import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloModel
from oraculo.evaluate.backtest import EvalResult
from oraculo.evaluate.walk_forward import walk_forward


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def test_returns_eval_result():
    matches = [_m("A", "B", 1, 0, 1), _m("A", "B", 2, 1, 2)]
    res = walk_forward(EloModel(), matches)
    assert isinstance(res, EvalResult)
    assert res.n_matches == 2


def test_eval_from_filters_warmup():
    matches = [
        _m("A", "B", 1, 0, 1),
        _m("A", "B", 1, 0, 2),
        _m("A", "B", 1, 0, 3),
    ]
    res = walk_forward(EloModel(), matches, eval_from=datetime.date(2020, 1, 2))
    assert res.n_matches == 2


def test_empty_eval_window_raises():
    matches = [_m("A", "B", 1, 0, 1)]
    with pytest.raises(ValueError):
        walk_forward(EloModel(), matches, eval_from=datetime.date(2021, 1, 1))


def test_predicts_before_observing():
    matches = [_m("A", "B", 5, 0, 1)]
    res = walk_forward(EloModel(), matches)
    assert res.rps > 0
