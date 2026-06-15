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
from app.services import top_scorelines, model_comparison
from app.flags import with_flag

DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"
EVAL_FROM = datetime.date(2010, 1, 1)

ACCENT = "#00C2A8"
ACCENT_2 = "#F4B740"
MUTED = "#8A94A6"


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


@st.cache_data
def champion_probs(n_iter: int):
    return run_tournament_mc(get_poisson(), get_config(), n_iter=n_iter)


@st.cache_data
def model_metrics():
    res = model_comparison(get_matches(), EVAL_FROM)
    return {k: {"RPS": v.rps, "Brier": v.brier, "LogLoss": v.log_loss} for k, v in res.items()}


# --------------------------------------------------------------------------- #
# Estilo
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="OlorACulo — Mundial 2026", page_icon="⚽", layout="wide")

st.markdown(
    """
    <style>
      #MainMenu, footer, header {visibility: hidden;}
      .block-container {padding-top: 1.5rem; max-width: 1180px;}
      .hero {
        background: linear-gradient(135deg, #0b3d2e 0%, #0e7a5f 55%, #00c2a8 130%);
        border-radius: 18px; padding: 26px 32px; margin-bottom: 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,.35);
      }
      .hero h1 {color: #fff; margin: 0; font-size: 2.2rem; letter-spacing: -.5px;}
      .hero p {color: #cdeede; margin: .35rem 0 0; font-size: 1.02rem;}
      .pill {display:inline-block; background: rgba(255,255,255,.14); color:#eafff8;
        padding: 2px 12px; border-radius: 999px; font-size:.78rem; margin-top:10px;}
      div[data-testid="stMetric"] {
        background: #161B26; border: 1px solid #232a39; border-radius: 14px;
        padding: 14px 16px;
      }
      .stTabs [data-baseweb="tab-list"] {gap: 6px;}
      .stTabs [data-baseweb="tab"] {
        background:#161B26; border-radius: 10px 10px 0 0; padding: 8px 18px;
      }
      .stTabs [aria-selected="true"] {background:#1f2735; color:#fff;}
      .caption {color:#8A94A6; font-size:.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>⚽ OlorACulo</h1>
      <p>Predictor del Mundial 2026 — del oloráculo inútil al Monte Carlo, por niveles.</p>
      <span class="pill">Modelo Poisson · Dixon-Coles · 49.000 partidos de historia</span>
    </div>
    """,
    unsafe_allow_html=True,
)

teams = sorted(get_config().teams)

tab_match, tab_cup, tab_teams, tab_metrics = st.tabs(
    ["⚽  Partido", "🏆  Mundial", "📊  Equipos", "🎯  Métricas"]
)


# --------------------------------------------------------------------------- #
# Vista: Analizar partido
# --------------------------------------------------------------------------- #
with tab_match:
    st.subheader("Analizar un partido")
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

    outcomes = pd.DataFrame(
        {
            "Resultado": [f"Gana {home}", "Empate", f"Gana {away}"],
            "Probabilidad": [pred.p_home, pred.p_draw, pred.p_away],
        }
    )
    chart = (
        alt.Chart(outcomes)
        .mark_bar(cornerRadiusEnd=6, size=34)
        .encode(
            x=alt.X("Probabilidad:Q", axis=alt.Axis(format="%"), title=None),
            y=alt.Y("Resultado:N", sort=None, title=None),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(range=[ACCENT, MUTED, ACCENT_2]),
                legend=None,
            ),
            tooltip=[alt.Tooltip("Probabilidad:Q", format=".1%")],
        )
        .properties(height=180)
    )
    st.altair_chart(chart, use_container_width=True)

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
                st.markdown(f"{with_flag(home)} **{i}–{j}** {with_flag(away)} · `{p * 100:.1f}%`")


# --------------------------------------------------------------------------- #
# Vista: Predicción del Mundial
# --------------------------------------------------------------------------- #
with tab_cup:
    st.subheader("Predicción del Mundial 2026")
    c1, c2 = st.columns([3, 1])
    n_iter = c1.slider("Simulaciones", 200, 10000, 2000, step=200)
    st.markdown(
        '<p class="caption">Más simulaciones = más preciso pero más lento. Semilla fija.</p>',
        unsafe_allow_html=True,
    )
    if c2.button("Simular 🏆", use_container_width=True, type="primary"):
        with st.spinner(f"Corriendo {n_iter:,} torneos..."):
            probs = champion_probs(n_iter)
        ranking = sorted(get_config().teams, key=lambda t: probs[t]["Champion"], reverse=True)
        df = pd.DataFrame(
            [
                {
                    "Equipo": with_flag(t),
                    "Campeón": probs[t]["Champion"] * 100,
                    "Final": probs[t]["Final"] * 100,
                    "Semis": probs[t]["SF"] * 100,
                }
                for t in ranking
            ]
        )
        top = df.head(12)
        bars = (
            alt.Chart(top)
            .mark_bar(color=ACCENT, cornerRadiusEnd=5)
            .encode(
                x=alt.X("Campeón:Q", title="Probabilidad de campeón (%)"),
                y=alt.Y("Equipo:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("Campeón:Q", format=".1f")],
            )
        )
        labels = bars.mark_text(align="left", dx=4, color="#E6E9EF").encode(
            text=alt.Text("Campeón:Q", format=".1f")
        )
        st.altair_chart((bars + labels).properties(height=420), use_container_width=True)
        st.dataframe(
            df.style.format({"Campeón": "{:.1f}%", "Final": "{:.1f}%", "Semis": "{:.1f}%"}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Elegí la cantidad de simulaciones y apretá **Simular 🏆**.")


# --------------------------------------------------------------------------- #
# Vista: Comparar equipos
# --------------------------------------------------------------------------- #
with tab_teams:
    st.subheader("Comparar equipos")
    sel = st.multiselect(
        "Equipos", teams, default=["Argentina", "Brazil", "France", "Spain"], format_func=with_flag
    )
    if sel:
        poi = get_poisson()
        elo = get_elo()
        df = pd.DataFrame(
            [
                {
                    "Equipo": with_flag(t),
                    "Elo": round(elo.rating(t)),
                    "Ataque": round(poi.attack.get(t, 0.0), 2),
                    "Defensa": round(poi.defense.get(t, 0.0), 2),
                }
                for t in sel
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
        chart = (
            alt.Chart(df)
            .mark_bar(color=ACCENT_2, cornerRadiusEnd=5)
            .encode(
                x=alt.X("Elo:Q", scale=alt.Scale(zero=False), title="Rating Elo"),
                y=alt.Y("Equipo:N", sort="-x", title=None),
                tooltip=["Equipo", "Elo"],
            )
            .properties(height=60 + 32 * len(df))
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Elegí al menos un equipo.")


# --------------------------------------------------------------------------- #
# Vista: Métricas del modelo
# --------------------------------------------------------------------------- #
with tab_metrics:
    st.subheader("Métricas del modelo")
    st.markdown(
        '<p class="caption">Backtest walk-forward desde 2010. RPS más bajo = mejor. '
        'La <b>vara</b> es el modelo uniforme; cada nivel debe bajarla.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Calcular métricas", type="primary"):
        with st.spinner("Backtesteando uniforme, Elo y Poisson..."):
            metrics = model_metrics()
        df = pd.DataFrame([{"Modelo": k, **v} for k, v in metrics.items()]).sort_values("RPS")
        cols = st.columns(3)
        for col, (_, row) in zip(cols, df.iterrows()):
            col.metric(row["Modelo"].capitalize(), f"RPS {row['RPS']:.4f}")
        chart = (
            alt.Chart(df)
            .mark_bar(color=ACCENT, cornerRadiusEnd=5)
            .encode(
                x=alt.X("RPS:Q", scale=alt.Scale(zero=False), title="RPS (menor = mejor)"),
                y=alt.Y("Modelo:N", sort="x", title=None),
                tooltip=[alt.Tooltip("RPS:Q", format=".4f")],
            )
            .properties(height=160)
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(
            df.style.format({"RPS": "{:.4f}", "Brier": "{:.4f}", "LogLoss": "{:.4f}"}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Apretá **Calcular métricas** (tarda unos segundos la primera vez).")
