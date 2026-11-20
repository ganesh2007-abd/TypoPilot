@echo off
title TypoPilot Launcher
echo Starting TypoPilot in the background...

:: Launch TypoPilot using pythonw from the isolated virtual environment on D:
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"

echo TypoPilot is running in your Windows System Tray (near clock).
timeout /t 2 >nul
exit
