import pytest

from oraculo.ratings.elo import davidson_probs


def test_sums_to_one():
    for dr in (-300.0, -50.0, 0.0, 75.0, 500.0):
        p_home, p_draw, p_away = davidson_probs(dr, nu=0.6)
        assert p_home + p_draw + p_away == pytest.approx(1.0)


def test_even_teams_symmetric():
    p_home, p_draw, p_away = davidson_probs(0.0, nu=0.6)
    assert p_home == pytest.approx(p_away)
    assert p_draw == pytest.approx(0.6 / 2.6)
    assert p_home == pytest.approx(1.0 / 2.6)


def test_nu_zero_means_no_draws():
    p_home, p_draw, p_away = davidson_probs(120.0, nu=0.0)
    assert p_draw == pytest.approx(0.0)
    assert p_home + p_away == pytest.approx(1.0)


def test_positive_diff_favors_home():
    p_home, _, p_away = davidson_probs(200.0, nu=0.6)
    assert p_home > p_away
