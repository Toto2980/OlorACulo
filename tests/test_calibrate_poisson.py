import datetime

import pytest

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.walk_forward import walk_forward
from oraculo.calibrate.poisson import calibrate_poisson, PoissonCalibrationResult


def _m(home, away, hg, ag, d):
    return Match(
        date=datetime.date(2020, 1, d),
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        tournament="Friendly", neutral=True,
    )


def _matches():
    return [_m("A", "B", 3, 0, d) for d in range(1, 13)]


def test_returns_result():
    res = calibrate_poisson(
        _matches(),
        lr_values=[0.05],
        baseline_values=[0.26],
        home_adv_values=[0.0],
        rho_values=[-0.05],
    )
    assert isinstance(res, PoissonCalibrationResult)
    assert isinstance(res.config, PoissonConfig)


def test_picks_lowest_rps():
    matches = _matches()
    lr_grid = [0.02, 0.08, 0.2]
    res = calibrate_poisson(
        matches,
        lr_values=lr_grid,
        baseline_values=[0.26],
        home_adv_values=[0.0],
        rho_values=[-0.05],
    )
    expected = walk_forward(PoissonModel(res.config), matches)
    assert res.rps == pytest.approx(expected.rps)
    best_manual = min(
        walk_forward(
            PoissonModel(PoissonConfig(lr=lr, baseline=0.26, home_adv=0.0, rho=-0.05)),
            matches,
        ).rps
        for lr in lr_grid
    )
    assert res.rps == pytest.approx(best_manual)


def test_empty_grid_raises():
    with pytest.raises(ValueError):
        calibrate_poisson(
            _matches(),
            lr_values=[],
            baseline_values=[0.26],
            home_adv_values=[0.0],
            rho_values=[-0.05],
        )
