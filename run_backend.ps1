Set-Location -Path "$PSScriptRoot\backend"
Write-Host "Starting MAYA Backend Server on http://127.0.0.1:8000..." -ForegroundColor Green
if (Test-Path ".\venv\bin\python.exe") {
    & ".\venv\bin\python.exe" run_server.py
} elseif (Test-Path ".\venv\Scripts\python.exe") {
    & ".\venv\Scripts\python.exe" run_server.py
} else {
    python run_server.py
}
