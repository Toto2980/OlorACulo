from __future__ import annotations

import altair as alt
import pandas as pd

# Paleta "Álbum '86" (alineada con streamlit_app.py)
GREEN = "#3c7a4e"
ORANGE = "#e8a33d"
MUTED = "#c9bfa3"
INK = "#2b2b2b"


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
