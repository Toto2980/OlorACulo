import numpy as np

from oraculo.models.base import MatchPrediction
from oraculo.ratings.poisson import outcome_probs
from oraculo.tournament.config import WorldCupConfig
from oraculo.tournament.groupstage import simulate_group_stage, GroupStageResult


class _StrengthModel:
    """Modelo falso: cada equipo tiene una 'fuerza' (goles esperados). Marcador =
    matriz concentrada en (round(lh), round(la))."""

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
    groups = {}
    for gi in range(12):
        letter = chr(ord("A") + gi)
        groups[letter] = names[gi * 4:(gi + 1) * 4]
    return WorldCupConfig(seed=1, groups=groups)


def test_returns_result_with_standings_and_advancing():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    assert isinstance(res, GroupStageResult)
    assert len(res.standings) == 12
    assert all(len(v) == 4 for v in res.standings.values())


def test_advancing_count_is_24_plus_8():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    assert len(res.advancing) == 32


def test_top_two_always_advance():
    strength = {f"T{i}": 4 - (i % 4) for i in range(48)}
    model = _StrengthModel(strength)
    res = simulate_group_stage(model, _config(), np.random.default_rng(1))
    for ranked in res.standings.values():
        assert ranked[0].team in res.advancing
        assert ranked[1].team in res.advancing
