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

import pandas as pd
import streamlit as st

from oraculo.ingest.results import load_results
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.tournament.config import load_config
from oraculo.tournament.tournament import run_tournament_mc
from app.services import top_scorelines, model_comparison

DATA = ROOT / "data" / "results.csv"
WC = ROOT / "data" / "wc2026.yaml"
EVAL_FROM = datetime.date(2010, 1, 1)


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


st.set_page_config(page_title="OlorACulo — Mundial 2026", page_icon="⚽")
st.title("⚽ OlorACulo — Predictor del Mundial 2026")

teams = sorted(get_config().teams)
view = st.sidebar.radio(
    "Vista",
    ["Analizar partido", "Predicción del Mundial", "Comparar equipos", "Métricas del modelo"],
)

if view == "Analizar partido":
    st.header("Analizar un partido")
    c1, c2 = st.columns(2)
    home = c1.selectbox("Equipo 1", teams, index=teams.index("Argentina"))
    away = c2.selectbox("Equipo 2", teams, index=teams.index("Brazil"))
    neutral = st.checkbox("Cancha neutral", value=True)
    model_name = st.radio("Modelo", ["Poisson", "Elo"], horizontal=True)
    model = get_poisson() if model_name == "Poisson" else get_elo()

    pred = model.predict(home, away, neutral=neutral)
    cols = st.columns(3)
    cols[0].metric(f"Gana {home}", f"{pred.p_home * 100:.1f}%")
    cols[1].metric("Empate", f"{pred.p_draw * 100:.1f}%")
    cols[2].metric(f"Gana {away}", f"{pred.p_away * 100:.1f}%")

    probs_df = pd.DataFrame(
        {"Probabilidad": [pred.p_home, pred.p_draw, pred.p_away]},
        index=[f"Gana {home}", "Empate", f"Gana {away}"],
    )
    st.bar_chart(probs_df)

    if pred.xg_home is not None:
        st.write(f"**Goles esperados:** {home} {pred.xg_home:.2f} – {pred.xg_away:.2f} {away}")
        st.subheader("Marcadores más probables")
        for (i, j), p in top_scorelines(pred.score_matrix, 5):
            st.write(f"- {home} **{i}–{j}** {away} · {p * 100:.1f}%")

if view == "Predicción del Mundial":
    st.header("Predicción del Mundial 2026")
    n_iter = st.slider("Simulaciones", 200, 10000, 2000, step=200)
    if st.button("Simular el Mundial 🏆"):
        with st.spinner(f"Corriendo {n_iter} simulaciones..."):
            probs = champion_probs(n_iter)
        ranking = sorted(get_config().teams, key=lambda t: probs[t]["Champion"], reverse=True)
        df = pd.DataFrame(
            [
                {
                    "Equipo": t,
                    "Campeón %": round(probs[t]["Champion"] * 100, 1),
                    "Final %": round(probs[t]["Final"] * 100, 1),
                    "Semi %": round(probs[t]["SF"] * 100, 1),
                }
                for t in ranking
            ]
        )
        st.subheader("Probabilidad de ser campeón (top 12)")
        st.bar_chart(df.head(12).set_index("Equipo")["Campeón %"])
        st.dataframe(df, hide_index=True, use_container_width=True)

if view == "Comparar equipos":
    st.header("Comparar equipos")
    sel = st.multiselect("Equipos", teams, default=["Argentina", "Brazil", "France", "Spain"])
    poi = get_poisson()
    elo = get_elo()
    rows = [
        {
            "Equipo": t,
            "Elo": round(elo.rating(t)),
            "Ataque (Poisson)": round(poi.attack.get(t, 0.0), 2),
            "Defensa (Poisson)": round(poi.defense.get(t, 0.0), 2),
        }
        for t in sel
    ]
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.bar_chart(df.set_index("Equipo")["Elo"])

if view == "Métricas del modelo":
    st.header("Métricas del modelo (backtest desde 2010)")
    st.write("RPS más bajo = mejor. La **vara** es el modelo uniforme; cada nivel debe bajarla.")
    metrics = model_metrics()
    df = pd.DataFrame(
        [{"Modelo": k, **v} for k, v in metrics.items()]
    ).sort_values("RPS")
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.bar_chart(df.set_index("Modelo")["RPS"])
