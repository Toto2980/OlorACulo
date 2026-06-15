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
Abre una página local con 4 vistas: analizar partido, predicción del Mundial, comparar equipos y métricas.
