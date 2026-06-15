from __future__ import annotations

from oraculo.tournament.groupstage import GroupStageResult

# Plantilla fija de 32avos (SIMPLIFICACIÓN de la tabla oficial de FIFA).
# Tokens: "W_<grupo>" = ganador, "R_<grupo>" = segundo, "T<n>" = n-ésimo mejor tercero.
# Construida para no cruzar ganador y segundo del mismo grupo en 32avos.
R32_TEMPLATE: list[tuple[str, str]] = [
    ("W_A", "R_B"),
    ("W_C", "R_D"),
    ("W_E", "T1"),
    ("W_G", "R_H"),
    ("W_I", "R_J"),
    ("W_K", "T2"),
    ("W_B", "R_A"),
    ("W_D", "R_C"),
    ("W_F", "T3"),
    ("W_H", "R_G"),
    ("W_J", "R_I"),
    ("W_L", "T4"),
    ("R_E", "T5"),
    ("R_F", "T6"),
    ("R_K", "T7"),
    ("R_L", "T8"),
]


def _resolve_slot(slot: str, gsr: GroupStageResult) -> str:
    kind = slot[0]
    if kind == "W":
        return gsr.standings[slot[2:]][0].team
    if kind == "R":
        return gsr.standings[slot[2:]][1].team
    if kind == "T":
        return gsr.best_thirds[int(slot[1:]) - 1].team
    raise ValueError(f"slot desconocido: {slot}")


def resolve_bracket(gsr: GroupStageResult) -> list[tuple[str, str]]:
    """Convierte la plantilla de slots en cruces concretos (nombres de equipos)."""
    return [(_resolve_slot(a, gsr), _resolve_slot(b, gsr)) for a, b in R32_TEMPLATE]
