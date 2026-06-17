import numpy as np

from oraculo.models.base import MatchPrediction
from app.postmatch import postmatch_report, PostMatch


def _pred(ph, pd, pa, top_cell):
    m = np.zeros((11, 11))
    m[top_cell] = 0.5
    m[0, 0] = 0.3
    m[2, 2] = 0.2
    return MatchPrediction(p_home=ph, p_draw=pd, p_away=pa, xg_home=1.7, xg_away=0.6, score_matrix=m)


def test_postmatch_acierto_con_marcador_en_top():
    pred = _pred(0.60, 0.25, 0.15, (2, 0))
    r = postmatch_report(pred, "Argentina", "Brazil", 2, 0)
    assert isinstance(r, PostMatch)
    assert r.outcome_pred == "home" and r.outcome_actual == "home"
    assert r.hit is True
    assert r.scoreline_in_top5 is True
    assert r.scoreline_rank == 1
    assert "acert" in r.verdict.lower()


def test_postmatch_error_de_resultado():
    pred = _pred(0.60, 0.25, 0.15, (2, 0))
    r = postmatch_report(pred, "Argentina", "Brazil", 0, 2)  # ganó el visitante
    assert r.outcome_pred == "home" and r.outcome_actual == "away"
    assert r.hit is False
    assert "falló" in r.verdict.lower() or "fallo" in r.verdict.lower()


def test_postmatch_marcador_fuera_del_top():
    pred = _pred(0.60, 0.25, 0.15, (2, 0))
    r = postmatch_report(pred, "Argentina", "Brazil", 4, 3)
    assert r.scoreline_in_top5 is False
    assert r.scoreline_rank is None


def test_postmatch_usa_nombres_en_espanol():
    pred = _pred(0.60, 0.25, 0.15, (2, 0))
    r = postmatch_report(pred, "Brazil", "Spain", 2, 0)
    assert "Brasil" in r.verdict and "España" in r.verdict
