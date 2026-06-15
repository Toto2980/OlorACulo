import numpy as np
import pytest

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.montecarlo import run_group_stage_mc


class _FakeModel:
    """Marcador siempre 1-1 -> todo se define por azar sembrado."""

    def __init__(self):
        self.matrix = np.zeros((11, 11))
        self.matrix[1, 1] = 1.0
        self._probs = outcome_probs(self.matrix)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def _config():
    groups = {chr(ord("A") + gi): [f"T{gi}_{k}" for k in range(4)] for gi in range(12)}
    return WorldCupConfig(seed=2026, groups=groups)


def test_position_probabilities_sum_to_one_per_team():
    res = run_group_stage_mc(_FakeModel(), _config(), n_iter=200)
    for team, probs in res.items():
        total = probs["1st"] + probs["2nd"] + probs["3rd"] + probs["4th"]
        assert total == pytest.approx(1.0)


def test_advance_probability_in_range():
    res = run_group_stage_mc(_FakeModel(), _config(), n_iter=200)
    for probs in res.values():
        assert 0.0 <= probs["advance"] <= 1.0


def test_deterministic_with_seed():
    a = run_group_stage_mc(_FakeModel(), _config(), n_iter=100)
    b = run_group_stage_mc(_FakeModel(), _config(), n_iter=100)
    assert a == b
