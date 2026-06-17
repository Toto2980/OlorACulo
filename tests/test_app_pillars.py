from types import SimpleNamespace

from app.pillars import prematch_pillars, Pillar, DATO, ESTIMACION
from oraculo.report.match_report import MatchReport, Speculative


def _report(p_home, p_draw, p_away, xg_home, xg_away, over25=0.45, home="Argentina", away="Brazil"):
    return MatchReport(
        home=home, away=away,
        p_home=p_home, p_draw=p_draw, p_away=p_away,
        xg_home=xg_home, xg_away=xg_away,
        top_scores=[((1, 0), 0.12)],
        btts=0.4, over25=over25, over15=0.7,
        speculative=Speculative(top_scorer_team=home, cards_band="3–5"),
    )


def test_devuelve_seis_pilares():
    ps = prematch_pillars(_report(0.5, 0.25, 0.25, 1.4, 1.0), home="Argentina", away="Brazil")
    assert len(ps) == 6
    assert all(isinstance(p, Pillar) for p in ps)
    assert all(p.fundamento in (DATO, ESTIMACION) for p in ps)


def test_favorito_claro_nombra_al_favorito_en_pilar1():
    ps = prematch_pillars(_report(0.70, 0.20, 0.10, 1.8, 0.7), home="Argentina", away="Brazil")
    assert "Argentina" in ps[0].texto
    assert ps[0].fundamento == DATO


def test_partido_trabado_menciona_abrelatas_en_pelota_parada():
    # xG total bajo -> trabado
    ps = prematch_pillars(_report(0.40, 0.34, 0.26, 1.0, 0.9), home="Argentina", away="Brazil")
    pelota = ps[2]
    assert "Pelota parada" in pelota.titulo
    assert "abrelatas" in pelota.texto.lower()


def test_arbitro_es_dato_en_contexto():
    ps = prematch_pillars(
        _report(0.5, 0.25, 0.25, 1.4, 1.0), home="Argentina", away="Brazil",
        referee="Wilton Sampaio", referee_country="Brazil",
    )
    ctx = next(p for p in ps if "ambiental" in p.titulo.lower())
    assert "Wilton Sampaio" in ctx.texto
    assert ctx.fundamento == DATO


def test_sin_arbitro_ni_localia_contexto_es_estimacion():
    ps = prematch_pillars(_report(0.5, 0.25, 0.25, 1.4, 1.0), home="Argentina", away="Brazil")
    ctx = next(p for p in ps if "ambiental" in p.titulo.lower())
    assert ctx.fundamento == ESTIMACION


def test_localia_anfitrion_se_marca_dato():
    ps = prematch_pillars(
        _report(0.5, 0.25, 0.25, 1.4, 1.0), home="Mexico", away="Brazil",
        local_team="Mexico",
    )
    ctx = next(p for p in ps if "ambiental" in p.titulo.lower())
    assert "local" in ctx.texto.lower()
    assert ctx.fundamento == DATO


def test_con_formaciones_pilar1_es_dato_y_menciona_dibujo():
    lu = (SimpleNamespace(formation="4-3-3"), SimpleNamespace(formation="5-3-2"))
    ps = prematch_pillars(
        _report(0.5, 0.25, 0.25, 1.4, 1.0), home="Argentina", away="Brazil", lineups=lu,
    )
    assert "4-3-3" in ps[0].texto and "5-3-2" in ps[0].texto
    assert ps[0].fundamento == DATO


def test_historial_aparece_en_mentalidad():
    ps = prematch_pillars(
        _report(0.70, 0.20, 0.10, 1.8, 0.7), home="Argentina", away="Brazil",
        h2h=(10, 5, 4, 1),
    )
    ment = ps[5]
    assert "Mentalidad" in ment.titulo
    assert "10" in ment.texto  # PJ del historial


def test_squad_convierte_duelos_y_bancos_en_dato():
    squad = {
        "home_top": ("Messi", 8.5), "away_top": ("Neymar", 7.9),
        "home_bench": 9, "away_bench": 9,
    }
    ps = prematch_pillars(
        _report(0.6, 0.2, 0.2, 1.6, 1.0), home="Argentina", away="Brazil", squad=squad,
    )
    duelos = next(p for p in ps if "Emparejamientos" in p.titulo)
    bancos = next(p for p in ps if "desgaste" in p.titulo.lower())
    assert duelos.fundamento == DATO and "Messi" in duelos.texto
    assert bancos.fundamento == DATO and "9" in bancos.texto


def test_sin_squad_duelos_y_bancos_siguen_estimacion():
    ps = prematch_pillars(_report(0.6, 0.2, 0.2, 1.6, 1.0), home="Argentina", away="Brazil")
    duelos = next(p for p in ps if "Emparejamientos" in p.titulo)
    bancos = next(p for p in ps if "desgaste" in p.titulo.lower())
    assert duelos.fundamento == ESTIMACION
    assert bancos.fundamento == ESTIMACION


def test_clima_real_enriquece_contexto_y_es_dato():
    ps = prematch_pillars(
        _report(0.5, 0.25, 0.25, 1.4, 1.0), home="Argentina", away="Brazil",
        weather={"temperature": 23, "description": "Clear", "precipitation": 0},
    )
    ctx = next(p for p in ps if "ambiental" in p.titulo.lower())
    assert "23" in ctx.texto
    assert ctx.fundamento == DATO
