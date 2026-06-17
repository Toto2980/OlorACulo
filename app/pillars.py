"""Análisis pre-partido por 6 pilares. Determinístico (sin LLM, sin internet):
se arma a partir del MatchReport (Poisson) + extras reales cuando hay (árbitro,
localía de anfitrión, historial, formaciones). Cada pilar se marca como DATO
(respaldado por datos) o ESTIMACIÓN (lectura sin datos de jugadores)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from app.flags import display_name

if TYPE_CHECKING:
    from oraculo.report.match_report import MatchReport

DATO = "dato"
ESTIMACION = "estimación"

# Anfitriones del Mundial 2026 (localía real).
HOSTS = {"United States", "Canada", "Mexico"}


@dataclass
class Pillar:
    titulo: str
    emoji: str
    texto: str
    fundamento: str  # DATO | ESTIMACION


def _favorito(report: "MatchReport", home: str, away: str) -> tuple[str, str, float]:
    if report.p_home >= report.p_away:
        return home, away, report.p_home
    return away, home, report.p_away


def _tempo(report: "MatchReport") -> tuple[str, float]:
    total = (report.xg_home or 0.0) + (report.xg_away or 0.0)
    if total >= 2.7:
        return "abierto", total
    if total <= 2.2:
        return "trabado", total
    return "de intensidad media", total


def prematch_pillars(
    report: "MatchReport",
    *,
    home: str,
    away: str,
    referee: Optional[str] = None,
    referee_country: Optional[str] = None,
    local_team: Optional[str] = None,
    h2h: Optional[tuple[int, int, int, int]] = None,
    lineups=None,
    weather: Optional[dict] = None,
    squad: Optional[dict] = None,
) -> list[Pillar]:
    fav, undog, fav_p = _favorito(report, home, away)
    parejo = max(report.p_home, report.p_draw, report.p_away) < 0.45
    tempo, total_xg = _tempo(report)
    H, A = display_name(home), display_name(away)
    FAV, UND = display_name(fav), display_name(undog)
    xh, xa = report.xg_home or 0.0, report.xg_away or 0.0

    pillars: list[Pillar] = []

    # 1 — Control del ritmo y posturas base
    quien = "Cruce parejo, nadie domina claro" if parejo else f"{FAV} es el llamado a imponer su tempo ({fav_p * 100:.0f}%)"
    if lineups:
        f_home = getattr(lineups[0], "formation", None) or "?"
        f_away = getattr(lineups[1], "formation", None) or "?"
        txt1 = (
            f"Choque de dibujos: {H} con {f_home} vs {A} con {f_away}. "
            f"{quien}. El partido pinta {tempo} (xG total {total_xg:.1f})."
        )
    else:
        txt1 = f"{quien}. El partido pinta {tempo} (xG total {total_xg:.1f})."
    pillars.append(Pillar("Control del ritmo y posturas base", "🎛️", txt1, DATO))

    # 2 — Emparejamientos individuales y zonas de conflicto
    home_top = (squad or {}).get("home_top")
    away_top = (squad or {}).get("away_top")
    if squad and (home_top or away_top):
        bits = []
        if home_top:
            bits.append(f"{H} se apoya en {home_top[0]} (rating {home_top[1]})")
        if away_top:
            bits.append(f"{A} en {away_top[0]} (rating {away_top[1]})")
        lado = H if xh >= xa else A
        txt2 = (
            "Duelo de figuras: " + "; ".join(bits) + f". El peso ofensivo cae del lado de {lado} "
            f"(xG {xh:.2f}–{xa:.2f}); ahí se rompe el equilibrio."
        )
        fund2 = DATO
    else:
        if abs(xh - xa) < 0.25:
            txt2 = f"Sin un lado claramente más peligroso (xG {xh:.2f}–{xa:.2f}): se define en los duelos del medio y en las transiciones."
        else:
            lado = H if xh > xa else A
            txt2 = f"El peso ofensivo cae del lado de {lado} (xG {xh:.2f}–{xa:.2f}); ahí está el mano a mano que rompe el equilibrio, y ojo a la pelota a la espalda."
        txt2 += " Sin datos de jugadores, es lectura del modelo."
        fund2 = ESTIMACION
    pillars.append(Pillar("Emparejamientos individuales y zonas de conflicto", "⚔️", txt2, fund2))

    # 3 — Pelota parada y juego aéreo
    if tempo == "trabado" or parejo:
        txt3 = "Partido cerrado: la pelota parada pesa el doble — suele ser el abrelatas, y la mejor chance del más débil."
    else:
        txt3 = "Con el juego abierto, la pelota parada suma pero no debería ser lo decisivo."
    pillars.append(Pillar("Pelota parada y juego aéreo", "🎯", txt3, ESTIMACION))

    # 4 — Gestión del desgaste y los bancos
    home_bench = (squad or {}).get("home_bench")
    away_bench = (squad or {}).get("away_bench")
    if squad and (home_bench is not None or away_bench is not None):
        txt4 = (
            f"Banco: {H} con {home_bench} suplentes vs {A} con {away_bench}. "
            "Los últimos 20-30' los define quién tenga recambio para mantener el nivel"
        )
        if not parejo:
            txt4 += f"; {FAV} además parte con ventaja para administrar"
        txt4 += "."
        fund4 = DATO
    else:
        txt4 = "Los últimos 20-30' suelen definir los partidos cerrados. "
        if not parejo:
            txt4 += f"{FAV}, con la ventaja, intentará administrar; "
        txt4 += "sin datos de plantel, la profundidad del banco queda como incógnita."
        fund4 = ESTIMACION
    pillars.append(Pillar("Gestión del desgaste y los bancos", "🔋", txt4, fund4))

    # 5 — Contexto ambiental
    partes: list[str] = []
    fund5 = ESTIMACION
    if referee:
        partes.append("Árbitro: " + referee + (f" ({referee_country})" if referee_country else ""))
        fund5 = DATO
    if local_team:
        partes.append(f"{display_name(local_team)} juega casi de local (anfitrión)")
        fund5 = DATO
    else:
        partes.append("Cancha neutral")
    if weather and weather.get("temperature") is not None:
        desc = weather.get("description")
        clima = f"Clima: {weather['temperature']}°C"
        if desc:
            clima += f", {desc.lower()}"
        if weather.get("precipitation"):
            clima += f", lluvia {weather['precipitation']} mm"
        partes.append(clima)
        fund5 = DATO
    else:
        partes.append("clima no disponible")
    pillars.append(Pillar("Contexto ambiental", "🌎", ". ".join(partes) + ".", fund5))

    # 6 — Mentalidad y manejo del momento
    if parejo:
        txt6 = "Dos parejos: gana quien maneje mejor el momento (presión, experiencia, liderazgo)."
    else:
        txt6 = f"{FAV} carga la mochila de favorito; {UND} juega liberado, sin nada que perder."
    if h2h:
        pj, wh, wa, dr = h2h
        if pj:
            txt6 += f" Historial: {pj} cruces, {H} {wh}–{wa} {A} y {dr} empates."
    txt6 += " El primer gol y el reloj mandan en el plano mental."
    pillars.append(Pillar("Mentalidad y manejo del momento", "🧠", txt6, DATO))

    return pillars
