from pathlib import Path

from oraculo.live.names import to_canonical, ALIASES
from oraculo.tournament.config import load_config

WC = Path(__file__).resolve().parent.parent / "data" / "wc2026.yaml"


def test_known_api_spellings_map_to_canonical():
    assert to_canonical("Bosnia-Herzegovina") == "Bosnia and Herzegovina"
    assert to_canonical("Cape Verde Islands") == "Cape Verde"
    assert to_canonical("Congo DR") == "DR Congo"
    assert to_canonical("Czechia") == "Czech Republic"


def test_identity_for_already_canonical():
    assert to_canonical("Argentina") == "Argentina"
    assert to_canonical("South Korea") == "South Korea"  # la API ya usa este nombre


def test_unknown_name_falls_back_to_itself():
    assert to_canonical("Atlantis") == "Atlantis"


def test_all_48_wc_teams_are_covered():
    teams = set(load_config(WC).teams)
    covered = set(ALIASES.values())
    missing = teams - covered
    assert not missing, f"equipos del Mundial sin entrada en ALIASES: {sorted(missing)}"
