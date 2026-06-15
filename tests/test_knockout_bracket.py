import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.knockout import simulate_knockout


class _StrengthModel:
    """El equipo con índice más bajo (T0 < T1 < ...) es más fuerte y siempre gana."""

    def _strength(self, team):
        return 100 - int(team[1:])  # T0 fuerte, T31 débil

    def predict(self, home, away, *, neutral=False, on_date=None):
        sh, sa = self._strength(home), self._strength(away)
        m = np.zeros((11, 11))
        if sh >= sa:
            m[3, 0] = 1.0
        else:
            m[0, 3] = 1.0
        ph, pd, pa = outcome_probs(m)
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=m)


def _bracket_32():
    teams = [f"T{i}" for i in range(32)]
    return [(teams[i], teams[i + 1]) for i in range(0, 32, 2)]


def test_round_sizes():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    assert len(rounds["R32"]) == 32
    assert len(rounds["R16"]) == 16
    assert len(rounds["QF"]) == 8
    assert len(rounds["SF"]) == 4
    assert len(rounds["Final"]) == 2
    assert len(rounds["Champion"]) == 1


def test_strongest_team_wins():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    assert rounds["Champion"] == ["T0"]


def test_champion_reached_every_round():
    rounds = simulate_knockout(_StrengthModel(), _bracket_32(), np.random.default_rng(0))
    champ = rounds["Champion"][0]
    for r in ("R32", "R16", "QF", "SF", "Final"):
        assert champ in rounds[r]
