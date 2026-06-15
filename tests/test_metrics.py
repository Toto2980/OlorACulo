import math

import pytest

from oraculo.evaluate.metrics import brier_score, rps, log_loss

P = (0.5, 0.3, 0.2)


def test_brier_home():
    assert brier_score(P, "home") == pytest.approx(0.38)


def test_rps_home():
    assert rps(P, "home") == pytest.approx(0.145)


def test_log_loss_home():
    assert log_loss(P, "home") == pytest.approx(-math.log(0.5))


def test_uniform_metrics_home():
    u = (1 / 3, 1 / 3, 1 / 3)
    assert brier_score(u, "home") == pytest.approx(2 / 3)
    assert rps(u, "home") == pytest.approx(5 / 18)
    assert log_loss(u, "home") == pytest.approx(-math.log(1 / 3))


def test_rps_perfect_prediction_is_zero():
    assert rps((1.0, 0.0, 0.0), "home") == pytest.approx(0.0)
