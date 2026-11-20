"""TypoPilot Windowless Background Launcher.

Double-clicking this file runs TypoPilot quietly in the background
without popping up any command prompt window.
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHONW = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"
MAIN_SCRIPT = BASE_DIR / "main.py"

if not PYTHONW.exists():
    PYTHONW = Path(sys.executable.replace("python.exe", "pythonw.exe"))

subprocess.Popen(
    [str(PYTHONW), str(MAIN_SCRIPT)],
    cwd=str(BASE_DIR),
    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
)
