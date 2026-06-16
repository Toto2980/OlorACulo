import datetime

from oraculo.match import Match
from oraculo.verify.predictor import WC_CUTOFF, frozen_poisson


def _m(year, month, day, hg, ag):
    return Match(
        date=datetime.date(year, month, day),
        home="Argentina", away="Brazil", home_goals=hg, away_goals=ag,
        tournament="FIFA World Cup", neutral=True,
    )


def test_cutoff_default_is_wc_start():
    assert WC_CUTOFF == datetime.date(2026, 6, 11)


def test_frozen_model_ignores_matches_on_or_after_cutoff():
    pre = [_m(2025, 1, 1, 3, 0), _m(2025, 6, 1, 2, 0)]
    post = [_m(2026, 6, 12, 0, 5)]  # un partido del Mundial que NO debe influir
    only_pre = frozen_poisson(pre)
    with_post = frozen_poisson(pre + post)
    # las predicciones deben ser idénticas: el partido post-cutoff fue descartado
    a = only_pre.predict("Argentina", "Brazil", neutral=True)
    b = with_post.predict("Argentina", "Brazil", neutral=True)
    assert a.probs == b.probs
