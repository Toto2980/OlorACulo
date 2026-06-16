import pandas as pd
import altair as alt

from app.charts import win_prob_bar, ranking_bar, calibration_chart


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
