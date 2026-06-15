from pathlib import Path

from oraculo.ingest.results import load_results
from oraculo.tournament.config import load_config

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"


def test_all_wc2026_teams_exist_in_history():
    matches = load_results(DATA)
    known = {m.home for m in matches} | {m.away for m in matches}
    cfg = load_config(WC)
    missing = [t for t in cfg.teams if t not in known]
    assert missing == [], f"equipos sin datos históricos: {missing}"


def test_twelve_groups_of_four():
    cfg = load_config(WC)
    assert len(cfg.groups) == 12
    assert all(len(teams) == 4 for teams in cfg.groups.values())
    assert len(cfg.teams) == 48
