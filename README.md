# Oráculo Mundial 2026

Predictor del Mundial 2026 por niveles (uniforme → FIFA → Elo → Poisson/Dixon-Coles)
con simulación Monte Carlo. Núcleo Python; interfaz CLI + Streamlit.

## Setup
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

## Página web (Streamlit)
```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```
Abre una página local con 5 vistas: **En vivo** (próximos con readiness T-60/30/15 + recientes real-vs-predicho), **Cuadro** (fixtures reales por fase: Grupos/16vos/8vos/4tos/Semis/Final), **Partido** (1X2, marcadores, xG, BTTS, Over/Under + extras), **Mundial** (Monte Carlo de campeón) y **Verificación** (aciertos/Brier/RPS + calibración sobre partidos jugados, modelo congelado).

## Datos en vivo del Mundial 2026

1. Conseguí una API key gratis en https://www.football-data.org/client/register
2. Copiá `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y pegá tu token
   (o exportá la variable de entorno `FOOTBALL_DATA_TOKEN`).
3. Corré la app: las pestañas **En vivo**, **Cuadro** y **Verificación** se llenan solas.

Sin token, la app igual funciona con el histórico (Partido, Mundial) y usa el
último cache disponible en `data/cache/` (modo offline). La key **nunca** se commitea
(`.streamlit/secrets.toml` está en `.gitignore`).
