from oraculo.verify.scoring import (
    actual_outcome,
    score_match,
    aggregate,
    calibration_bins,
)


def test_actual_outcome():
    assert actual_outcome(2, 0) == "home"
    assert actual_outcome(1, 1) == "draw"
    assert actual_outcome(0, 3) == "away"


def test_score_match_hit_and_metrics():
    # predijo local (0.7) y ganó local -> acierto
    s = score_match(fixture_id=1, probs=(0.7, 0.2, 0.1), home_goals=2, away_goals=0)
    assert s.outcome_pred == "home"
    assert s.outcome_actual == "home"
    assert s.hit is True
    assert s.brier >= 0.0 and s.rps >= 0.0


def test_score_match_miss():
    s = score_match(fixture_id=2, probs=(0.6, 0.3, 0.1), home_goals=0, away_goals=1)
    assert s.outcome_pred == "home"
    assert s.outcome_actual == "away"
    assert s.hit is False


def test_aggregate_counts_and_means():
    scores = [
        score_match(1, (0.7, 0.2, 0.1), 2, 0),  # hit
        score_match(2, (0.6, 0.3, 0.1), 0, 1),  # miss
    ]
    summ = aggregate(scores)
    assert summ.n == 2
    assert summ.hit_rate == 0.5
    assert summ.mean_brier > 0.0
    assert summ.mean_rps > 0.0


def test_calibration_bins_groups_predictions():
    # pares (prob_predicha_de_local, ganó_local?)
    pairs = [(0.9, True), (0.85, True), (0.2, False), (0.1, False)]
    bins = calibration_bins(pairs, n_bins=2)
    assert len(bins) == 2
    # cada bin: (centro, prob_media_predicha, frecuencia_real, n)
    low, high = bins[0], bins[1]
    assert low.n == 2 and high.n == 2
    assert high.observed == 1.0   # los dos de prob alta ganaron
    assert low.observed == 0.0    # los dos de prob baja no
