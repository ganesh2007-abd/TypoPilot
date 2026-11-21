@echo off
title TypoPilot Live Debug Console
cd /d "%~dp0"
echo ========================================================
echo   TypoPilot Live Debug Console
echo ========================================================
echo.
echo NOTE FOR HP LAPTOPS:
echo If pressing [F2] changes screen brightness or volume,
echo your laptop requires: [Fn + F2] !
echo.
echo Press [F2] or [Fn + F2] in Notepad to see live debug logs below:
echo ========================================================
echo.

"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
pause
