"""OlorACulo — página web (Streamlit). Correr con:
    .\\.venv\\Scripts\\python.exe -m streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from oraculo.ingest.results import load_results
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.tournament.config import load_config
from oraculo.tournament.tournament import run_tournament_mc
from app.services import (
    top_scorelines,
    model_comparison,
    prode_verdict,
    scoreline_hit,
    head_to_head,
)
from app.flags import with_flag, display_name
from app.pillars import prematch_pillars, DATO

import os

from oraculo.live.client import LiveClient, LiveDataError
from oraculo.live.fixtures import parse_fixtures
from oraculo.live.lineups import LineupClient
from oraculo.live.schedule import Readiness
from oraculo.report.match_report import build_match_report
from oraculo.verify.predictor import frozen_poisson
from oraculo.verify.scoring import score_match, aggregate, calibration_bins
from app.live_view import group_by_phase, upcoming_rows, finished_rows
from app.charts import (
    ranking_bar,
    calibration_chart,
    scoreline_heatmap,
    xg_bars,
    markets_bars,
    progression_bars,
    rps_line,
)

DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"
EVAL_FROM = datetime.date(2010, 1, 1)

# Paleta "Álbum '86" — figuritas Panini
GREEN = "#3c7a4e"      # verde césped vintage
GREEN_DK = "#2a6b3e"
ORANGE = "#e8a33d"     # naranja mostaza
RED = "#e84f3d"        # rojo figurita
INK = "#2b2b2b"
MUTED = "#c9bfa3"      # tan apagado (empate / neutro)

ACCENT = GREEN
ACCENT_2 = ORANGE
LABEL = INK


# --------------------------------------------------------------------------- #
# Caché de recursos pesados
# --------------------------------------------------------------------------- #
@st.cache_resource
def get_matches():
    return load_results(DATA)


@st.cache_resource
def get_poisson():
    return PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)).fit(get_matches())


@st.cache_resource
def get_elo():
    return EloModel().fit(get_matches())


@st.cache_resource
def get_config():
    return load_config(WC)


@st.cache_resource
def get_frozen():
    """Poisson congelado al inicio del Mundial (sin data leakage) para verificación."""
    return frozen_poisson(get_matches())


def _token():
    try:
        return st.secrets["FOOTBALL_DATA_TOKEN"]
    except Exception:
        return os.environ.get("FOOTBALL_DATA_TOKEN")


@st.cache_data(ttl=60)
def get_fixtures():
    client = LiveClient(_token())
    raw = client.get_matches()
    return parse_fixtures(raw), client.fetched_at


@st.cache_data
def champion_probs(n_iter: int, known_items: tuple = ()):
    """known_items: tupla hashable de (home, away, hg, ag) de partidos ya jugados.
    Se respetan en la simulación (no se muestrean)."""
    known: dict = {}
    for h, a, hg, ag in known_items:
        known[(h, a)] = (hg, ag)
        known[(a, h)] = (ag, hg)
    return run_tournament_mc(
        get_poisson(), get_config(), n_iter=n_iter, known=known or None
    )


def _played_known_items():
    """Resultados ya jugados del Mundial (solo equipos del torneo), como tupla hashable."""
    try:
        fx, _ = get_fixtures()
    except LiveDataError:
        return ()
    teamset = set(get_config().teams)
    return tuple(
        (r["home"], r["away"], r["home_goals"], r["away_goals"])
        for r in finished_rows(fx)
        if r["home"] in teamset and r["away"] in teamset
    )


@st.cache_data
def model_metrics():
    res = model_comparison(get_matches(), EVAL_FROM)
    return {k: {"RPS": v.rps, "Brier": v.brier, "LogLoss": v.log_loss} for k, v in res.items()}


# --------------------------------------------------------------------------- #
# Análisis pre-partido (6 pilares)
# --------------------------------------------------------------------------- #
HOSTS = {"United States", "Canada", "Mexico"}


def _local_team(home: str, away: str):
    if home in HOSTS:
        return home
    if away in HOSTS:
        return away
    return None


def _build_pillars(home: str, away: str, *, referee=None, referee_country=None, lineups=None):
    report = build_match_report(get_poisson(), home, away, neutral=True)
    h2h = head_to_head(get_matches(), home, away)
    return prematch_pillars(
        report, home=home, away=away,
        referee=referee, referee_country=referee_country,
        local_team=_local_team(home, away), h2h=h2h, lineups=lineups,
    )


def _render_pillars(pillars, target=st):
    for p in pillars:
        chip = "📊 dato" if p.fundamento == DATO else "🔮 estimación"
        target.markdown(
            f"<div class='scoreline'><b>{p.emoji} {p.titulo}</b> "
            f"<span class='caption'>· {chip}</span><br>{p.texto}</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Formaciones (API-Football, opcional por API key)
# --------------------------------------------------------------------------- #
LINEUP_READY = {Readiness.T30, Readiness.T15, Readiness.EN_VIVO}


def _apifootball_token():
    try:
        return st.secrets["API_FOOTBALL_KEY"]
    except Exception:
        return os.environ.get("API_FOOTBALL_KEY")


@st.cache_data(ttl=300)
def _lineups_for(home: str, away: str, date_iso: str):
    """(lineup_home, lineup_away) o None. Cacheado 5 min (cuida las 100 req/día)."""
    token = _apifootball_token()
    if not token:
        return None
    return LineupClient(token).lineups_for(home, away, datetime.date.fromisoformat(date_iso))


def _render_lineups(home: str, away: str, lineups) -> None:
    home_lu, away_lu = lineups
    c1, c2 = st.columns(2)
    for col, team, lu in ((c1, home, home_lu), (c2, away, away_lu)):
        col.markdown(f"**{with_flag(team)} · {lu.formation or '?'}**")
        for pos, name in lu.start_xi:
            col.markdown(f"<div class='scoreline'>{pos} · {name}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Estilo — álbum de figuritas
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="OlorACulo — Álbum Mundial 2026", page_icon="⚽", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Bungee&family=Fredoka:wght@400;500;600;700&display=swap');

      #MainMenu, footer, header {visibility: hidden;}

      /* Fondo crema con textura de puntitos (papel de álbum) */
      .stApp {
        background-color: #f7e9cf;
        background-image: radial-gradient(#e7d4a9 1.3px, transparent 1.3px);
        background-size: 20px 20px;
      }
      html, body, [class*="css"], .stMarkdown, p, div, span, label {
        font-family: 'Fredoka', sans-serif;
      }
      .block-container {padding-top: 1.4rem; max-width: 1180px;}

      h1, h2, h3 {
        font-family: 'Bungee', sans-serif !important;
        color: #2a6b3e !important; letter-spacing: .5px;
      }

      /* Hero: logo tipo sticker rojo pegado */
      .hero {
        background: #ffffff; border-radius: 20px; padding: 24px 30px;
        margin-bottom: 24px; position: relative; overflow: hidden;
        border: 3px solid #ffffff;
        box-shadow: 0 6px 0 rgba(0,0,0,.10), 0 12px 26px rgba(0,0,0,.12);
      }
      .logo-sticker {
        display: inline-block; font-family: 'Bungee', sans-serif;
        font-size: 2.3rem; color: #fff; background: #e84f3d;
        padding: 8px 22px; border-radius: 14px; letter-spacing: 2px;
        border: 4px solid #fff; transform: rotate(-2deg);
        box-shadow: 0 0 0 3px #e84f3d, 0 5px 12px rgba(0,0,0,.28);
      }
      .hero p {
        font-family: 'Fredoka', sans-serif; font-weight: 600;
        color: #3c7a4e; font-size: 1.1rem; margin: 1rem 0 0;
      }
      .pill {
        display: inline-block; background: #3c7a4e; color: #fff;
        padding: 4px 14px; border-radius: 999px; font-size: .8rem;
        font-weight: 600; margin-top: 12px;
      }

      /* Métricas = figuritas con borde punteado y tilt */
      div[data-testid="stMetric"] {
        background: #fffdf7; border: 3px dashed #e8a33d; border-radius: 16px;
        padding: 16px 18px; box-shadow: 0 5px 10px rgba(0,0,0,.08);
        transition: transform .15s ease;
      }
      [data-testid="column"]:nth-child(odd) div[data-testid="stMetric"]  {transform: rotate(-1.6deg);}
      [data-testid="column"]:nth-child(even) div[data-testid="stMetric"] {transform: rotate(1.6deg);}
      div[data-testid="stMetric"]:hover {transform: rotate(0deg) scale(1.03);}
      [data-testid="stMetricValue"] {
        font-family: 'Bungee', sans-serif !important; color: #e84f3d !important;
        font-size: 1.85rem !important;
      }
      [data-testid="stMetricLabel"] p {
        font-family: 'Fredoka', sans-serif !important; font-weight: 600 !important;
        color: #2a6b3e !important;
      }

      /* Tabs = solapas de cartón del álbum */
      .stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: 3px solid #2a6b3e;}
      .stTabs [data-baseweb="tab"] {
        background: #fbe7c8; border: 2px solid #d9b876; border-bottom: none;
        border-radius: 14px 14px 0 0; padding: 8px 20px;
        font-weight: 600; color: #7a6a3a;
      }
      .stTabs [aria-selected="true"] {
        background: #e8a33d !important; color: #fff !important; border-color: #e8a33d;
      }

      /* Botones chunky */
      .stButton > button {
        font-family: 'Bungee', sans-serif !important; border-radius: 14px !important;
        letter-spacing: .5px; border: 2px solid #d9b876 !important; color: #7a6a3a;
      }
      .stButton > button[kind="primary"] {
        background: #e84f3d !important; color: #fff !important;
        border: 3px solid #fff !important;
        box-shadow: 0 0 0 2px #e84f3d, 0 4px 9px rgba(0,0,0,.22) !important;
      }

      /* Veredicto = figurita destacada */
      .verdict {
        background: #fffdf7; border: 3px dashed #3c7a4e; border-radius: 14px;
        padding: 12px 18px; margin: 6px 0 16px; color: #2a6b3e;
        font-weight: 600; font-size: 1.06rem;
      }
      /* Favorito = figu dorada */
      .fav {
        background: #fff8e8; border: 4px solid #e8a33d; border-radius: 18px;
        padding: 18px 24px; font-weight: 600; font-size: 1.25rem;
        color: #2a6b3e; margin-bottom: 18px; transform: rotate(-1.2deg);
        box-shadow: 0 6px 0 rgba(232,163,61,.35);
      }
      .scoreline {
        background: #fffdf7; border: 2px solid #e7d4a9; border-radius: 10px;
        padding: 6px 12px; margin: 5px 0; font-weight: 500;
      }
      .caption {color: #8a857a; font-size: .86rem; font-weight: 500;}
      .footer {
        text-align: center; color: #8a857a; font-size: .82rem; font-weight: 500;
        margin-top: 42px; padding-top: 16px; border-top: 3px dashed #d9b876;
      }
      .footer a {color: #e84f3d; font-weight: 600; text-decoration: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <span class="logo-sticker">⚽ OLORÁCULO</span>
      <p>¡Pegá tu figurita del Mundial 2026! 📒</p>
      <span class="pill">Modelo Poisson · Dixon-Coles · 49.000 partidos de archivo</span>
    </div>
    """,
    unsafe_allow_html=True,
)

teams = sorted(get_config().teams)

tab_live, tab_bracket, tab_match, tab_prode, tab_cup, tab_verify = st.tabs(
    ["🔴  En vivo", "🗺️  Cuadro", "⚽  Partido", "📋  Prode", "🏆  Mundial", "🎯  Verificación"]
)


# --------------------------------------------------------------------------- #
# Vista: En vivo
# --------------------------------------------------------------------------- #
with tab_live:
    st.subheader("Partidos del Mundial en vivo")
    try:
        fixtures, fetched_at = get_fixtures()
    except LiveDataError:
        st.error("Sin datos: configurá FOOTBALL_DATA_TOKEN en .streamlit/secrets.toml.")
        fixtures, fetched_at = [], None

    if fetched_at:
        st.caption(f"Datos al {fetched_at:%Y-%m-%d %H:%M UTC}")

    if fixtures:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        st.markdown("#### ⏱️ Próximos")
        upcoming = upcoming_rows(fixtures, now=now)[:8]
        if not upcoming:
            st.caption("No hay próximos partidos cargados.")
        for r in upcoming:
            cols = st.columns([4, 3, 3])
            partido_es = (
                f"{with_flag(r['home'])} vs {with_flag(r['away'])}"
                if r["home"] and r["away"]
                else r["partido"]
            )
            cols[0].markdown(f"**{partido_es}**  ·  _{r['fase']}_")
            cols[1].markdown(f"🕒 {r['kickoff']:%d/%m %H:%M} UTC")
            cols[2].markdown(f"🔖 {r['estado']}")
            ok = sum(c.ok for c in r["checks"])
            cols[2].caption(f"Verificación: {ok}/{len(r['checks'])} checks")
            if r["home"] in teams and r["away"] in teams:
                with st.expander("🔍 Análisis pre-partido (resumen)"):
                    report = build_match_report(get_poisson(), r["home"], r["away"], neutral=True)
                    st.markdown(
                        f"<div class='verdict'>🃏 {prode_verdict(report)}</div>",
                        unsafe_allow_html=True,
                    )
                    pillars = _build_pillars(
                        r["home"], r["away"],
                        referee=r.get("referee"), referee_country=r.get("referee_country"),
                    )
                    _render_pillars([p for p in pillars if p.fundamento == DATO])

        st.markdown("#### ✅ Resultados recientes (real vs predicho)")
        model = get_frozen()
        recientes = finished_rows(fixtures)[-8:]
        if not recientes:
            st.caption("Todavía no hay resultados.")
        for r in recientes:
            pred = model.predict(r["home"], r["away"], neutral=True)
            s = score_match(r["id"], pred.probs, r["home_goals"], r["away_goals"])
            mark = "✅" if s.hit else "❌"
            st.markdown(
                f"<div class='scoreline'>{mark} {with_flag(r['home'])} "
                f"<b>{r['marcador']}</b> {with_flag(r['away'])} · "
                f"predicho: {s.outcome_pred} · RPS {s.rps:.3f}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Cuando haya partidos cargados, aparecen acá con su predicción.")


# --------------------------------------------------------------------------- #
# Vista: Analizar partido
# --------------------------------------------------------------------------- #
with tab_match:
    st.subheader("Analizá un partido")
    c1, c2, c3 = st.columns([3, 3, 2])
    home = c1.selectbox("Equipo 1", teams, index=teams.index("Argentina"), format_func=with_flag)
    away = c2.selectbox("Equipo 2", teams, index=teams.index("Brazil"), format_func=with_flag)
    model_name = c3.radio("Modelo", ["Poisson", "Elo"], horizontal=True)
    neutral = st.toggle("Cancha neutral", value=True)

    model = get_poisson() if model_name == "Poisson" else get_elo()
    pred = model.predict(home, away, neutral=neutral)

    m1, m2, m3 = st.columns(3)
    m1.metric(with_flag(home), f"{pred.p_home * 100:.1f}%", "gana")
    m2.metric("Empate", f"{pred.p_draw * 100:.1f}%")
    m3.metric(with_flag(away), f"{pred.p_away * 100:.1f}%", "gana")

    options = {f"Gana {home}": pred.p_home, "Empate": pred.p_draw, f"Gana {away}": pred.p_away}
    best = max(options, key=options.get)
    st.markdown(
        f"<div class='verdict'>🃏 Figurita más probable: <b>{best}</b> · {options[best] * 100:.0f}%</div>",
        unsafe_allow_html=True,
    )

    seg = pd.DataFrame(
        {
            "Resultado": [f"Gana {home}", "Empate", f"Gana {away}"],
            "Probabilidad": [pred.p_home, pred.p_draw, pred.p_away],
            "orden": [0, 1, 2],
        }
    )
    bar = (
        alt.Chart(seg)
        .mark_bar()
        .encode(
            x=alt.X("Probabilidad:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(
                    domain=[f"Gana {home}", "Empate", f"Gana {away}"],
                    range=[ACCENT, MUTED, ACCENT_2],
                ),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            order=alt.Order("orden:Q"),
            tooltip=["Resultado", alt.Tooltip("Probabilidad:Q", format=".1%")],
        )
        .properties(height=84)
    )
    st.altair_chart(bar, width="stretch")

    if pred.xg_home is not None:
        left, right = st.columns(2)
        with left:
            st.markdown("**Goles esperados**")
            st.markdown(
                f"### {with_flag(home)} {pred.xg_home:.2f} – {pred.xg_away:.2f} {with_flag(away)}"
            )
        with right:
            st.markdown("**Marcadores más probables**")
            for (i, j), p in top_scorelines(pred.score_matrix, 5):
                st.markdown(
                    f"<div class='scoreline'>{with_flag(home)} <b>{i}–{j}</b> {with_flag(away)} "
                    f"· {p * 100:.1f}%</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("**Mapa de calor de marcadores**")
        st.altair_chart(
            scoreline_heatmap(pred.score_matrix, with_flag(home), with_flag(away)),
            width="stretch",
        )
        st.altair_chart(
            xg_bars(with_flag(home), with_flag(away), pred.xg_home, pred.xg_away),
            width="stretch",
        )

        report = build_match_report(model, home, away, neutral=neutral)
        st.markdown("**Mercados derivados**")
        d1, d2 = st.columns(2)
        d1.metric("Ambos marcan (BTTS)", f"{report.btts * 100:.0f}%")
        d2.metric("Over 2.5 goles", f"{report.over25 * 100:.0f}%")
        st.altair_chart(markets_bars(report.btts, report.over25, report.over15), width="stretch")
        st.markdown(
            f"<div class='caption'>⚠️ Estimación (no sale del modelo): "
            f"favorito a convertir <b>{display_name(report.speculative.top_scorer_team)}</b> · "
            f"tarjetas estimadas {report.speculative.cards_band}.</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Vista: Prode (análisis pre-partido)
# --------------------------------------------------------------------------- #
with tab_prode:
    st.subheader("📋 El prode del oráculo")
    st.markdown(
        '<p class="caption">Análisis pre-partido completo para armar tu prode. '
        'Usa el modelo Poisson y cancha neutral (es Mundial).</p>',
        unsafe_allow_html=True,
    )

    # Selección de partido: fixtures reales si hay; si no, dos equipos cualquiera.
    try:
        fixtures, _ = get_fixtures()
    except LiveDataError:
        fixtures = []
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    proximos = upcoming_rows(fixtures, now=now) if fixtures else []
    # Solo cruces con ambos equipos definidos y conocidos por el modelo.
    candidatos = [r for r in proximos if r["home"] in teams and r["away"] in teams]

    p_referee = p_referee_country = None
    if candidatos:
        labels = [
            f"{r['fase']} · {with_flag(r['home'])} vs {with_flag(r['away'])} · {r['kickoff']:%d/%m %H:%M} UTC"
            for r in candidatos
        ]
        idx = st.selectbox(
            "Partido del Mundial", range(len(labels)), format_func=lambda i: labels[i]
        )
        chosen = candidatos[idx]
        p_home_team, p_away_team = chosen["home"], chosen["away"]
        p_referee, p_referee_country = chosen.get("referee"), chosen.get("referee_country")
        st.caption(f"Fase: {chosen['fase']}")
    else:
        st.info("No hay próximos partidos del fixture; elegí dos equipos.")
        cc1, cc2 = st.columns(2)
        p_home_team = cc1.selectbox(
            "Equipo 1", teams, index=teams.index("Argentina"),
            format_func=with_flag, key="prode_home",
        )
        p_away_team = cc2.selectbox(
            "Equipo 2", teams, index=teams.index("Brazil"),
            format_func=with_flag, key="prode_away",
        )

    report = build_match_report(get_poisson(), p_home_team, p_away_team, neutral=True)
    pred = get_poisson().predict(p_home_team, p_away_team, neutral=True)

    st.markdown(f"### {with_flag(p_home_team)} vs {with_flag(p_away_team)}")

    pm1, pm2, pm3 = st.columns(3)
    pm1.metric(with_flag(p_home_team), f"{report.p_home * 100:.1f}%", "gana")
    pm2.metric("Empate", f"{report.p_draw * 100:.1f}%")
    pm3.metric(with_flag(p_away_team), f"{report.p_away * 100:.1f}%", "gana")

    st.markdown("**Goles esperados (xG)**")
    st.altair_chart(
        xg_bars(with_flag(p_home_team), with_flag(p_away_team), report.xg_home, report.xg_away),
        width="stretch",
    )

    st.markdown("**Mapa de calor de marcadores**")
    st.altair_chart(
        scoreline_heatmap(pred.score_matrix, with_flag(p_home_team), with_flag(p_away_team)),
        width="stretch",
    )

    st.markdown("**Marcadores más probables**")
    for (i, j), p in top_scorelines(pred.score_matrix, 5):
        st.markdown(
            f"<div class='scoreline'>{with_flag(p_home_team)} <b>{i}–{j}</b> "
            f"{with_flag(p_away_team)} · {p * 100:.1f}%</div>",
            unsafe_allow_html=True,
        )

    st.markdown("**Mercados derivados**")
    st.altair_chart(markets_bars(report.btts, report.over25, report.over15), width="stretch")

    st.markdown(
        f"<div class='fav'>🃏 Conclusión del oráculo: {prode_verdict(report)}</div>",
        unsafe_allow_html=True,
    )

    # Formaciones (solo dentro de ~T-30 y si hay API key). No cambian el número.
    p_lineups = None
    st.markdown("#### 🧩 Formaciones")
    if candidatos:
        if not _apifootball_token():
            st.caption(
                "ℹ️ Agregá `API_FOOTBALL_KEY` en `.streamlit/secrets.toml` para ver el XI "
                "confirmado (entra ~30 min antes del partido)."
            )
        elif chosen["readiness"] in LINEUP_READY:
            p_lineups = _lineups_for(p_home_team, p_away_team, chosen["kickoff"].date().isoformat())
            if p_lineups:
                st.success("Formación confirmada (T-30) ✅")
                _render_lineups(p_home_team, p_away_team, p_lineups)
            else:
                st.caption("Formación todavía no publicada por la fuente (reintentá cerca del inicio).")
        else:
            st.caption("Formación oficial ~30 min antes del partido (modo *probable* por ahora).")
    else:
        st.caption("Elegí un partido del fixture para intentar traer las formaciones.")

    st.markdown("#### 🔍 Análisis por pilares")
    st.markdown(
        '<p class="caption">📊 = respaldado por datos · 🔮 = estimación (sin datos de jugadores).</p>',
        unsafe_allow_html=True,
    )
    _render_pillars(
        _build_pillars(
            p_home_team, p_away_team,
            referee=p_referee, referee_country=p_referee_country, lineups=p_lineups,
        )
    )


# --------------------------------------------------------------------------- #
# Vista: Predicción del Mundial
# --------------------------------------------------------------------------- #
with tab_cup:
    st.subheader("El sobre del Mundial 2026")
    c1, c2 = st.columns([3, 1])
    n_iter = c1.slider("Simulaciones", 200, 10000, 2000, step=200)
    st.markdown(
        '<p class="caption">Más sobres abiertos = más preciso pero más lento. Semilla fija.</p>',
        unsafe_allow_html=True,
    )
    usar_jugados = st.toggle(
        "Tener en cuenta los partidos ya jugados", value=True,
        help="Fija los resultados reales del Mundial y simula solo lo que falta.",
    )
    known_items = _played_known_items() if usar_jugados else ()
    if usar_jugados:
        st.caption(f"Partidos reales ya incorporados: {len(known_items)}")
    if c2.button("¡Abrí el sobre! 📦", width="stretch", type="primary"):
        with st.spinner(f"Abriendo {n_iter:,} sobres..."):
            probs = champion_probs(n_iter, known_items)
        ranking = sorted(get_config().teams, key=lambda t: probs[t]["Champion"], reverse=True)
        fav = ranking[0]
        st.markdown(
            f"<div class='fav'>🏅 La figu dorada es para <b>{with_flag(fav)}</b> · "
            f"{probs[fav]['Champion'] * 100:.1f}% de ser campeón</div>",
            unsafe_allow_html=True,
        )
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        df = pd.DataFrame(
            [
                {
                    "Equipo": f"{medals.get(i, '')} {with_flag(t)}".strip(),
                    "Campeón": probs[t]["Champion"] * 100,
                    "Final": probs[t]["Final"] * 100,
                    "Semis": probs[t]["SF"] * 100,
                }
                for i, t in enumerate(ranking)
            ]
        )
        top = df.head(12)
        st.altair_chart(
            ranking_bar(top, value="Campeón", title="Probabilidad de campeón (%)"),
            width="stretch",
        )
        st.markdown("**Camino al título (Semis / Final / Campeón)**")
        prog = df.head(8)[["Equipo", "Semis", "Final", "Campeón"]]
        st.altair_chart(progression_bars(prog), width="stretch")
        st.dataframe(
            df.style.format({"Campeón": "{:.1f}%", "Final": "{:.1f}%", "Semis": "{:.1f}%"}),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Elegí cuántos sobres abrir y apretá **¡Abrí el sobre! 📦**.")


# --------------------------------------------------------------------------- #
# Vista: Cuadro por fase
# --------------------------------------------------------------------------- #
with tab_bracket:
    st.subheader("El cuadro, fase por fase")
    st.markdown(
        '<p class="caption">Cada cruce real del Mundial con su predicción; si ya se '
        'jugó, el resultado y si el oráculo acertó.</p>',
        unsafe_allow_html=True,
    )
    try:
        fixtures, _ = get_fixtures()
    except LiveDataError:
        fixtures = []
    if fixtures:
        model = get_frozen()
        for fase, fs in group_by_phase(fixtures).items():
            with st.expander(f"{fase}  ·  {len(fs)} partidos", expanded=(fase == "Grupos")):
                for f in sorted(fs, key=lambda x: x.kickoff_utc):
                    if not f.resolved:
                        st.markdown(
                            "<div class='scoreline'>⏳ Por definirse</div>",
                            unsafe_allow_html=True,
                        )
                        continue
                    pred = model.predict(f.home, f.away, neutral=True)
                    if f.is_finished and not f.has_score:
                        st.markdown(
                            f"<div class='scoreline'>✔️ {with_flag(f.home)} vs "
                            f"{with_flag(f.away)} · finalizado (sin datos de marcador)</div>",
                            unsafe_allow_html=True,
                        )
                    elif f.has_score:
                        s = score_match(f.id, pred.probs, f.home_goals, f.away_goals)
                        mark = "✅" if s.hit else "❌"
                        top5 = top_scorelines(pred.score_matrix, 5)
                        if scoreline_hit(pred.score_matrix, f.home_goals, f.away_goals, n=5):
                            puesto = next(
                                k for k, ((i, j), _) in enumerate(top5, start=1)
                                if i == f.home_goals and j == f.away_goals
                            )
                            marcador_txt = f"🎯 marcador entre los probables (#{puesto})"
                        else:
                            (pi, pj), _ = top5[0]
                            marcador_txt = f"marcador fuera del top-5 (más probable {pi}–{pj})"
                        st.markdown(
                            f"<div class='scoreline'>{mark} {with_flag(f.home)} "
                            f"<b>{f.home_goals}–{f.away_goals}</b> {with_flag(f.away)} "
                            f"· predicho {s.outcome_pred} · {marcador_txt}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        fav = f.home if pred.p_home >= pred.p_away else f.away
                        st.markdown(
                            f"<div class='scoreline'>🔮 {with_flag(f.home)} vs {with_flag(f.away)} "
                            f"· favorito: <b>{display_name(fav)}</b> "
                            f"({max(pred.p_home, pred.p_away) * 100:.0f}%)</div>",
                            unsafe_allow_html=True,
                        )
    else:
        st.info("El cuadro se arma con los fixtures de la API (configurá tu token).")


# --------------------------------------------------------------------------- #
# Vista: Verificación
# --------------------------------------------------------------------------- #
with tab_verify:
    st.subheader("¿Cuánto le acierta el oráculo?")
    st.markdown(
        '<p class="caption">Métricas sobre los partidos YA jugados del Mundial. '
        'El modelo está congelado al inicio del torneo (sin data leakage).</p>',
        unsafe_allow_html=True,
    )
    try:
        fixtures, _ = get_fixtures()
    except LiveDataError:
        fixtures = []
    model = get_frozen()
    scores = []
    home_pairs = []
    for f in finished_rows(fixtures):
        pred = model.predict(f["home"], f["away"], neutral=True)
        scores.append(score_match(f["id"], pred.probs, f["home_goals"], f["away_goals"]))
        home_pairs.append((pred.p_home, f["home_goals"] > f["away_goals"]))

    if scores:
        summ = aggregate(scores)
        c1, c2, c3 = st.columns(3)
        c1.metric("Aciertos 1X2", f"{summ.hit_rate * 100:.0f}%")
        c2.metric("Brier medio", f"{summ.mean_brier:.3f}")
        c3.metric("RPS medio", f"{summ.mean_rps:.3f}")
        bins = calibration_bins(home_pairs, n_bins=5)
        cdf = pd.DataFrame(
            [{"predicted": b.predicted, "observed": b.observed, "n": b.n} for b in bins if b.n]
        )
        if not cdf.empty:
            st.markdown("#### Calibración (P(gana local) predicha vs real)")
            st.altair_chart(calibration_chart(cdf), width="stretch")
        st.markdown("#### Evolución del acierto (RPS por partido)")
        rps_df = pd.DataFrame([{"n": k + 1, "rps": s.rps} for k, s in enumerate(scores)])
        st.altair_chart(rps_line(rps_df), width="stretch")
    else:
        st.info("Todavía no hay partidos jugados para verificar.")

    st.divider()
    st.markdown("#### Backtest histórico (walk-forward desde 2010)")
    st.markdown(
        '<p class="caption">RPS más bajo = mejor. La <b>vara</b> es el modelo uniforme; '
        'cada nivel debe bajarla.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Revisar el álbum 📖", type="primary"):
        with st.spinner("Backtesteando uniforme, Elo y Poisson..."):
            metrics = model_metrics()
        mdf = pd.DataFrame([{"Modelo": k, **v} for k, v in metrics.items()]).sort_values("RPS")
        cols = st.columns(3)
        for col, (_, row) in zip(cols, mdf.iterrows()):
            col.metric(row["Modelo"].capitalize(), f"RPS {row['RPS']:.4f}")
        st.dataframe(
            mdf.style.format({"RPS": "{:.4f}", "Brier": "{:.4f}", "LogLoss": "{:.4f}"}),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Apretá **Revisar el álbum 📖** (tarda unos segundos la primera vez).")


st.markdown(
    "<div class='footer'>OlorACulo · álbum del Mundial 2026 · datos: martj42/international_results · "
    "modelo Poisson + Dixon-Coles · "
    "<a href='https://github.com/Toto2980/OlorACulo' target='_blank'>código en GitHub</a></div>",
    unsafe_allow_html=True,
)
