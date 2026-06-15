from pathlib import Path

from oraculo.tournament.config import load_config, WorldCupConfig

FIXTURE = Path(__file__).parent / "fixtures" / "wc_test.yaml"


def _write_fixture():
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(
        "seed: 7\n"
        "groups:\n"
        "  A: [Argentina, Brazil, Chile, Peru]\n"
        "  B: [France, Spain, Italy, Germany]\n",
        encoding="utf-8",
    )


def test_loads_seed_and_groups():
    _write_fixture()
    cfg = load_config(FIXTURE)
    assert isinstance(cfg, WorldCupConfig)
    assert cfg.seed == 7
    assert cfg.groups["A"] == ["Argentina", "Brazil", "Chile", "Peru"]
    assert len(cfg.groups) == 2


def test_teams_flattens_all_groups():
    _write_fixture()
    cfg = load_config(FIXTURE)
    assert len(cfg.teams) == 8
    assert "Italy" in cfg.teams
