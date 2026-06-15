import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.tournament.knockout import knockout_winner


class _FixedScore:
    """Devuelve siempre un marcador concentrado (hg, ag) y probs coherentes."""

    def __init__(self, hg, ag):
        self.m = np.zeros((11, 11))
        self.m[hg, ag] = 1.0
        from oraculo.ratings.poisson import outcome_probs
        self._p = outcome_probs(self.m)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def test_home_win_returns_home():
    assert knockout_winner(_FixedScore(2, 0), "A", "B", np.random.default_rng(0)) == "A"


def test_away_win_returns_away():
    assert knockout_winner(_FixedScore(0, 3), "A", "B", np.random.default_rng(0)) == "B"


class _DrawThenStrength:
    """Marcador siempre 1-1 (empate), pero con probs 1-X-2 asimétricas para penales."""

    def __init__(self, p_home, p_draw, p_away):
        self.m = np.zeros((11, 11))
        self.m[1, 1] = 1.0
        self._p = (p_home, p_draw, p_away)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._p
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.m)


def test_draw_resolves_by_weighted_penalties_favoring_stronger():
    model = _DrawThenStrength(0.8, 0.15, 0.05)
    wins_a = sum(
        knockout_winner(model, "A", "B", np.random.default_rng(s)) == "A"
        for s in range(200)
    )
    assert wins_a > 150
