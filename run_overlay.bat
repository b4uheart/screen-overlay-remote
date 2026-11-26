@echo off
title Screen Overlay Daemon
cls
echo ==============================================================
echo       SCREEN OVERLAY REMOTE - HEADLESS NETWORK DAEMON
echo ==============================================================
echo.
echo Starting headless daemon...
echo.

python "%~dp0overlay.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Daemon closed with an error.
    pause
)
