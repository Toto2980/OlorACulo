from __future__ import annotations

import altair as alt
import pandas as pd

# Paleta "Álbum '86" (alineada con streamlit_app.py)
GREEN = "#3c7a4e"
ORANGE = "#e8a33d"
MUTED = "#c9bfa3"
INK = "#2b2b2b"
RED = "#e84f3d"


def win_prob_bar(home: str, away: str, p_home: float, p_draw: float, p_away: float) -> alt.Chart:
    df = pd.DataFrame(
        {
            "Resultado": [f"Gana {home}", "Empate", f"Gana {away}"],
            "Probabilidad": [p_home, p_draw, p_away],
            "orden": [0, 1, 2],
        }
    )
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Probabilidad:Q", stack="normalize", axis=alt.Axis(format="%"), title=None),
            color=alt.Color(
                "Resultado:N",
                scale=alt.Scale(
                    domain=[f"Gana {home}", "Empate", f"Gana {away}"],
                    range=[GREEN, MUTED, ORANGE],
                ),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            order=alt.Order("orden:Q"),
            tooltip=["Resultado", alt.Tooltip("Probabilidad:Q", format=".1%")],
        )
        .properties(height=84)
    )


def ranking_bar(df: pd.DataFrame, *, value: str, title: str, label: str = "Equipo") -> alt.Chart:
    bars = (
        alt.Chart(df)
        .mark_bar(color=GREEN, cornerRadiusEnd=5)
        .encode(
            x=alt.X(f"{value}:Q", title=title),
            y=alt.Y(f"{label}:N", sort="-x", title=None),
            tooltip=[alt.Tooltip(f"{value}:Q", format=".1f")],
        )
    )
    text = bars.mark_text(align="left", dx=4, color=INK, fontWeight="bold").encode(
        text=alt.Text(f"{value}:Q", format=".1f")
    )
    return (bars + text).properties(height=30 * len(df) + 40)


def calibration_chart(df: pd.DataFrame) -> alt.LayerChart:
    """df: columnas predicted, observed, n. Dibuja la curva vs la diagonal ideal."""
    diag = (
        alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]}))
        .mark_line(strokeDash=[5, 5], color=MUTED)
        .encode(x="x:Q", y="y:Q")
    )
    pts = (
        alt.Chart(df)
        .mark_circle(color=ORANGE, size=120)
        .encode(
            x=alt.X("predicted:Q", title="Probabilidad predicha", scale=alt.Scale(domain=[0, 1])),
            y=alt.Y("observed:Q", title="Frecuencia real", scale=alt.Scale(domain=[0, 1])),
            size=alt.Size("n:Q", legend=None),
            tooltip=["predicted", "observed", "n"],
        )
    )
    return (diag + pts).properties(height=300)


def scoreline_heatmap(matrix, home: str, away: str, max_goals: int = 5) -> alt.Chart:
    """Grilla de calor goles local × goles visitante."""
    n = min(max_goals + 1, matrix.shape[0])
    m = min(max_goals + 1, matrix.shape[1])
    rows = [
        {"local": i, "visita": j, "p": float(matrix[i, j])}
        for i in range(n)
        for j in range(m)
    ]
    df = pd.DataFrame(rows)
    return (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("visita:O", title=f"Goles {away}"),
            y=alt.Y("local:O", title=f"Goles {home}", sort="descending"),
            color=alt.Color("p:Q", scale=alt.Scale(scheme="yelloworangered"), legend=None),
            tooltip=[
                alt.Tooltip("local:O", title=f"{home}"),
                alt.Tooltip("visita:O", title=f"{away}"),
                alt.Tooltip("p:Q", format=".1%", title="Prob"),
            ],
        )
        .properties(height=260)
    )


def xg_bars(home: str, away: str, xg_home: float, xg_away: float) -> alt.LayerChart:
    """Barras cara a cara de goles esperados (xG)."""
    df = pd.DataFrame({"Equipo": [home, away], "xG": [xg_home, xg_away], "orden": [0, 1]})
    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X("xG:Q", title="Goles esperados (xG)"),
            y=alt.Y("Equipo:N", sort=alt.SortField("orden"), title=None),
            color=alt.Color(
                "Equipo:N",
                scale=alt.Scale(domain=[home, away], range=[GREEN, ORANGE]),
                legend=None,
            ),
            tooltip=[alt.Tooltip("xG:Q", format=".2f")],
        )
    )
    text = bars.mark_text(align="left", dx=4, color=INK, fontWeight="bold").encode(
        text=alt.Text("xG:Q", format=".2f")
    )
    return (bars + text).properties(height=110)


def markets_bars(btts: float, over25: float, over15: float) -> alt.LayerChart:
    """Barras de probabilidad de los mercados derivados."""
    df = pd.DataFrame(
        {
            "Mercado": ["Ambos marcan", "Over 2.5", "Over 1.5"],
            "Probabilidad": [btts, over25, over15],
            "orden": [0, 1, 2],
        }
    )
    bars = (
        alt.Chart(df)
        .mark_bar(color=ORANGE, cornerRadiusEnd=5)
        .encode(
            x=alt.X(
                "Probabilidad:Q",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1]),
                title=None,
            ),
            y=alt.Y("Mercado:N", sort=alt.SortField("orden"), title=None),
            tooltip=[alt.Tooltip("Probabilidad:Q", format=".0%")],
        )
    )
    text = bars.mark_text(align="left", dx=4, color=INK, fontWeight="bold").encode(
        text=alt.Text("Probabilidad:Q", format=".0%")
    )
    return (bars + text).properties(height=120)


def progression_bars(df: pd.DataFrame) -> alt.Chart:
    """Barras agrupadas por equipo: chance de Semis / Final / Campeón.
    df: columnas Equipo, Semis, Final, Campeón (en %)."""
    long = df.melt(
        id_vars="Equipo",
        value_vars=["Semis", "Final", "Campeón"],
        var_name="Fase",
        value_name="Probabilidad",
    )
    return (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("Probabilidad:Q", title="Probabilidad (%)"),
            y=alt.Y("Equipo:N", sort="-x", title=None),
            yOffset="Fase:N",
            color=alt.Color(
                "Fase:N",
                scale=alt.Scale(domain=["Semis", "Final", "Campeón"], range=[GREEN, ORANGE, RED]),
                legend=alt.Legend(orient="bottom", title=None),
            ),
            tooltip=["Equipo", "Fase", alt.Tooltip("Probabilidad:Q", format=".1f")],
        )
        .properties(height=34 * len(df) + 60)
    )


def rps_line(df: pd.DataFrame) -> alt.Chart:
    """Evolución del RPS partido a partido (menos es mejor).
    df: columnas n, rps."""
    return (
        alt.Chart(df)
        .mark_line(color=GREEN, point=alt.OverlayMarkDef(color=RED, size=60))
        .encode(
            x=alt.X("n:Q", title="Partido jugado", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("rps:Q", title="RPS (menos es mejor)"),
            tooltip=[alt.Tooltip("n:Q", title="Partido"), alt.Tooltip("rps:Q", format=".3f")],
        )
        .properties(height=240)
    )
