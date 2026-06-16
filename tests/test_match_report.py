import numpy as np

from oraculo.report.match_report import (
    MatchReport,
    btts_prob,
    over_prob,
    build_match_report,
)
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.match import Match
import datetime


def test_btts_and_over_on_known_matrix():
    m = np.zeros((3, 3))
    m[0, 0] = 0.25  # 0-0
    m[1, 0] = 0.25  # 1-0
    m[1, 1] = 0.25  # 1-1
    m[2, 2] = 0.25  # 2-2 (over 2.5)
    # BTTS = casos donde ambos > 0 = (1,1)+(2,2) = 0.5
    assert abs(btts_prob(m) - 0.5) < 1e-9
    # over 2.5 = total >= 3 = solo (2,2) = 0.25
    assert abs(over_prob(m, line=2.5) - 0.25) < 1e-9


def _model():
    matches = [
        Match(datetime.date(2024, 1, d), "Argentina", "Brazil", 2, 1, "Friendly", True)
        for d in range(1, 6)
    ]
    return PoissonModel(PoissonConfig(lr=0.05)).fit(matches)


def test_build_match_report_shape():
    r = build_match_report(_model(), "Argentina", "Brazil", neutral=True)
    assert isinstance(r, MatchReport)
    assert abs(r.p_home + r.p_draw + r.p_away - 1.0) < 1e-6
    assert 0.0 <= r.btts <= 1.0
    assert 0.0 <= r.over25 <= 1.0
    assert len(r.top_scores) == 5
    # extras especulativos presentes y marcados
    assert r.speculative.top_scorer_team in ("Argentina", "Brazil")
    assert "–" in r.speculative.cards_band
