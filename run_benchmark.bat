@echo off
title TypoPilot Accuracy Benchmark
cd /d "%~dp0"
echo ========================================================
echo   Running TypoPilot Benchmark Evaluator...
echo ========================================================
echo.

"%~dp0.venv\Scripts\python.exe" "%~dp0benchmark\evaluator.py" %*

echo.
echo ========================================================
echo   Benchmark Complete!
echo ========================================================
pause
