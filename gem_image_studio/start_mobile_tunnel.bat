@echo off
cd /d "%~dp0"

echo ========================================================
echo   CosplayDad3D Glass Studio - Mobile Web Tunnel
echo   Exposes Glass Studio to the Public Internet (Phones)
echo ========================================================
echo.

:: Ensure server is running
netstat -aon | findstr "5050" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [Notice] Glass Studio is not running yet. Starting server in background...
    start "" /b "%~dp0.venv\Scripts\python.exe" "%~dp0app.py" --no-browser
    timeout /t 2 >nul
)

echo Starting Cloudflare Quick Tunnel to http://127.0.0.1:5050...
echo Look for your https://*.trycloudflare.com URL below:
echo.

if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:5050
) else (
    echo ERROR: cloudflared.exe not found in C:\Program Files (x86)\cloudflared\
    pause
)
