@echo off
title Stop Screen Overlay
cls
echo Stopping background overlay...
taskkill /F /IM pythonw.exe >nul 2>&1
echo.
echo ===============================================
echo   Overlay successfully stopped.
echo ===============================================
echo.
timeout /t 2 >nul
