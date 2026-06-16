# OlorACulo — Español + Gráficos + Prode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar la app 100% en español (nombres de equipos), sumar 5 gráficos Altair y una pestaña "Prode" con análisis pre-partido completo, sin tocar la capa de modelo/datos.

**Architecture:** Toda la traducción al español es una capa de *presentación* en `app/` (las claves de equipos siguen en inglés porque las usan el dataset, el modelo y los tests). Los gráficos son funciones puras que devuelven objetos Altair en `app/charts.py`. La pestaña Prode reutiliza `build_match_report()` y arma una conclusión determinística (sin LLM ni internet).

**Tech Stack:** Python 3.11, Streamlit, Altair, pandas, NumPy, pytest. Entorno: `.\.venv\Scripts\python.exe`.

**Rama:** `feat/prode-graficos-espanol` (ya creada).

**Spec:** `docs/superpowers/specs/2026-06-16-prode-graficos-espanol-design.md`

---

## File Structure

- `app/flags.py` — **modificar**: dict `ES_NAMES`, función `display_name`, `with_flag` usa nombre ES.
- `oraculo/report/match_report.py` — **modificar**: campo `over15` en `MatchReport` + cálculo en `build_match_report`.
- `app/services.py` — **modificar**: función `prode_verdict`.
- `app/charts.py` — **modificar**: 5 funciones de gráficos nuevas.
- `app/streamlit_app.py` — **modificar**: pestaña Prode + enchufar gráficos en Partido / Mundial / Verificación.
- Tests: `tests/test_app_flags.py` (nuevo), `tests/test_match_report.py`, `tests/test_app_services.py`, `tests/test_app_charts.py` (ampliar).

**Nota de comandos:** en Windows correr pytest con el python del venv. El AppTest necesita el token:
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:FOOTBALL_DATA_TOKEN="6b4c4b9d0bd541248e22a8e266000fe1"
```

---

## Task 1: Capa de display en español (nombres de equipos)

**Files:**
- Modify: `app/flags.py`
- Test: `tests/test_app_flags.py` (crear)

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_app_flags.py`:

```python
from app.flags import display_name, with_flag


def test_display_name_traduce_los_que_difieren():
    assert display_name("Brazil") == "Brasil"
    assert display_name("Spain") == "España"
    assert display_name("Germany") == "Alemania"
    assert display_name("England") == "Inglaterra"
    assert display_name("Netherlands") == "Países Bajos"


def test_display_name_deja_intactos_los_que_coinciden():
    assert display_name("Argentina") == "Argentina"
    assert display_name("Colombia") == "Colombia"


def test_display_name_equipo_desconocido_se_devuelve_igual():
    assert display_name("Wakanda") == "Wakanda"


def test_with_flag_usa_nombre_en_espanol():
    assert with_flag("Brazil") == "🇧🇷 Brasil"
    assert with_flag("Argentina") == "🇦🇷 Argentina"
    assert with_flag("Wakanda") == "⚽ Wakanda"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_flags.py -v`
Expected: FAIL con `ImportError: cannot import name 'display_name'`.

- [ ] **Step 3: Implementar `ES_NAMES` + `display_name` y actualizar `with_flag`**

En `app/flags.py`, debajo del dict `FLAGS` (antes de `with_flag`), agregar:

```python
# Nombre en español para mostrar. Solo los que difieren de la clave canónica
# (las claves siguen en inglés porque las usa el dataset/modelo/tests).
ES_NAMES: dict[str, str] = {
    "Mexico": "México",
    "South Africa": "Sudáfrica",
    "South Korea": "Corea del Sur",
    "Czech Republic": "Chequia",
    "Canada": "Canadá",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Qatar": "Catar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Scotland": "Escocia",
    "United States": "Estados Unidos",
    "Turkey": "Turquía",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Ivory Coast": "Costa de Marfil",
    "Netherlands": "Países Bajos",
    "Japan": "Japón",
    "Sweden": "Suecia",
    "Tunisia": "Túnez",
    "Belgium": "Bélgica",
    "Egypt": "Egipto",
    "Iran": "Irán",
    "New Zealand": "Nueva Zelanda",
    "Spain": "España",
    "Cape Verde": "Cabo Verde",
    "Saudi Arabia": "Arabia Saudita",
    "France": "Francia",
    "Iraq": "Irak",
    "Norway": "Noruega",
    "Algeria": "Argelia",
    "Jordan": "Jordania",
    "DR Congo": "RD Congo",
    "Uzbekistan": "Uzbekistán",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Panama": "Panamá",
}


def display_name(team: str) -> str:
    """Nombre en español para mostrar. Equipo sin traducción -> tal cual."""
    return ES_NAMES.get(team, team)
```

Reemplazar la función `with_flag` existente por:

```python
def with_flag(team: str) -> str:
    """'Brazil' -> '🇧🇷 Brasil'. Equipo desconocido -> '⚽ <team>'."""
    return f"{FLAGS.get(team, '⚽')} {display_name(team)}"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_flags.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```powershell
git add app/flags.py tests/test_app_flags.py
git commit -m "feat(ui): nombres de equipos en español (capa de display)"
```

---

## Task 2: Campo `over15` en MatchReport

**Files:**
- Modify: `oraculo/report/match_report.py`
- Test: `tests/test_match_report.py` (ampliar)

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_match_report.py`:

```python
def test_build_match_report_incluye_over15_y_es_mayor_que_over25():
    r = build_match_report(_model(), "Argentina", "Brazil", neutral=True)
    assert 0.0 <= r.over15 <= 1.0
    # P(total > 1.5) siempre >= P(total > 2.5)
    assert r.over15 >= r.over25
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_report.py::test_build_match_report_incluye_over15_y_es_mayor_que_over25 -v`
Expected: FAIL con `AttributeError: 'MatchReport' object has no attribute 'over15'`.

- [ ] **Step 3: Agregar el campo y su cálculo**

En `oraculo/report/match_report.py`, en el dataclass `MatchReport`, agregar el campo `over15` justo después de `over25`:

```python
    btts: float
    over25: float
    over15: float
    speculative: Speculative
```

En `build_match_report`, en la construcción del `MatchReport`, agregar `over15` después de `over25`:

```python
        btts=btts_prob(matrix),
        over25=over_prob(matrix, 2.5),
        over15=over_prob(matrix, 1.5),
        speculative=Speculative(
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_match_report.py -v`
Expected: PASS (todos, incluido el nuevo).

- [ ] **Step 5: Commit**

```powershell
git add oraculo/report/match_report.py tests/test_match_report.py
git commit -m "feat(report): agregar over15 a MatchReport"
```

---

## Task 3: `prode_verdict` (conclusión en lenguaje natural)

**Files:**
- Modify: `app/services.py`
- Test: `tests/test_app_services.py` (ampliar)

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_app_services.py` (junto a los imports existentes agregar `from app.services import prode_verdict` y `from oraculo.report.match_report import MatchReport, Speculative`):

```python
def _report(p_home, p_draw, p_away, over25, home="Argentina", away="Brazil"):
    return MatchReport(
        home=home, away=away,
        p_home=p_home, p_draw=p_draw, p_away=p_away,
        xg_home=1.5, xg_away=0.8,
        top_scores=[((1, 0), 0.12)],
        btts=0.4, over25=over25, over15=0.7,
        speculative=Speculative(top_scorer_team=home, cards_band="3–5"),
    )


def test_prode_verdict_favorito_claro_usa_nombre_es():
    txt = prode_verdict(_report(0.70, 0.20, 0.10, over25=0.30))
    assert "Brasil" in txt          # away traducido al español
    assert "favorito" in txt.lower()
    assert "%" in txt


def test_prode_verdict_cruce_parejo_lo_dice():
    txt = prode_verdict(_report(0.35, 0.33, 0.32, over25=0.50))
    assert "parejo" in txt.lower()


def test_prode_verdict_pocos_goles_cuando_over25_bajo():
    txt = prode_verdict(_report(0.70, 0.20, 0.10, over25=0.30))
    assert "pocos goles" in txt.lower()
```

Nota: con `p_home=0.70` el favorito es el **local** (Argentina); el test verifica que el texto nombra al rival en español ("Brasil") porque la conclusión menciona ambos. Ver implementación abajo.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_services.py -k prode_verdict -v`
Expected: FAIL con `ImportError: cannot import name 'prode_verdict'`.

- [ ] **Step 3: Implementar `prode_verdict`**

En `app/services.py`, agregar el import arriba:

```python
from app.flags import display_name
from oraculo.report.match_report import MatchReport
```

Y agregar la función al final del archivo:

```python
def prode_verdict(report: MatchReport) -> str:
    """Conclusión pre-partido en lenguaje natural a partir del MatchReport.
    Determinística (sin LLM ni internet)."""
    probs = {report.home: report.p_home, report.away: report.p_away}
    fav = max(probs, key=probs.get)
    rival = report.away if fav == report.home else report.home
    fav_p = probs[fav]
    spread = max(report.p_home, report.p_draw, report.p_away)

    if spread < 0.45:
        tono = (
            f"Cruce parejo entre {display_name(fav)} y {display_name(rival)}: "
            f"{display_name(fav)} apenas favorito ({fav_p * 100:.0f}%)."
        )
    else:
        tono = (
            f"{display_name(fav)} llega favorito ({fav_p * 100:.0f}%) "
            f"ante {display_name(rival)}."
        )

    if report.over25 >= 0.55:
        goles = f"Se esperan goles (Over 2.5 al {report.over25 * 100:.0f}%)."
    elif report.over25 <= 0.40:
        goles = f"Partido trabado, pocos goles (Over 2.5 al {report.over25 * 100:.0f}%)."
    else:
        goles = f"Los goles están en duda (Over 2.5 al {report.over25 * 100:.0f}%)."

    return f"{tono} {goles}"
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_services.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```powershell
git add app/services.py tests/test_app_services.py
git commit -m "feat(prode): conclusion pre-partido en lenguaje natural"
```

---

## Task 4: Cinco gráficos nuevos en `app/charts.py`

**Files:**
- Modify: `app/charts.py`
- Test: `tests/test_app_charts.py` (ampliar)

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_charts.py` (ampliar el import de arriba a
`from app.charts import win_prob_bar, ranking_bar, calibration_chart, scoreline_heatmap, xg_bars, markets_bars, progression_bars, rps_line` y agregar `import numpy as np`):

```python
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
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_charts.py -v`
Expected: FAIL con `ImportError: cannot import name 'scoreline_heatmap'`.

- [ ] **Step 3: Implementar las 5 funciones**

Agregar al final de `app/charts.py` (la paleta `GREEN`, `ORANGE`, `MUTED`, `INK` ya está definida arriba en el módulo). Agregar `RED = "#e84f3d"` junto a las constantes de color del principio del archivo:

```python
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
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_charts.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```powershell
git add app/charts.py tests/test_app_charts.py
git commit -m "feat(charts): heatmap, xG, mercados, progresion y RPS"
```

---

## Task 5: Pestaña "Prode" + enchufar gráficos en la UI

**Files:**
- Modify: `app/streamlit_app.py`

Esta tarea es de UI; se verifica con AppTest (la app levanta con 6 pestañas sin excepción) y revisión visual. No lleva test unitario propio.

- [ ] **Step 1: Actualizar imports y agregar la pestaña**

En `app/streamlit_app.py`, ampliar los imports de charts y services:

```python
from app.services import top_scorelines, model_comparison, prode_verdict
from app.flags import with_flag, display_name
from app.charts import (
    ranking_bar,
    calibration_chart,
    scoreline_heatmap,
    xg_bars,
    markets_bars,
    progression_bars,
    rps_line,
)
```

(Quitar el `from app.charts import ranking_bar, calibration_chart` y el `from app.flags import with_flag` viejos para no duplicar.)

Reemplazar la línea de tabs por seis pestañas:

```python
tab_live, tab_bracket, tab_match, tab_prode, tab_cup, tab_verify = st.tabs(
    ["🔴  En vivo", "🗺️  Cuadro", "⚽  Partido", "📋  Prode", "🏆  Mundial", "🎯  Verificación"]
)
```

- [ ] **Step 2: Enchufar gráficos nuevos en la pestaña Partido**

En el bloque `with tab_match:`, dentro del `if pred.xg_home is not None:`, después del bloque de "Marcadores más probables" y antes de `report = build_match_report(...)`, agregar el heatmap y las barras de xG:

```python
        st.markdown("**Mapa de calor de marcadores**")
        st.altair_chart(
            scoreline_heatmap(pred.score_matrix, with_flag(home), with_flag(away)),
            width="stretch",
        )
        st.altair_chart(xg_bars(with_flag(home), with_flag(away), pred.xg_home, pred.xg_away), width="stretch")
```

Y donde hoy muestra los mercados (`d1.metric("Ambos marcan (BTTS)"...)`), agregar debajo de esas métricas la barra de mercados:

```python
        st.altair_chart(markets_bars(report.btts, report.over25, report.over15), width="stretch")
```

En el mismo bloque, el goleador especulativo se muestra con nombre crudo en inglés. Reemplazar
`report.speculative.top_scorer_team` por `display_name(report.speculative.top_scorer_team)` en el
`st.markdown` del `caption` de "Estimación".

- [ ] **Step 3: Crear el bloque de la pestaña Prode**

Agregar un bloque nuevo `with tab_prode:` (por ejemplo después de `with tab_match:`). Código completo:

```python
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
    proximos = [r for r in upcoming_rows(fixtures, now=now) if "vs" in r["partido"]] if fixtures else []
    # Solo cruces con ambos equipos definidos y conocidos por el modelo.
    candidatos = []
    for r in proximos:
        partes = r["partido"].split(" vs ")
        if len(partes) == 2 and partes[0] in teams and partes[1] in teams:
            candidatos.append((r["fase"], partes[0], partes[1], r["kickoff"]))

    if candidatos:
        labels = [
            f"{fase} · {with_flag(h)} vs {with_flag(a)} · {ko:%d/%m %H:%M} UTC"
            for (fase, h, a, ko) in candidatos
        ]
        idx = st.selectbox("Partido del Mundial", range(len(labels)), format_func=lambda i: labels[i])
        fase, p_home_team, p_away_team, _ = candidatos[idx]
        st.caption(f"Fase: {fase}")
    else:
        st.info("No hay próximos partidos del fixture; elegí dos equipos.")
        cc1, cc2 = st.columns(2)
        p_home_team = cc1.selectbox("Equipo 1", teams, index=teams.index("Argentina"), format_func=with_flag, key="prode_home")
        p_away_team = cc2.selectbox("Equipo 2", teams, index=teams.index("Brazil"), format_func=with_flag, key="prode_away")

    report = build_match_report(get_poisson(), p_home_team, p_away_team, neutral=True)
    pred = get_poisson().predict(p_home_team, p_away_team, neutral=True)

    st.markdown(f"### {with_flag(p_home_team)} vs {with_flag(p_away_team)}")

    pm1, pm2, pm3 = st.columns(3)
    pm1.metric(with_flag(p_home_team), f"{report.p_home * 100:.1f}%", "gana")
    pm2.metric("Empate", f"{report.p_draw * 100:.1f}%")
    pm3.metric(with_flag(p_away_team), f"{report.p_away * 100:.1f}%", "gana")

    st.markdown("**Goles esperados (xG)**")
    st.altair_chart(xg_bars(with_flag(p_home_team), with_flag(p_away_team), report.xg_home, report.xg_away), width="stretch")

    st.markdown("**Mapa de calor de marcadores**")
    st.altair_chart(scoreline_heatmap(pred.score_matrix, with_flag(p_home_team), with_flag(p_away_team)), width="stretch")

    st.markdown("**Marcadores más probables**")
    for (i, j), p in top_scorelines(pred.score_matrix, 5):
        st.markdown(
            f"<div class='scoreline'>{with_flag(p_home_team)} <b>{i}–{j}</b> {with_flag(p_away_team)} "
            f"· {p * 100:.1f}%</div>",
            unsafe_allow_html=True,
        )

    st.markdown("**Mercados derivados**")
    st.altair_chart(markets_bars(report.btts, report.over25, report.over15), width="stretch")

    st.markdown(
        f"<div class='fav'>🃏 Conclusión del oráculo: {prode_verdict(report)}</div>",
        unsafe_allow_html=True,
    )
```

- [ ] **Step 3b: Traducir el favorito del Cuadro**

En el bloque `with tab_bracket:`, el favorito de un cruce no jugado se muestra con nombre crudo
(`favorito: <b>{fav}</b>`). Reemplazar `<b>{fav}</b>` por `<b>{display_name(fav)}</b>` en ese
`st.markdown`.

- [ ] **Step 4: Enchufar `progression_bars` en la pestaña Mundial**

En el bloque `with tab_cup:`, después del `st.altair_chart(ranking_bar(...))` existente y antes del `st.dataframe(...)`, agregar (usa el `df` ya construido, que tiene columnas Campeón/Final/Semis; reusar las primeras 8 filas):

```python
        st.markdown("**Camino al título (Semis / Final / Campeón)**")
        prog = df.head(8)[["Equipo", "Semis", "Final", "Campeón"]]
        st.altair_chart(progression_bars(prog), width="stretch")
```

- [ ] **Step 5: Enchufar `rps_line` en la pestaña Verificación**

En el bloque `with tab_verify:`, dentro del `if scores:`, después del gráfico de calibración, agregar la evolución del RPS:

```python
        st.markdown("#### Evolución del acierto (RPS por partido)")
        rps_df = pd.DataFrame(
            [{"n": k + 1, "rps": s.rps} for k, s in enumerate(scores)]
        )
        st.altair_chart(rps_line(rps_df), width="stretch")
```

- [ ] **Step 6: Verificar con AppTest (6 pestañas, sin excepción)**

Run:
```powershell
$env:PYTHONIOENCODING="utf-8"; $env:FOOTBALL_DATA_TOKEN="6b4c4b9d0bd541248e22a8e266000fe1"; .\.venv\Scripts\python.exe -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app/streamlit_app.py', default_timeout=90); at.run(); assert not at.exception; print('OK', len(at.tabs))"
```
Expected: `OK 6` y sin excepción.

- [ ] **Step 7: Correr la suite completa**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos verdes (132 previos + nuevos).

- [ ] **Step 8: Revisión visual**

Run: `.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py`
Abrir http://localhost:8501 y verificar: nombres en español, pestaña Prode con sus gráficos, heatmap/xG/mercados en Partido, camino al título en Mundial, RPS en Verificación.

- [ ] **Step 9: Commit**

```powershell
git add app/streamlit_app.py
git commit -m "feat(ui): pestana Prode + graficos enchufados en la app"
```

---

## Verificación final

- `.\.venv\Scripts\python.exe -m pytest -q` → todos verdes.
- AppTest imprime `OK 6` sin excepción.
- App levantada: español, Prode y los 5 gráficos visibles.

## Notas

- **No** renombrar claves de equipos (rompe dataset/modelo/tests). Toda traducción vive en `app/flags.py`.
- `progression_bars` usa `yOffset` (barras agrupadas, Vega-Lite ≥5.1, ya soportado por la versión de Altair/Streamlit del proyecto). Si el AppTest fallara por eso, degradar a barras apiladas (`mark_bar()` sin `yOffset`, con `color` apilado).
