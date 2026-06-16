import datetime

import numpy as np

from oraculo.match import Match
from oraculo.evaluate.backtest import EvalResult
from app.services import top_scorelines, model_comparison, prode_verdict, scoreline_hit
from oraculo.report.match_report import MatchReport, Speculative


def test_top_scorelines_orders_by_probability():
    m = np.zeros((11, 11))
    m[2, 3] = 0.6
    m[1, 0] = 0.4
    top = top_scorelines(m, n=2)
    assert top[0] == ((2, 3), 0.6)
    assert top[1] == ((1, 0), 0.4)


def test_top_scorelines_length():
    m = np.full((11, 11), 1.0 / 121)
    assert len(top_scorelines(m, n=5)) == 5


def _matches():
    out = []
    day = 1
    for year in (2008, 2009, 2011, 2012):
        for _ in range(3):
            out.append(Match(
                date=datetime.date(year, 1, day),
                home="A", away="B", home_goals=2, away_goals=1,
                tournament="Friendly", neutral=True,
            ))
            day += 1
    return out


def test_model_comparison_returns_three_eval_results():
    res = model_comparison(_matches(), datetime.date(2010, 1, 1))
    assert set(res.keys()) == {"uniforme", "elo", "poisson"}
    for ev in res.values():
        assert isinstance(ev, EvalResult)
        assert ev.n_matches > 0


def _report(p_home, p_draw, p_away, over25, home="Argentina", away="Brazil"):
    return MatchReport(
        home=home, away=away,
        p_home=p_home, p_draw=p_draw, p_away=p_away,
        xg_home=1.5, xg_away=0.8,
        top_scores=[((1, 0), 0.12)],
        btts=0.4, over25=over25, over15=0.7,
        speculative=Speculative(top_scorer_team=home, cards_band="3–5"),
    )


def test_prode_verdict_favorito_claro_usa_nombre_es():
    txt = prode_verdict(_report(0.70, 0.20, 0.10, over25=0.30))
    assert "Brasil" in txt          # away traducido al español
    assert "favorito" in txt.lower()
    assert "%" in txt


def test_prode_verdict_cruce_parejo_lo_dice():
    txt = prode_verdict(_report(0.35, 0.33, 0.32, over25=0.50))
    assert "parejo" in txt.lower()


def test_prode_verdict_pocos_goles_cuando_over25_bajo():
    txt = prode_verdict(_report(0.70, 0.20, 0.10, over25=0.30))
    assert "pocos goles" in txt.lower()


def _matrix_con(marcadores):
    """marcadores: dict {(i,j): prob}. Devuelve matriz 11x11."""
    m = np.zeros((11, 11))
    for (i, j), p in marcadores.items():
        m[i, j] = p
    return m


def test_scoreline_hit_true_cuando_el_real_esta_en_el_top_n():
    m = _matrix_con({(1, 0): 0.5, (0, 0): 0.3, (2, 1): 0.2})
    assert scoreline_hit(m, 1, 0, n=3) is True
    assert scoreline_hit(m, 2, 1, n=3) is True


def test_scoreline_hit_false_cuando_el_real_no_esta_en_el_top_n():
    m = _matrix_con({(1, 0): 0.5, (0, 0): 0.3, (2, 1): 0.2})
    assert scoreline_hit(m, 3, 3, n=3) is False


def test_scoreline_hit_false_cuando_marcador_fuera_de_la_matriz():
    m = _matrix_con({(1, 0): 1.0})
    assert scoreline_hit(m, 20, 0, n=5) is False
