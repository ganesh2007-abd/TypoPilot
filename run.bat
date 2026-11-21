@echo off
title TypoPilot Launcher
cd /d "%~dp0"
echo ========================================================
echo   TypoPilot - Real-Time NLP Assistant
echo ========================================================
echo.
echo Ensuring any previous instances are closed...
taskkill /F /IM pythonw.exe 2>nul
echo Starting TypoPilot...
echo.
echo - A draggable toolbar will appear at the bottom of your screen.
echo - You can click [PAUSE] or [X] on it anytime if you need to stop it!
echo.
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
echo TypoPilot is running!
timeout /t 2 >nul
exit
