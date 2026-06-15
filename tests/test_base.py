import pytest

from oraculo.models.base import MatchPrediction, OUTCOMES


def test_outcomes_order():
    assert OUTCOMES == ("home", "draw", "away")


def test_probs_tuple():
    pred = MatchPrediction(p_home=0.5, p_draw=0.3, p_away=0.2)
    assert pred.probs == (0.5, 0.3, 0.2)


def test_rejects_probs_not_summing_to_one():
    with pytest.raises(ValueError):
        MatchPrediction(p_home=0.5, p_draw=0.5, p_away=0.5)
