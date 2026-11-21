@echo off
title Stop TypoPilot
cd /d "%~dp0"
echo ========================================================
echo   Stopping all TypoPilot background processes...
echo ========================================================
echo.

taskkill /F /IM pythonw.exe /T 2>nul
taskkill /F /FI "WINDOWTITLE eq TypoPilot*" /T 2>nul

echo.
echo ========================================================
echo   TypoPilot has been stopped completely!
echo   Your keyboard is 100%% back to normal.
echo ========================================================
timeout /t 3
exit
