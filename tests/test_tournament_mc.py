import numpy as np
import pytest

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.tournament import simulate_tournament, run_tournament_mc


class _FakeModel:
    """Marcador 1-1 siempre -> todo se define por azar sembrado (grupos y penales)."""

    def __init__(self):
        self.m = np.zeros((11, 11))
        self.m[1, 1] = 1.0
        self._p = outcome_probs(self.m)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def _config():
    names = [f"T{i}" for i in range(48)]
    groups = {chr(ord("A") + gi): names[gi * 4:(gi + 1) * 4] for gi in range(12)}
    return WorldCupConfig(seed=2026, groups=groups)


def test_simulate_tournament_has_one_champion():
    rounds = simulate_tournament(_FakeModel(), _config(), np.random.default_rng(3))
    assert len(rounds["Champion"]) == 1
    assert len(rounds["R32"]) == 32


def test_mc_champion_probs_sum_to_one():
    probs = run_tournament_mc(_FakeModel(), _config(), n_iter=300)
    total = sum(p["Champion"] for p in probs.values())
    assert total == pytest.approx(1.0)


def test_mc_round_probabilities_monotonic():
    probs = run_tournament_mc(_FakeModel(), _config(), n_iter=300)
    for p in probs.values():
        assert p["R32"] >= p["R16"] >= p["QF"] >= p["SF"] >= p["Final"] >= p["Champion"]


def test_mc_deterministic_with_seed():
    a = run_tournament_mc(_FakeModel(), _config(), n_iter=100)
    b = run_tournament_mc(_FakeModel(), _config(), n_iter=100)
    assert a == b
