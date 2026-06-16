import numpy as np
import pandas as pd
import altair as alt

from app.charts import (
    win_prob_bar,
    ranking_bar,
    calibration_chart,
    scoreline_heatmap,
    xg_bars,
    markets_bars,
    progression_bars,
    rps_line,
)


def test_win_prob_bar_builds():
    ch = win_prob_bar("Argentina", "Brazil", 0.6, 0.25, 0.15)
    assert isinstance(ch, alt.LayerChart) or isinstance(ch, alt.Chart)


def test_ranking_bar_builds():
    df = pd.DataFrame({"Equipo": ["A", "B"], "Valor": [10, 5]})
    ch = ranking_bar(df, value="Valor", title="x")
    assert isinstance(ch, alt.Chart) or hasattr(ch, "to_dict")


def test_calibration_chart_builds():
    df = pd.DataFrame({"predicted": [0.2, 0.8], "observed": [0.1, 0.9], "n": [3, 4]})
    ch = calibration_chart(df)
    assert hasattr(ch, "to_dict")


def test_scoreline_heatmap_builds():
    m = np.full((11, 11), 1.0 / 121)
    ch = scoreline_heatmap(m, "Argentina", "Brazil", max_goals=5)
    assert hasattr(ch, "to_dict")


def test_xg_bars_builds():
    ch = xg_bars("Argentina", "Brazil", 1.4, 0.9)
    assert hasattr(ch, "to_dict")


def test_markets_bars_builds():
    ch = markets_bars(0.41, 0.38, 0.67)
    assert hasattr(ch, "to_dict")


def test_progression_bars_builds():
    df = pd.DataFrame(
        {"Equipo": ["A", "B"], "Semis": [30.0, 28.0], "Final": [18.0, 16.0], "Campeón": [10.0, 9.0]}
    )
    ch = progression_bars(df)
    assert hasattr(ch, "to_dict")


def test_rps_line_builds():
    df = pd.DataFrame({"n": [1, 2, 3], "rps": [0.2, 0.18, 0.21]})
    ch = rps_line(df)
    assert hasattr(ch, "to_dict")
