import datetime

import numpy as np

from oraculo.match import Match
from oraculo.evaluate.backtest import EvalResult
from app.services import top_scorelines, model_comparison


def test_top_scorelines_orders_by_probability():
    m = np.zeros((11, 11))
    m[2, 3] = 0.6
    m[1, 0] = 0.4
    top = top_scorelines(m, n=2)
    assert top[0] == ((2, 3), 0.6)
    assert top[1] == ((1, 0), 0.4)


def test_top_scorelines_length():
    m = np.full((11, 11), 1.0 / 121)
    assert len(top_scorelines(m, n=5)) == 5


def _matches():
    out = []
    day = 1
    for year in (2008, 2009, 2011, 2012):
        for _ in range(3):
            out.append(Match(
                date=datetime.date(year, 1, day),
                home="A", away="B", home_goals=2, away_goals=1,
                tournament="Friendly", neutral=True,
            ))
            day += 1
    return out


def test_model_comparison_returns_three_eval_results():
    res = model_comparison(_matches(), datetime.date(2010, 1, 1))
    assert set(res.keys()) == {"uniforme", "elo", "poisson"}
    for ev in res.values():
        assert isinstance(ev, EvalResult)
        assert ev.n_matches > 0
