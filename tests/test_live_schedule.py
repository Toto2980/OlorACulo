import datetime

from oraculo.live.fixtures import Fixture
from oraculo.live.schedule import Readiness, readiness, verification_checks

UTC = datetime.timezone.utc


def _ko(hours_from_now: float, now: datetime.datetime) -> datetime.datetime:
    return now + datetime.timedelta(hours=hours_from_now)


def _fx(**kw):
    base = dict(
        id=1, stage="GROUP_STAGE", group="A", home="Argentina", away="Brazil",
        kickoff_utc=datetime.datetime(2026, 6, 20, 19, 0, tzinfo=UTC),
        status="SCHEDULED", home_goals=None, away_goals=None,
    )
    base.update(kw)
    return Fixture(**base)


def test_readiness_far_away():
    now = datetime.datetime(2026, 6, 20, 10, 0, tzinfo=UTC)
    assert readiness(now, _ko(9, now)) == Readiness.LEJOS


def test_readiness_t60_t30_t15():
    now = datetime.datetime(2026, 6, 20, 18, 0, tzinfo=UTC)
    assert readiness(now, now + datetime.timedelta(minutes=50)) == Readiness.T60
    assert readiness(now, now + datetime.timedelta(minutes=25)) == Readiness.T30
    assert readiness(now, now + datetime.timedelta(minutes=10)) == Readiness.T15


def test_readiness_live_and_final_use_status():
    now = datetime.datetime(2026, 6, 20, 19, 30, tzinfo=UTC)
    assert readiness(now, now - datetime.timedelta(minutes=5), status="LIVE") == Readiness.EN_VIVO
    assert readiness(now, now - datetime.timedelta(hours=3), status="FINISHED") == Readiness.FINAL


def test_verification_checks_all_ok():
    checks = verification_checks(_fx())
    assert all(c.ok for c in checks)
    assert {c.label for c in checks} >= {"Fixture confirmado", "Rivales resueltos", "No postergado"}


def test_verification_flags_postponed_and_unresolved():
    checks = verification_checks(_fx(status="POSTPONED", home=None))
    by_label = {c.label: c.ok for c in checks}
    assert by_label["No postergado"] is False
    assert by_label["Rivales resueltos"] is False
