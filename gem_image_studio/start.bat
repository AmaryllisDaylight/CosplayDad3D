@echo off
cd /d "%~dp0"

echo ========================================================
echo   CosplayDad3D Glass Studio - Image ^& Tripo 3D Hub
echo   URL: http://127.0.0.1:5050
echo ========================================================

:: Auto-bootstrap virtual environment on a new laptop if .venv is missing
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [First-Time Setup] Creating Python virtual environment ^(.venv^)...
    python -m venv "%~dp0.venv"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Could not create .venv. Make sure Python 3.10+ is installed and on PATH.
        pause
        goto :eof
    )
    echo [First-Time Setup] Installing requirements...
    "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
    "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
)

netstat -aon | findstr "127.0.0.1:5050" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Server is already running on http://127.0.0.1:5050
    echo Opening browser...
    start "" "http://127.0.0.1:5050"
    goto :eof
)

echo Starting server and opening browser...
"%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server stopped with error code %ERRORLEVEL%.
    pause
)
