@echo off
cd /d "%~dp0backend"
echo Starting MAYA Backend Server on http://127.0.0.1:8000...
if exist ".\venv\bin\python.exe" (
    .\venv\bin\python.exe run_server.py
) else if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe run_server.py
) else (
    python run_server.py
)
pause
