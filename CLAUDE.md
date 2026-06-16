# OlorACulo — Predictor del Mundial 2026

Predictor de fútbol en Python por niveles, inspirado en Olora (Mariano Villa, .NET).
Repo: https://github.com/Toto2980/OlorACulo

## Stack
- Python 3.11, Streamlit, Altair, NumPy, pandas
- Entorno virtual: `.venv/`
- 131 tests en `tests/` (pytest)
- Datos en vivo del Mundial: football-data.org (free tier, competición `WC`). Token en `.streamlit/secrets.toml` o env `FOOTBALL_DATA_TOKEN` (gitignored).

## Correr la app
```bash
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
# → http://localhost:8501
```

## CLI
```bash
.\.venv\Scripts\python.exe scripts/predict_match.py "Argentina" "Brazil"
.\.venv\Scripts\python.exe scripts/run_world_cup.py
```

## Arquitectura por niveles

Protocolo común `Predictor` (`oraculo/models/base.py`):
- `predict(home, away, *, neutral, on_date) -> MatchPrediction`
- `MatchPrediction(p_home, p_draw, p_away, xg_home, xg_away, score_matrix)`
- `StatefulModel` agrega `observe(match)` + `reset()` para walk-forward sin data leakage

| Nivel | Archivo | RPS (desde 2010) |
|-------|---------|-----------------|
| Uniforme (vara) | `models/uniform.py` | 0.2391 |
| Elo | `models/elo.py` | 0.1745 |
| **Poisson + DC** | `models/poisson.py` | **0.1726** ✅ |

## Parámetros calibrados
- **Elo:** K=40, home_adv=135, ν=0.8
- **Poisson:** lr=0.03, home_adv=0.3, rho=-0.05, baseline=log(1.3), max_goals=10

## Estructura clave
```
oraculo/
  ingest/results.py        # load_results() → list[Match]
  models/                  # uniform, elo, poisson
  ratings/elo.py           # davidson_probs, update_ratings
  ratings/poisson.py       # dc_tau, score_matrix, outcome_probs
  evaluate/                # metrics, backtest, walk_forward
  calibrate/               # grid search Elo y Poisson
  tournament/              # config, group, groupstage, bracket, knockout, tournament
  live/                    # client (API+cache+offline), names (alias), fixtures (parser), schedule (readiness T-60/30/15)
  report/match_report.py   # 1X2, marcadores, xG, BTTS, Over/Under + extras especulativos
  verify/                  # predictor (Poisson congelado anti-leakage), scoring (acierto/Brier/RPS/calibración), log
app/
  flags.py                 # with_flag(team) → "🇦🇷 Argentina"
  services.py              # top_scorelines, model_comparison
  charts.py                # componentes Altair reutilizables (win_prob_bar, ranking_bar, calibration_chart)
  live_view.py             # group_by_phase + filas próximos/finalizados
  streamlit_app.py         # UI 5 tabs: En vivo/Cuadro/Partido/Mundial/Verificación
data/
  results.csv              # ~49.4k partidos históricos (gitignored, martj42)
  wc2026.yaml              # 12 grupos del sorteo oficial + seed: 2026
  cache/                   # cache JSON de la API en vivo (gitignored)
```

## Decisiones de diseño
- Poisson usa **SGD incremental** sobre log-verosimilitud (no GLM con ventana) → encaja en walk_forward sin data leakage
- Elo usa **Davidson model** para convertir rating diff en 1-X-2
- Dixon-Coles corrige celdas (0,0)(0,1)(1,0)(1,1) via `dc_tau()`
- Monte Carlo: semilla fija desde `wc2026.yaml`, RNG único, modelo NO se resetea entre iteraciones
- Empates en eliminatorias → penales ponderados `p_home/(p_home+p_away)`
- Nombres de países alineados al dataset: "Czech Republic" (no "Czechia"), "Curaçao" (con cedilla)

## Predicciones WC2026 (Poisson, 10k sims, semilla 2026)
🥇 Argentina 19.1% · 🥈 Brasil 16.4% · 🥉 España 11.0% · Colombia 10.0% · Inglaterra 7.5%

## Datos en vivo + verificación (rama feat/live-tracking-verificacion)
- `oraculo/live/` trae fixtures/resultados reales de football-data.org (cache TTL + modo offline).
- `oraculo/verify/predictor.frozen_poisson` entrena solo con `date < 2026-06-11` → predicciones del Mundial out-of-sample (sin leakage).
- Pestañas En vivo / Cuadro / Verificación leen la API al abrir la app; sin proceso de fondo (readiness se calcula on-open).
- Nombres de la API mapeados a canónicos en `live/names.py` (solo 4 difieren: Bosnia-Herzegovina, Cape Verde Islands, Congo DR, Czechia).

## Pendientes opcionales
- Calibrar `baseline` Poisson con grid más amplio (óptimo quedó en el borde)
- Localía de anfitriones (USA/Canadá/México) en la simulación
- Adaptador score_matrix para EloModel (actualmente no simula torneos)
- Migrar `use_container_width` → `width=` en la UI (deprecado en Streamlit reciente)
