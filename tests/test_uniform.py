import pytest

from oraculo.models.uniform import UniformPredictor


def test_name():
    assert UniformPredictor().name == "uniform"


def test_returns_thirds():
    pred = UniformPredictor().predict("Argentina", "Francia")
    assert pred.p_home == pytest.approx(1 / 3)
    assert pred.p_draw == pytest.approx(1 / 3)
    assert pred.p_away == pytest.approx(1 / 3)


def test_ignores_teams():
    a = UniformPredictor().predict("Brasil", "San Marino").probs
    b = UniformPredictor().predict("San Marino", "Brasil").probs
    assert a == b
