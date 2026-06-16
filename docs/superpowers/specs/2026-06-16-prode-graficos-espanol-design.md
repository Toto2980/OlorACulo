# OlorACulo — Español, gráficos y pestaña Prode

## Contexto

La app Streamlit del predictor del Mundial 2026 ([app/streamlit_app.py](../../../app/streamlit_app.py))
funciona bien pero tiene tres carencias que molestan al usuario:

1. **Mezcla idioma**: los nombres de equipos se muestran en inglés ("Brazil", "Spain", "Germany")
   porque son las claves canónicas del dataset histórico, el modelo y la config.
2. **Casi sin gráficos**: fuera de una barra de probabilidad 1X2, el análisis es texto plano.
3. **No hay análisis pre-partido tipo "prode"**: la pestaña Partido da números sueltos pero no
   un boletín pre-partido pensado para decidir un prode.

Objetivo: app 100% en español de cara al usuario, con visualizaciones ricas, y una pestaña nueva
de Prode con análisis pre-partido completo. Sin tocar la capa de modelo/datos (los 132 tests siguen
verdes) y sin sumar dependencias pagas ni de internet más allá de la API ya existente.

## Restricción clave

Las claves de equipos (`"Brazil"`, `"Spain"`, ...) son **canónicas** y se usan en `load_results`,
el modelo Poisson/Elo, `tournament/config`, `live/names` y los tests. **No se renombran.** Toda la
traducción al español es una capa de *presentación* en `app/`.

## Diseño

### 1. Español (capa de display)

- En [app/flags.py](../../../app/flags.py) agregar un dict `ES_NAMES: dict[str, str]` que mapea la
  clave canónica inglesa → nombre en español **solo para los casos que difieren** (Brazil→Brasil,
  Spain→España, Germany→Alemania, England→Inglaterra, Netherlands→Países Bajos, Japan→Japón,
  Sweden→Suecia, Egypt→Egipto, etc.). Los que ya coinciden (Argentina, Colombia, Uruguay…) no
  necesitan entrada.
- Nueva función `display_name(team: str) -> str` que devuelve `ES_NAMES.get(team, team)`.
- `with_flag(team)` pasa a devolver `f"{FLAGS.get(team,'⚽')} {display_name(team)}"` → `"🇧🇷 Brasil"`.
  Como toda la UI ya rutea los nombres por `with_flag()`, el cambio se propaga solo.
- Donde la UI usa el nombre crudo sin bandera (ej. el `fav` en el cuadro, `top_scorer_team`), rutear
  por `display_name()`.
- Las fases ya están en español ([oraculo/live/fixtures.py](../../../oraculo/live/fixtures.py) `PHASE_LABELS`).
  Se mantienen "Poisson"/"Elo" (nombres propios del modelo) y "BTTS" con su aclaración existente.

### 2. Gráficos nuevos (en [app/charts.py](../../../app/charts.py))

Cinco funciones nuevas, reutilizando la paleta "Álbum '86" ya definida en el módulo:

| Función | Firma | Consume | Se usa en |
|---------|-------|---------|-----------|
| `scoreline_heatmap` | `(matrix, home, away, max_goals=5)` | `pred.score_matrix` | Partido, Prode |
| `xg_bars` | `(home, away, xg_home, xg_away)` | `pred.xg_home/away` | Partido, Prode |
| `markets_bars` | `(btts, over25, over15)` | `MatchReport` | Partido, Prode |
| `progression_bars` | `(df)` con columnas Equipo/Semis/Final/Campeón | `champion_probs` | Mundial |
| `rps_line` | `(df)` con columnas n_partido/rps/partido | lista de `score_match` | Verificación |

Cada función devuelve un objeto Altair (`alt.Chart`/`alt.LayerChart`), como las existentes.
`markets_bars` necesita `over15`: se calcula con `over_prob(matrix, 1.5)` (ya existe en
[oraculo/report/match_report.py](../../../oraculo/report/match_report.py)); se agrega `over15` al
dataclass `MatchReport` y a `build_match_report`.

### 3. Pestaña "📋 Prode"

Sexta pestaña en [app/streamlit_app.py](../../../app/streamlit_app.py) (`st.tabs([... "📋 Prode"])`).

- **Selección de partido**:
  - Si hay fixtures reales (`get_fixtures()` ok): un `selectbox` con los próximos partidos
    (`upcoming_rows`), mostrando `"{fase} · {home} vs {away} · {kickoff}"`. Se usa cancha neutral
    (es Mundial).
  - Fallback (sin fixtures): dos `selectbox` de equipos como en la pestaña Partido.
- **Modelo**: Poisson (el de menor RPS). No se ofrece elegir — es el análisis "serio".
- **Secciones** (de arriba a abajo):
  1. Encabezado con los dos equipos (banderas + nombres ES) y, si viene de fixture, fase + horario.
  2. Métricas 1X2 + barra `win_prob_bar` (ya existe).
  3. Barras de xG (`xg_bars`).
  4. Heatmap de marcadores (`scoreline_heatmap`).
  5. Marcadores más probables (texto, vía `top_scorelines`).
  6. Barras de mercados (`markets_bars`): BTTS, Over 2.5, Over 1.5.
  7. **Conclusión** en lenguaje natural (figurita destacada `.verdict`/`.fav`).
- **Conclusión generada**: función nueva `prode_verdict(report: MatchReport) -> str` en
  [app/services.py](../../../app/services.py). Determinística (sin LLM, sin internet): a partir del
  `MatchReport` arma un párrafo — favorito y su margen, si el cruce viene parejo/abierto, y
  expectativa de goles (a partir de Over 2.5 / xG total). Ej.: *"Argentina llega favorita (52%).
  Partido trabado: el oráculo espera pocos goles (Over 2.5 al 38%)."*

Reutiliza `build_match_report()` que ya calcula 1X2, xG, marcadores, BTTS y Over.

## Archivos a tocar

- [app/flags.py](../../../app/flags.py) — `ES_NAMES`, `display_name`, `with_flag`.
- [app/charts.py](../../../app/charts.py) — 5 funciones de gráficos nuevas.
- [app/services.py](../../../app/services.py) — `prode_verdict`.
- [oraculo/report/match_report.py](../../../oraculo/report/match_report.py) — campo `over15`.
- [app/streamlit_app.py](../../../app/streamlit_app.py) — pestaña Prode + enchufar gráficos en
  Partido / Mundial / Verificación.

## Verificación

- **Tests nuevos** (pytest): `display_name`/`with_flag` traducen y dejan intactos los que ya coinciden;
  `prode_verdict` devuelve texto razonable para un favorito claro y para un cruce parejo; cada función
  de chart devuelve un objeto Altair sin excepción para un input típico; `over15 >= over25` en
  `build_match_report`.
- **AppTest**: la app levanta con **6 pestañas** sin excepción
  (`assert not at.exception; len(at.tabs) == 6`).
- **Suite completa** sigue verde (132 + nuevos).
- **Visual**: levantar la app de verdad (`streamlit run`) y revisar la pestaña Prode y los gráficos.

## Fuera de alcance (YAGNI)

- Export a imagen/PDF de la tarjeta de prode (opción C descartada).
- Localía de anfitriones en la simulación (sigue como pendiente del proyecto).
- Traducir nombres de equipos en datos crudos / API (solo capa de display).
