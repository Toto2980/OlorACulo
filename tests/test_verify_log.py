import datetime

from oraculo.verify.log import append_snapshot, load_log


def test_append_and_load(tmp_path):
    path = tmp_path / "predictions_log.json"
    now = datetime.datetime(2026, 6, 20, 18, 0, tzinfo=datetime.timezone.utc)
    append_snapshot(path, fixture_id=1, probs=(0.7, 0.2, 0.1), top_score=(2, 0), now=now)
    log = load_log(path)
    assert "1" in log
    assert log["1"]["p_home"] == 0.7
    assert log["1"]["top_score"] == [2, 0]


def test_append_is_idempotent_per_fixture(tmp_path):
    path = tmp_path / "predictions_log.json"
    append_snapshot(path, 1, (0.7, 0.2, 0.1), (2, 0))
    append_snapshot(path, 1, (0.1, 0.2, 0.7), (0, 2))  # no debe pisar el primero
    log = load_log(path)
    assert log["1"]["p_home"] == 0.7


def test_load_missing_returns_empty(tmp_path):
    assert load_log(tmp_path / "nope.json") == {}
