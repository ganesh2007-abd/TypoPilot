@echo off
title TypoPilot Keyboard Diagnostics
cd /d "%~dp0"
echo Starting keyboard tester...
"%~dp0.venv\Scripts\python.exe" "%~dp0test_keys.py"
pause
