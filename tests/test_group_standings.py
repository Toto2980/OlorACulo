import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.group import compute_standings, rank_group, simulate_group


def test_standings_points_and_goals():
    teams = ["A", "B", "C", "D"]
    results = [
        ("A", "B", 2, 0),  # A gana
        ("A", "C", 1, 1),  # empate
        ("A", "D", 3, 0),  # A gana
        ("B", "C", 0, 0),
        ("B", "D", 1, 0),
        ("C", "D", 2, 2),
    ]
    table = compute_standings(teams, results)
    assert table["A"].points == 7      # 2 victorias + 1 empate
    assert table["A"].goals_for == 6
    assert table["A"].goals_against == 1
    assert table["A"].goal_diff == 5


def test_rank_orders_by_points_then_gd():
    teams = ["A", "B", "C", "D"]
    results = [
        ("A", "B", 1, 0),
        ("A", "C", 1, 0),
        ("A", "D", 1, 0),
        ("B", "C", 5, 0),  # B con mejor DG que C/D
        ("B", "D", 0, 0),
        ("C", "D", 0, 0),
    ]
    table = compute_standings(teams, results)
    ranked = rank_group(table, np.random.default_rng(0))
    assert ranked[0].team == "A"   # 9 pts
    assert ranked[1].team == "B"   # 4 pts, +5 DG


class _FakeModel:
    def __init__(self, matrix):
        self.matrix = matrix
        self._probs = outcome_probs(matrix)

    def predict(self, home, away, *, neutral=False, on_date=None):
        ph, pd, pa = self._probs
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=self.matrix)


def test_simulate_group_returns_four_ranked_teams():
    m = np.zeros((11, 11))
    m[1, 1] = 1.0  # todos empatan 1-1 -> desempate por azar
    model = _FakeModel(m)
    ranked = simulate_group(model, ["A", "B", "C", "D"], np.random.default_rng(1))
    assert len(ranked) == 4
    assert {r.team for r in ranked} == {"A", "B", "C", "D"}
