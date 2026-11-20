@echo off
title TypoPilot Automated Test Suite
cd /d "%~dp0"
echo Running all 28 automated tests for TypoPilot...
echo.
"%~dp0.venv\Scripts\pytest.exe" -v
echo.
pause
