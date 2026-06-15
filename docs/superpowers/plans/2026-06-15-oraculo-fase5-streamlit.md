# Oráculo Mundial 2026 — Plan 5: Página web Streamlit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una página web local (Streamlit) que consuma el núcleo ya construido, con 4 vistas: analizar un partido, predicción del Mundial (P campeón), comparar equipos (ratings), y métricas del modelo.

**Architecture:** La lógica de preparación de datos vive en `app/services.py` (funciones puras, testeables, sin Streamlit). `app/streamlit_app.py` es solo la vista: widgets, caché (`@st.cache_resource`/`@st.cache_data`) y gráficos, llamando a `services` y al núcleo. El núcleo (`oraculo/`) no se toca ni depende de Streamlit.

**Tech Stack:** Python 3.11+, **streamlit** (nueva dependencia), pandas (ya), numpy (ya), pytest. Reusa `PoissonModel`, `EloModel`, `run_tournament_mc`, `run_group_stage_mc`, `backtest`, `walk_forward`.

**Decomposición:** Plan 5, sobre el predictor completo (Fases 1-4b). Última capa planificada del spec original (núcleo + Streamlit encima).

**Raíz del repo:** `C:\Users\locas\OneDrive\Escritorio\Claude\oraculo`. Paths relativos.

**Convenciones (Windows/PowerShell):** python/pytest con `.\.venv\Scripts\python.exe`; commits con doble `-m` para el trailer de coautoría.

**Decisiones (rendimiento):**
- Modelos entrenados una sola vez con `@st.cache_resource` (no en cada interacción).
- La simulación del Mundial (lenta) se cachea con `@st.cache_data` por nº de iteraciones y se controla con un slider (default 2000 para que responda).
- Sin matplotlib: la matriz de marcadores se muestra como tabla formateada, no como heatmap con gradiente.
- `app/streamlit_app.py` agrega la raíz del repo a `sys.path` para poder importar `app.services` tanto al correr con `streamlit run` como en tests.

---

## Task 1: Capa de servicios (lógica pura, testeable)

**Files:**
- Modify: `pyproject.toml` (agregar `streamlit` a dependencies)
- Create: `app/__init__.py` (EMPTY)
- Create: `app/services.py`
- Test: `tests/test_app_services.py`

- [ ] **Step 1: Agregar streamlit a `pyproject.toml`** — cambiar la línea de dependencies:

```toml
dependencies = ["pandas", "numpy", "pyyaml", "streamlit"]
```

Luego reinstalar: `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"` (instala Streamlit; puede tardar, baja varias dependencias).

- [ ] **Step 2: Write the failing test** `tests/test_app_services.py`:

```python
import datetime

import numpy as np

from oraculo.match import Match
from oraculo.evaluate.backtest import EvalResult
from app.services import top_scorelines, model_comparison


def test_top_scorelines_orders_by_probability():
    m = np.zeros((11, 11))
    m[2, 3] = 0.6
    m[1, 0] = 0.4
    top = top_scorelines(m, n=2)
    assert top[0] == ((2, 3), 0.6)
    assert top[1] == ((1, 0), 0.4)


def test_top_scorelines_length():
    m = np.full((11, 11), 1.0 / 121)
    assert len(top_scorelines(m, n=5)) == 5


def _matches():
    out = []
    day = 1
    for year in (2008, 2009, 2011, 2012):
        for _ in range(3):
            out.append(Match(
                date=datetime.date(year, 1, day),
                home="A", away="B", home_goals=2, away_goals=1,
                tournament="Friendly", neutral=True,
            ))
            day += 1
    return out


def test_model_comparison_returns_three_eval_results():
    res = model_comparison(_matches(), datetime.date(2010, 1, 1))
    assert set(res.keys()) == {"uniforme", "elo", "poisson"}
    for ev in res.values():
        assert isinstance(ev, EvalResult)
        assert ev.n_matches > 0
```

- [ ] **Step 3: Run, confirm FAIL** (`ModuleNotFoundError: No module named 'app.services'`):

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_services.py -v`

- [ ] **Step 4: Create `app/__init__.py` EMPTY, then implement `app/services.py`:**

```python
from __future__ import annotations

import datetime

import numpy as np

from oraculo.match import Match
from oraculo.models.uniform import UniformPredictor
from oraculo.models.elo import EloModel
from oraculo.models.poisson import PoissonConfig, PoissonModel
from oraculo.evaluate.backtest import backtest, EvalResult
from oraculo.evaluate.walk_forward import walk_forward


def top_scorelines(matrix: np.ndarray, n: int = 5) -> list[tuple[tuple[int, int], float]]:
    """Los n marcadores más probables: lista de ((goles_local, goles_visit), prob)."""
    cols = matrix.shape[1]
    order = np.argsort(matrix, axis=None)[::-1][:n]
    out: list[tuple[tuple[int, int], float]] = []
    for idx in order:
        i, j = divmod(int(idx), cols)
        out.append(((i, j), float(matrix[i, j])))
    return out


def model_comparison(
    matches: list[Match], eval_from: datetime.date
) -> dict[str, EvalResult]:
    """Backtest comparativo (uniforme vs Elo vs Poisson) sobre la misma ventana."""
    eval_set = [m for m in matches if m.date >= eval_from]
    return {
        "uniforme": backtest(UniformPredictor(), eval_set),
        "elo": walk_forward(EloModel(), matches, eval_from=eval_from),
        "poisson": walk_forward(
            PoissonModel(PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)),
            matches,
            eval_from=eval_from,
        ),
    }
```

- [ ] **Step 5: Run, confirm 3 passed:**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_services.py -v`
Expected: PASS (3 passed). (Si el import de `app.services` fallara por sys.path, confirmar que `app/__init__.py` existe y que se corre pytest desde la raíz del repo.)

- [ ] **Step 6: Commit:**

```powershell
git add pyproject.toml app/__init__.py app/services.py tests/test_app_services.py
git commit -m "feat: add Streamlit app services layer (pure, tested)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: La página Streamlit (4 vistas)

**Files:**
- Create: `app/streamlit_app.py`
- Modify: `README.md` (agregar instrucción de cómo correr la web)

- [ ] **Step 1: Implement `app/streamlit_app.py`:**

```python
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
from oraculo.tournament.montecarlo import run_group_stage_mc
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
```

- [ ] **Step 2: Verificar que compila** (no hay forma estándar de "testear" UI Streamlit; verificamos sintaxis e imports):

Run: `.\.venv\Scripts\python.exe -m py_compile app/streamlit_app.py app/services.py`
Expected: sin salida (compila OK).

- [ ] **Step 3: Smoke test de arranque headless** (lanzar y confirmar que levanta sin excepción):

Run en background y esperar ~10s:
`.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.headless true --server.port 8765`
Expected: en el log aparece "You can now view your Streamlit app" (o similar) sin traceback. Luego cortar el proceso. Si tira excepción al iniciar, reportarla como concern (NO seguir). Si no se puede correr en background de forma confiable, reportar que el `py_compile` pasó y dejar el arranque para verificación manual.

- [ ] **Step 4: Agregar instrucción a `README.md`** — añadir esta sección al final:

```markdown

## Página web (Streamlit)
```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```
Abre una página local con 4 vistas: analizar partido, predicción del Mundial, comparar equipos y métricas.
```

- [ ] **Step 5: Run the FULL suite and commit:**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests en verde (la suite no incluye la UI, pero confirma que nada se rompió).

```powershell
git add app/streamlit_app.py README.md
git commit -m "feat: add Streamlit web UI (match analysis, champion prediction, team comparison, metrics)" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Done cuando

- `pytest` pasa toda la suite + los tests de `app/services.py`.
- `app/streamlit_app.py` compila y arranca sin excepción.
- `streamlit run app/streamlit_app.py` levanta la página con las 4 vistas funcionando.

Siguiente (opcional): desplegar (Streamlit Community Cloud), persistencia SQLite, fijar partidos jugados, extensión de lesiones.
