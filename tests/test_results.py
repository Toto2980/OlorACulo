import datetime
from pathlib import Path

from oraculo.ingest.results import load_results

FIXTURE = Path(__file__).parent / "fixtures" / "sample_results.csv"


def test_loads_only_played_matches():
    matches = load_results(FIXTURE)
    # la 4ta fila tiene marcador vacío y se ignora
    assert len(matches) == 3


def test_parses_fields():
    matches = load_results(FIXTURE)
    first = matches[0]
    assert first.date == datetime.date(2022, 11, 20)
    assert first.home == "Qatar"
    assert first.away == "Ecuador"
    assert first.home_goals == 0
    assert first.away_goals == 2
    assert first.neutral is False


def test_parses_neutral_true():
    matches = load_results(FIXTURE)
    assert matches[1].neutral is True
