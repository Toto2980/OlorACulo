import datetime

import pytest

from oraculo.match import Match
from oraculo.models.elo import EloConfig, EloModel
from oraculo.evaluate.walk_forward import walk_forward
from oraculo.calibrate.elo import calibrate_elo, CalibrationResult


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def _matches():
    return [_m("A", "B", 2, 0, d) for d in range(1, 11)]


def test_returns_calibration_result():
    res = calibrate_elo(
        _matches(),
        k_values=[20.0],
        home_adv_values=[0.0],
        nu_values=[0.6],
    )
    assert isinstance(res, CalibrationResult)
    assert isinstance(res.config, EloConfig)


def test_picks_grid_point_with_lowest_rps():
    matches = _matches()
    grid_nu = [0.0, 0.6, 2.0]
    res = calibrate_elo(
        matches,
        k_values=[20.0],
        home_adv_values=[0.0],
        nu_values=grid_nu,
    )
    expected = walk_forward(EloModel(res.config), matches)
    assert res.rps == pytest.approx(expected.rps)
    best_manual = min(
        walk_forward(EloModel(EloConfig(k=20.0, home_adv=0.0, nu=nu)), matches).rps
        for nu in grid_nu
    )
    assert res.rps == pytest.approx(best_manual)


def test_empty_grid_raises():
    with pytest.raises(ValueError):
        calibrate_elo(_matches(), k_values=[], home_adv_values=[0.0], nu_values=[0.6])
