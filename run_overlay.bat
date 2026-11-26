@echo off
title Screen Overlay Controller
cls
echo ==============================================================
echo                 SCREEN OVERLAY WITH WI-FI CONTROL
echo ==============================================================
echo.
echo Starting server...
echo.

python "%~dp0overlay.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Overlay closed with an error.
    pause
)
