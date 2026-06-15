import pytest

from oraculo.ratings.poisson import score_matrix, outcome_probs


def test_matrix_sums_to_one():
    m = score_matrix(1.5, 1.2, rho=-0.05, max_goals=10)
    assert m.sum() == pytest.approx(1.0)


def test_matrix_shape():
    m = score_matrix(1.5, 1.2, rho=-0.05, max_goals=8)
    assert m.shape == (9, 9)


def test_outcome_probs_sum_to_one():
    m = score_matrix(1.7, 1.1, rho=-0.05, max_goals=10)
    p_home, p_draw, p_away = outcome_probs(m)
    assert p_home + p_draw + p_away == pytest.approx(1.0)


def test_equal_lambdas_symmetric_when_no_correction():
    m = score_matrix(1.4, 1.4, rho=0.0, max_goals=10)
    p_home, p_draw, p_away = outcome_probs(m)
    assert p_home == pytest.approx(p_away)
    assert p_draw > 0


def test_higher_home_lambda_favors_home():
    m = score_matrix(2.2, 0.8, rho=-0.05, max_goals=10)
    p_home, _, p_away = outcome_probs(m)
    assert p_home > p_away
