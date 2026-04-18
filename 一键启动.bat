@echo off
REM Open two CMD windows: backend :8000, frontend :3000
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERR] Missing .venv\Scripts\python.exe
    echo Create venv, then: pip install -r backend\requirements.txt
    echo Dir: %CD%
    pause
    exit /b 1
)
if not exist "frontend\package.json" (
    echo [ERR] Missing frontend\package.json
    pause
    exit /b 1
)

echo Starting backend and frontend ...
start "solo-backend" "%~dp0_run_backend.bat"
timeout /t 2 /nobreak >nul
start "solo-frontend" "%~dp0_run_frontend.bat"

echo Done. Close the two new windows to stop servers.
pause
