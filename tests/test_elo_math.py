import pytest

from oraculo.ratings.elo import expected_score, goal_multiplier, update_ratings


def test_expected_score_even():
    assert expected_score(0.0) == pytest.approx(0.5)


def test_expected_score_400_diff():
    assert expected_score(400.0) == pytest.approx(1 / 1.1)


def test_goal_multiplier():
    assert goal_multiplier(0) == 1.0
    assert goal_multiplier(1) == 1.0
    assert goal_multiplier(-1) == 1.0
    assert goal_multiplier(2) == 1.5
    assert goal_multiplier(3) == pytest.approx(14 / 8)
    assert goal_multiplier(4) == pytest.approx(15 / 8)


def test_update_even_draw_no_change():
    new_h, new_a = update_ratings(1500, 1500, 1, 1, k=20, home_adv=65, neutral=True)
    assert new_h == pytest.approx(1500)
    assert new_a == pytest.approx(1500)


def test_update_zero_sum():
    new_h, new_a = update_ratings(1500, 1500, 2, 0, k=20, home_adv=0, neutral=True)
    assert (new_h - 1500) == pytest.approx(-(new_a - 1500))


def test_update_upset_moves_more_than_expected_win():
    fav_win_h, _ = update_ratings(1800, 1500, 1, 0, k=20, home_adv=0, neutral=True)
    upset_h, _ = update_ratings(1800, 1500, 0, 1, k=20, home_adv=0, neutral=True)
    assert abs(upset_h - 1800) > abs(fav_win_h - 1800)
