from oraculo.tournament.bracket import R32_TEMPLATE, resolve_bracket
from oraculo.tournament.group import TeamRecord
from oraculo.tournament.groupstage import GroupStageResult


def _fake_gsr():
    standings = {
        g: [TeamRecord(f"{g}1"), TeamRecord(f"{g}2"), TeamRecord(f"{g}3"), TeamRecord(f"{g}4")]
        for g in "ABCDEFGHIJKL"
    }
    best_thirds = [TeamRecord(f"Third{i}") for i in range(1, 9)]
    return GroupStageResult(standings=standings, advancing=set(), best_thirds=best_thirds)


def test_template_has_16_matches_and_32_distinct_slots():
    assert len(R32_TEMPLATE) == 16
    slots = [s for pair in R32_TEMPLATE for s in pair]
    assert len(slots) == 32
    assert len(set(slots)) == 32


def test_resolve_maps_slots_to_team_names():
    pairs = resolve_bracket(_fake_gsr())
    assert len(pairs) == 16
    assert pairs[0] == ("A1", "B2")
    for a, b in pairs:
        assert isinstance(a, str) and isinstance(b, str) and a and b


def test_resolve_uses_best_thirds():
    pairs = resolve_bracket(_fake_gsr())
    resolved = {t for pair in pairs for t in pair}
    for i in range(1, 9):
        assert f"Third{i}" in resolved
