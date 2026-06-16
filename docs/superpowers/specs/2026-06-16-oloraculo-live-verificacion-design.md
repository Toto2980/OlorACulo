# OlorACulo — Seguimiento en vivo + verificación del Mundial 2026

**Fecha:** 2026-06-16
**Estado:** Diseño aprobado
**Autor:** brainstorming (Claude + Toto)

## Objetivo

Convertir OlorACulo de un predictor estático en un **dashboard profesional del Mundial 2026 en curso** que:

1. Trae **resultados reales** desde una API gratuita.
2. Muestra el **cuadro completo por fase** (Grupos · 16vos · 8vos · 4tos · Semis · Final) con la predicción del modelo y el resultado real lado a lado.
3. Tiene un **pipeline de preparación/verificación pre-partido** (T-60 / T-30 / T-15 min) que se evalúa **al abrir la app** (sin proceso de fondo).
4. **Verifica predicho vs. real** con métricas en vivo (aciertos, Brier, RPS, calibración) sobre los partidos ya jugados del Mundial.
5. Predicción por partido **rigurosa + extras especulativos** (estos últimos marcados como estimación).

## Contexto (estado actual)

- **Motor** (`oraculo/`): 3 niveles — Uniforme, Elo (Davidson), **Poisson + Dixon-Coles** (mejor, RPS 0.1726). Backtest walk-forward sin data leakage. 95 tests.
- **Simulación** (`oraculo/tournament/`): Monte Carlo completo (grupos → cuadro R32 → eliminatorias). `run_tournament_mc()` **ya calcula** P(llegar a cada ronda): R32, R16, QF, SF, Final, Campeón.
- **App** (`app/streamlit_app.py`): 4 pestañas (Partido / Mundial / Equipos / Métricas), estética "álbum Panini", gráficas Altair.
- **Hallazgo:** el motor ya computa todas las fases; la UI solo muestra una tabla Campeón/Final/Semis. No hay cuadro ni vista por fase, ni datos reales del torneo en curso.

## Decisiones de diseño (acordadas)

| Tema | Decisión |
|------|----------|
| Fuente de datos reales | **API gratuita con key** (football-data.org, competición `WC`; fallback API-Football). Verificar cobertura antes de codear. |
| Granularidad | **Resultado final por partido** (no minuto a minuto). |
| Detalle de predicción | **Riguroso + extras especulativos** (extras claramente marcados como estimación no rigurosa). |
| Automatización | **Sin background.** La app calcula al abrirse y muestra cuenta regresiva + estado de verificación T-60/30/15. |
| Anti-leakage | Predictor de verificación entrenado **solo con partidos anteriores al inicio del Mundial** (cutoff `2026-06-11`, configurable). |

## Arquitectura

Dos fuentes complementarias:
- **Reales** (API) → cuadro, verificación, partidos jugados.
- **Simulación** (engine Monte Carlo existente) → probabilidades de avance a futuro.

### 1. Capa de datos reales — `oraculo/live/`

Cada unidad es pura o con un único punto de I/O (el cliente), testeable de forma aislada.

- **`client.py`** — Cliente de football-data.org.
  - API key desde `.streamlit/secrets.toml` **o** env `FOOTBALL_DATA_TOKEN`. Nunca en el repo.
  - **Cache local** en `data/cache/*.json` con TTL (corto en días de partido, largo si no). Respeta rate-limit (free tier ~10 req/min) y permite **modo offline** (usa el último cache).
  - Backoff simple ante 429/5xx.
  - Interfaz: `fetch_matches()`, `fetch_standings()` → JSON crudo (cacheado).
- **`names.py`** — Mapa de alias **API ↔ nombres canónicos** (los de `wc2026.yaml` / dataset martj42; ej. `"USA" → "United States"`, `"Korea Republic" → "South Korea"`).
  - `to_canonical(api_name) -> str`. Test que falla si falta alguno de los 48 equipos del Mundial.
- **`fixtures.py`** — Modelo de dominio + parser.
  - `Fixture(id, stage, group, home, away, kickoff_utc, status, home_goals, away_goals)`.
  - `parse_fixtures(raw_json) -> list[Fixture]` (nombres ya canonicalizados vía `names`).
  - `status ∈ {SCHEDULED, LIVE, FINISHED, POSTPONED}`.
- **`schedule.py`** — Lógica de readiness **pura** (sin I/O).
  - `readiness(now, kickoff) -> ReadinessState` con estados `{LEJOS, T60, T30, T15, EN_VIVO, FINAL}`.
  - `verification_checks(fixture) -> list[Check]`: fixture confirmado, fecha/hora presente, no postergado, ambos rivales resueltos (no "TBD"). Cada `Check(label, ok)`.

### 2. Predicción detallada — `oraculo/report/match_report.py`

`build_match_report(model, home, away, *, neutral=True) -> MatchReport`

- **Riguroso** (derivado de `MatchPrediction.score_matrix`):
  - `p_home / p_draw / p_away`
  - top-5 marcadores (reusa `app.services.top_scorelines`)
  - `xg_home / xg_away`
  - **BTTS** (ambos marcan) = `1 - P(home=0) - P(away=0) + P(0,0)`
  - **Over/Under 2.5** = `P(total_goals >= 3)`
- **Extras especulativos** (campo separado `speculative`, marcado ⚠️ *estimación, no sale del modelo*):
  - favorito a goleador: el equipo con **mayor xG** del partido (regla única, no "o").
  - rango de tarjetas: **banda fija escalada por la paridad del cruce** (más parejo en 1X2 → banda más alta). Determinista, documentada como heurística.
- Invariante: `p_home + p_draw + p_away ≈ 1`; BTTS y O/U en `[0,1]`.

### 3. Verificación — `oraculo/verify/`

- **Predictor congelado (anti-leakage):**
  - Helper que entrena `PoissonModel` / `EloModel` **solo con `match.date < cutoff`** (`cutoff = 2026-06-11`).
  - Garantiza que toda predicción de un partido del Mundial es out-of-sample y determinista (no depende de cuándo se calcula).
- **`scoring.py`** (puro):
  - `score_match(pred, actual) -> MatchScore`: acierto 1X2 (bool), Brier, RPS, error de marcador (|pred_top - real|).
  - `aggregate(scores) -> Summary`: aciertos %, Brier/RPS medios, **curva de calibración** (bins de prob predicha vs frecuencia real observada), serie temporal (orden cronológico).
- **`data/predictions_log.json`** — Bitácora: snapshot por partido `{fixture_id, timestamp, p_home, p_draw, p_away, top_score}`. Se escribe al ver por primera vez un fixture; sirve de auditoría (la corrección de las métricas no depende de él gracias al cutoff congelado).

### 4. App profesional — `app/`

Reestructurar en 5 pestañas: **En vivo · Cuadro · Partido · Mundial · Verificación**

- **En vivo:** próximos partidos con **cuenta regresiva** + estado `T-60/30/15/EN_VIVO/FINAL` y checklist de verificación; partidos recientes con **real vs predicho** (acierto/fallo).
- **Cuadro:** vista por fase — **Grupos · 16vos · 8vos · 4tos · Semis · Final**. Cada cruce real (API) con su predicción y, si ya se jugó, el resultado. Overlay de **probabilidad Monte Carlo de avance**. Tablas de grupos en vivo (standings de la API).
- **Partido:** el `MatchReport` detallado (riguroso + extras).
- **Mundial:** Monte Carlo de campeón (lo actual, pulido).
- **Verificación:** predicho vs real **acumulado del Mundial** — % aciertos 1X2, Brier/RPS sobre partidos jugados, **curva de calibración**, evolución temporal; + el backtest histórico existente.
- **`app/charts.py`** — componentes Altair reutilizables (barra 1X2, ranking, calibración, serie temporal) para no repetir y unificar el estilo.

## Flujo de datos

```
API football-data.org
   │ (client + cache TTL)
   ▼
raw JSON ──► fixtures.parse_fixtures ──► list[Fixture]
                                          │
              ┌───────────────────────────┼────────────────────────────┐
              ▼                           ▼                            ▼
      schedule.readiness          report.build_match_report     verify.scoring
      (En vivo / countdown)       (Partido / Cuadro)            (fixtures FINISHED)
                                          ▲                            ▲
                                   modelo congelado (< cutoff) ────────┘

engine Monte Carlo (run_tournament_mc) ──► P(avance por fase) ──► overlay Cuadro + Mundial
```

## Manejo de errores / offline

- **Sin key o sin internet:** usar último cache + banner "modo offline / datos al `<timestamp>`". Simulación y backtest histórico siguen funcionando.
- **Rate limit (429):** respetar TTL del cache + backoff.
- **Nombre no mapeado:** log de advertencia + listarlo; el test de cobertura de `names` falla si falta alguno de los 48.

## Seguridad

- API key **nunca** en git: `.streamlit/secrets.toml` (ya gitignored) o env var `FOOTBALL_DATA_TOKEN`.
- Documentar el setup de la key en README.

## Testing

- `live/`: parser de fixtures con **JSON de ejemplo grabado** (sin red en tests), `schedule.readiness` y `verification_checks` puros, cobertura de `names` (48 equipos).
- `report/`: invariantes (probabilidades suman 1; BTTS y O/U coherentes con la matriz).
- `verify/`: `scoring` contra casos conocidos; test de **no-leakage** (el predictor congelado no ve partidos `>= cutoff`).
- Mantener los **95 tests** existentes en verde.

## Fuera de alcance (YAGNI)

- En vivo minuto a minuto / eventos (gol a gol, tarjetas reales).
- Proceso de fondo / scheduler (descartado: la app calcula al abrirse).
- Predicción de eventos individuales con rigor (el modelo es de goles a nivel equipo).
- Datos pagos o que requieran scraping frágil.

## Primer paso de implementación

Verificar que el free tier de **football-data.org** cubra el Mundial 2026 (endpoints `competitions/WC/matches` y `/standings`). Si no, fallback a **API-Football** (free tier vía RapidAPI). Confirmar antes de escribir el cliente.

## Plan de fases sugerido (para writing-plans)

1. **Fase L1 — Capa live:** `client` (+ cache), `names` (+ test 48), `fixtures` (+ parser con JSON grabado), `schedule` (readiness + checks). Sin UI.
2. **Fase L2 — Report + Verify:** `match_report`, predictor congelado, `scoring`, log. Pura lógica + tests.
3. **Fase L3 — UI:** `app/charts.py`, pestañas En vivo / Cuadro / Verificación; pulir Partido / Mundial.
4. **Fase L4 — Pulido profesional:** banners offline, README (setup de key), revisión de estilo/charts, docs.
