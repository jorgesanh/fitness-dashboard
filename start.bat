@echo off
REM Double-click launcher for the fitness dashboard (Windows).
REM Activates the local venv and starts Streamlit, reachable from your phone
REM on the same Wi-Fi network.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment found. Run:  python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0
pause
