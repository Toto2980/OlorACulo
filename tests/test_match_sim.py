import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.group import sample_scoreline, simulate_match


def _matrix_concentrated(i, j, n=11):
    m = np.zeros((n, n))
    m[i, j] = 1.0
    return m


def test_sample_scoreline_picks_only_nonzero_cell():
    rng = np.random.default_rng(0)
    m = _matrix_concentrated(2, 3)
    for _ in range(5):
        assert sample_scoreline(m, rng) == (2, 3)


class _FakeModel:
    def __init__(self, matrix):
        self.matrix = matrix
        ph, pd, pa = outcome_probs(matrix)
        self._probs = (ph, pd, pa)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def test_simulate_match_uses_model_matrix():
    rng = np.random.default_rng(0)
    model = _FakeModel(_matrix_concentrated(1, 0))
    assert simulate_match(model, "A", "B", rng, neutral=True) == (1, 0)
