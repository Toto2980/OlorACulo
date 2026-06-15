import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.group import TeamRecord
from oraculo.tournament.groupstage import simulate_group_stage


class _StrengthModel:
    def __init__(self, strength):
        self.strength = strength

    def predict(self, home, away, *, neutral=False, on_date=None):
        lh = self.strength.get(home, 1.0)
        la = self.strength.get(away, 1.0)
        m = np.zeros((11, 11))
        m[int(round(lh)), int(round(la))] = 1.0
        ph, pd, pa = outcome_probs(m)
        return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, score_matrix=m)


def _config():
    names = [f"T{i}" for i in range(48)]
    groups = {chr(ord("A") + gi): names[gi * 4:(gi + 1) * 4] for gi in range(12)}
    return WorldCupConfig(seed=1, groups=groups)


def test_best_thirds_has_eight_ranked_records():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    res = simulate_group_stage(_StrengthModel(strength), _config(), np.random.default_rng(1))
    assert len(res.best_thirds) == 8
    assert all(isinstance(r, TeamRecord) for r in res.best_thirds)


def test_best_thirds_all_advance_and_are_subset_of_advancing():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    res = simulate_group_stage(_StrengthModel(strength), _config(), np.random.default_rng(1))
    assert {r.team for r in res.best_thirds} <= res.advancing
