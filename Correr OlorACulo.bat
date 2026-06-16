@echo off
REM Lanzador de OlorACulo — doble click para abrir la app en el navegador.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No se encontro el entorno virtual .venv
    echo Crealo con: python -m venv .venv  y luego instalá las dependencias.
    pause
    exit /b 1
)

echo Iniciando OlorACulo... se abrira en tu navegador (http://localhost:8501)
echo Para cerrarlo, volve a esta ventana y apreta Ctrl+C.
echo.

.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py

REM Si streamlit termina por un error, dejamos la ventana abierta para ver el mensaje.
pause
