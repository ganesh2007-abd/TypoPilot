"""Windows startup integration manager for TypoPilot.

Manages automatic startup on Windows boot via user Startup folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "TypoPilot"


class StartupManager:
    """Manages Windows boot startup configuration without requiring administrator privileges."""

    @staticmethod
    def get_launcher_path() -> str:
        """Returns the command line to launch TypoPilot in the background using pythonw."""
        base_dir = Path(__file__).resolve().parent.parent
        venv_pythonw = base_dir / ".venv" / "Scripts" / "pythonw.exe"
        main_script = base_dir / "main.py"

        if venv_pythonw.exists():
            return f'"{venv_pythonw}" "{main_script}"'
        else:
            return f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{main_script}"'

    @staticmethod
    def get_startup_folder() -> Path:
        """Returns the user's personal Windows Startup directory."""
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    @classmethod
    def get_startup_script_path(cls) -> Path:
        """Returns path to the startup launcher batch file in user's Startup folder."""
        return cls.get_startup_folder() / f"{APP_NAME}.bat"

    @classmethod
    def is_startup_enabled(cls) -> bool:
        """Checks if TypoPilot is currently configured to start with Windows."""
        try:
            return cls.get_startup_script_path().exists()
        except Exception:
            return False

    @classmethod
    def set_startup(cls, enabled: bool) -> bool:
        """Enables or disables automatic startup with Windows by managing user's startup folder."""
        try:
            script_path = cls.get_startup_script_path()
            if enabled:
                cmd = cls.get_launcher_path()
                content = f'@echo off\nstart "" {cmd}\nexit\n'
                script_path.parent.mkdir(parents=True, exist_ok=True)
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                if script_path.exists():
                    script_path.unlink()
            return True
        except Exception as e:
            print(f"[TypoPilot Startup] Error modifying startup file: {e}")
            return False
