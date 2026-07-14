@echo off
chcp 65001 >nul
title AMZ analysis set - Bridge Server
echo.
echo   ========================================
echo     AMZ analysis set - Bridge Server
echo   ========================================
echo.
echo   Starting bridge server on http://127.0.0.1:9876
echo.
cd /d "%~dp0scripts"
python bridge.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Python not found. Trying python3...
    python3 bridge.py
)
pause