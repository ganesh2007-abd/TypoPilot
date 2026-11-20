@echo off
title TypoPilot Launcher
cd /d "%~dp0"
echo ========================================================
echo   TypoPilot - Real-Time NLP Assistant
echo ========================================================
echo.
echo Starting TypoPilot...
echo.
echo Look for the 'TP' icon in your Windows System Tray
echo (bottom-right near your clock / Wi-Fi icon).
echo.
echo Global Shortcuts:
echo   [F2]        - Word Correction / Next Candidate
echo   [Shift+F2]  - Previous Candidate
echo   [Esc]       - Restore Original Word
echo   [Ctrl+F2]   - Sentence Grammar Correction
echo.

start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"

echo TypoPilot is running!
timeout /t 3 >nul
exit
