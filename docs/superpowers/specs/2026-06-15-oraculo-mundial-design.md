# Oráculo Mundial 2026 — Diseño

**Fecha:** 2026-06-15
**Estado:** Aprobado, listo para plan de implementación
**Inspirado en:** [Olora](https://github.com/MarianoVilla/Olora) (Mariano Villa, .NET 9 / Blazor)

## Objetivo

Construir un predictor del Mundial 2026, priorizando **acertar el resultado**
por encima de la simplicidad. Requisito: que sea **gratis** (no necesariamente
100% local — datos de internet como CSVs, scraping o APIs gratuitas están OK;
lo que se evita es lo pago). Se construye por niveles
crecientes —igual que el video fuente— de modo que cada nivel pueda medirse
contra el anterior y contra una vara de referencia (el "oloráculo" uniforme).

### Decisiones de alcance

- **Stack:** Python.
- **Capa de lesiones (análisis de noticias con LLM):** fuera del alcance inicial.
  Queda como extensión enchufable para el final.
- **Interfaz:** núcleo usable por CLI/notebook **+** capa web Streamlit encima.
  La web es solo una vista; toda la lógica vive en el núcleo.
- **Arquitectura elegida:** pipeline de niveles con una interfaz común
  (`Predictor`), para poder medir cada nivel con la misma métrica.

## Arquitectura

```
oraculo/
├── oraculo/                  # núcleo (lógica pura, sin UI)
│   ├── teams.py              # registro de selecciones + config WC2026
│   ├── ingest/
│   │   ├── results.py        # resultados históricos (CSV)
│   │   └── fifa.py           # ranking FIFA
│   ├── ratings/
│   │   ├── elo.py            # calcula Elo desde resultados históricos
│   │   └── form.py           # forma reciente
│   ├── models/               # los "niveles"
│   │   ├── base.py           # protocolo Predictor + MatchPrediction
│   │   ├── uniform.py        # nivel 0 (vara de medición)
│   │   ├── fifa_ranking.py   # nivel 1
│   │   ├── elo.py            # nivel 2
│   │   ├── elo_form.py       # nivel 3
│   │   └── poisson.py        # nivel 4: Poisson + Dixon-Coles
│   ├── simulate/montecarlo.py# simulador del Mundial (semilla fija)
│   ├── evaluate/metrics.py   # Brier, RPS, log-loss + backtesting
│   └── storage/db.py         # SQLite: snapshots, evaluaciones
├── notebooks/                # exploración y gráficos
├── app/streamlit_app.py      # vista web (solo consume el núcleo)
├── data/                     # CSVs crudos + oraculo.db
└── tests/
```

**Regla de oro:** toda la lógica vive en `oraculo/`. CLI, notebooks y Streamlit
son vistas que llaman al núcleo. Se puede cambiar un modelo sin tocar la web.

## Contrato común de los modelos

Todos los niveles implementan el mismo protocolo y devuelven el mismo objeto:

```python
@dataclass
class MatchPrediction:
    p_home: float          # P(gana local)
    p_draw: float          # P(empate)
    p_away: float          # P(gana visitante)
    xg_home: float | None = None              # goles esperados (modelos de goles)
    xg_away: float | None = None
    score_matrix: np.ndarray | None = None    # P(i goles local - j goles visitante)

class Predictor(Protocol):
    name: str
    def predict(self, home, away, *, neutral=False, on_date=None) -> MatchPrediction: ...
```

- Modelos de **ranking** (FIFA, Elo) llenan solo `p_home/draw/away`.
- Modelos de **goles** (Poisson) llenan además `score_matrix`, de la que se derivan
  las probabilidades 1-X-2 y los goles que necesita el Monte Carlo.

**Mejora sobre el video:** el autor admite que su Poisson quedó sesgado a
resultados bajos. En vez de promedios crudos, ataque/defensa se estiman con
**regresión de Poisson** (GLM de `statsmodels`) con peso por antigüedad
(decaimiento estilo Dixon-Coles). Esto corrige el sesgo.

## Fuentes de datos

| Dato | Fuente | Uso |
|------|--------|-----|
| Resultados históricos | `results.csv` de [martj42/international_results](https://github.com/martj42/international_results) | Base: Elo propio, ataque/defensa Poisson, forma reciente |
| Ranking FIFA | Snapshot CSV (Kaggle) o scrape de tabla oficial | Nivel 1 |
| Elo | Calculado por nosotros desde `results.csv` | Nivel 2 — reproducible, offline |
| Estructura WC2026 | Config `wc2026.yaml` con el sorteo oficial | Grupos, sedes, fixture para el Monte Carlo |

Notas:

- **Elo propio** (no eloratings.net): reproducible, offline, y permite tunear
  K-factor y ventaja de localía. Eloratings.net queda como validación opcional.
- **Grupos WC2026:** NO se inventan de memoria. Van en `wc2026.yaml`, llenado con
  el sorteo oficial. El torneo ya arrancó / está por arrancar (15/06/2026).
- Estas fuentes son un punto de partida; se pueden cambiar más adelante.

## Simulador Monte Carlo (formato WC2026)

- **48 equipos, 12 grupos (A–L) de 4.** Round-robin (3 pts triunfo / 1 empate).
  Orden: puntos → diferencia de gol → goles a favor → head-to-head. Empates
  irresolubles se rompen **al azar con la semilla fija** (sin "fair-play").
- **Clasifican:** 2 primeros de cada grupo (24) + 8 mejores terceros = 32 →
  dieciseisavos → octavos → cuartos → semi → final.
- **Eliminación directa:** se simulan goles; empate → **penales** resueltos con
  moneda ponderada por fuerza relativa.
- **Semilla hardcodeada:** las predicciones solo cambian si cambian los datos.
- Corre N=10.000 y agrega por equipo: P(pasa de grupo), P(llega a cada ronda),
  P(campeón).

**Adaptador de goles:** el Monte Carlo quiere una `score_matrix`. Los modelos de
goles la dan directo; a los de ranking se los envuelve con un adaptador que
sintetiza una distribución de goles desde sus probabilidades 1-X-2. Así
cualquier nivel es simulable sin ensuciar el protocolo.

## Evaluación y calibración

- **RPS** como métrica estrella (penaliza bien resultados ordenados
  local/empate/visitante), más **Brier** y **log-loss**.
- **Backtest walk-forward:** para cada partido histórico, predecir usando solo
  datos previos a esa fecha, puntuar y agregar. Prueba que cada nivel le gana al
  uniforme, y sirve para **calibrar** hiperparámetros (K-factor, ventaja de
  localía, `rho` de Dixon-Coles, decaimiento temporal `xi`) minimizando RPS.
- **SQLite** guarda snapshots (predicciones + ratings congelados con fecha) y
  evaluaciones. Cargar resultados reales a medida que pasan → re-puntuar →
  recalibrar. Esa es la pieza de "tiende a la distribución real".

## Orden de construcción (incremental, con TDD)

Cada paso es entregable y testeable de forma independiente:

1. Andamiaje del proyecto + ingesta de `results.csv` + registro de equipos.
2. **Nivel 0 uniforme + protocolo `Predictor` + métricas (Brier/RPS/log-loss) +
   backtest walk-forward** — la vara de medición primero.
3. Nivel 1: ranking FIFA.
4. Nivel 2: Elo propio (+ calibrar K-factor / ventaja de localía).
5. Nivel 3: Elo + forma reciente.
6. Nivel 4: Poisson + Dixon-Coles (GLM ataque/defensa, decaimiento temporal,
   `rho`) (+ calibrar).
7. Monte Carlo + config `wc2026.yaml`.
8. SQLite (snapshots/evals) + ingesta de resultados en vivo.
9. CLI.
10. Streamlit.

*Más adelante, opcional:* extensión de lesiones (análisis de noticias con LLM).

## Testing

- TDD en todo el núcleo. Las funciones matemáticas son ideales para tests:
  valores conocidos de actualización Elo, `pmf` de Poisson, RPS calculado a mano.
- El Monte Carlo se testea con semilla fija (resultados reproducibles) y con
  invariantes (las probabilidades por equipo suman 1, todos los equipos aparecen).
