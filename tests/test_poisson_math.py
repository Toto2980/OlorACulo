import math

import pytest

from oraculo.ratings.poisson import poisson_pmf, dc_tau, expected_goals


def test_poisson_pmf_known_values():
    assert poisson_pmf(0, 1.0) == pytest.approx(math.exp(-1.0))
    assert poisson_pmf(1, 2.0) == pytest.approx(math.exp(-2.0) * 2.0)
    assert poisson_pmf(2, 1.5) == pytest.approx(math.exp(-1.5) * 1.5 ** 2 / 2)


def test_dc_tau_corrections():
    lh, la, rho = 1.5, 1.2, -0.1
    assert dc_tau(0, 0, lh, la, rho) == pytest.approx(1 - lh * la * rho)
    assert dc_tau(0, 1, lh, la, rho) == pytest.approx(1 + lh * rho)
    assert dc_tau(1, 0, lh, la, rho) == pytest.approx(1 + la * rho)
    assert dc_tau(1, 1, lh, la, rho) == pytest.approx(1 - rho)


def test_dc_tau_identity_elsewhere():
    assert dc_tau(2, 3, 1.5, 1.2, -0.1) == 1.0
    assert dc_tau(0, 2, 1.5, 1.2, -0.1) == 1.0


def test_expected_goals_neutral_baseline():
    base = math.log(1.3)
    lh, la = expected_goals(0.0, 0.0, 0.0, 0.0, baseline=base, home_adv=0.3, neutral=True)
    assert lh == pytest.approx(1.3)
    assert la == pytest.approx(1.3)


def test_expected_goals_home_advantage():
    base = math.log(1.3)
    lh, la = expected_goals(0.0, 0.0, 0.0, 0.0, baseline=base, home_adv=0.3, neutral=False)
    assert lh == pytest.approx(1.3 * math.exp(0.3))
    assert la == pytest.approx(1.3)


def test_expected_goals_attack_raises_lambda():
    base = math.log(1.3)
    lh, _ = expected_goals(0.5, 0.0, 0.0, 0.0, baseline=base, home_adv=0.0, neutral=True)
    assert lh == pytest.approx(1.3 * math.exp(0.5))
