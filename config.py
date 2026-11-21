"""Configuration manager for TypoPilot.

Handles persistent application settings, keyboard shortcuts, and NLP engine parameters.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Default path for persistent settings
CONFIG_FILE_PATH = Path(__file__).resolve().parent / "config.json"


@dataclass
class TypoPilotConfig:
    # General
    enabled: bool = True
    start_with_windows: bool = False
    tray_notifications: bool = True

    # Keyboard Shortcuts (human-readable string format)
    word_correction_shortcut: str = "F2"            # Next candidate / Activate
    word_correction_prev_shortcut: str = "Shift+F2" # Previous candidate
    sentence_correction_shortcut: str = "Ctrl+F2"  # Sentence correction
    cancel_shortcut: str = "Esc"                   # Restore original misspelled text
    undo_shortcut: str = "Ctrl+Alt+Z"

    # NLP Word Correction Settings
    max_edit_distance: int = 2
    prefix_length: int = 7
    max_suggestions: int = 5
    case_sensitive_preservation: bool = True

    # NLP Sentence Correction Settings
    sentence_correction_enabled: bool = True
    sentence_model_name: str = "Unbabel/gec-t5_small"
    use_gpu_if_available: bool = True

    # NLP Professional Tone & Style Transfer Settings
    tone_trigger_key: str = "f5"
    tone_correction_shortcut: str = "F5"
    tone_correction_enabled: bool = True
    tone_model_name: str = "prithivida/informal_to_formal_styletransfer"

    @classmethod
    def load(cls, file_path: Path | str = CONFIG_FILE_PATH) -> TypoPilotConfig:
        """Loads configuration from JSON file, falling back to defaults if missing or corrupted."""
        path = Path(file_path)
        if not path.exists():
            config = cls()
            config.save(path)
            return config

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filter only known keys to avoid breaking on old/extra config keys
            valid_keys = {k for k in cls.__dataclass_fields__.keys()}
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered)
        except Exception:
            # If corrupted, return default without crashing
            return cls()

    def save(self, file_path: Path | str = CONFIG_FILE_PATH) -> bool:
        """Saves current configuration to JSON file."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
            return True
        except Exception as e:
            print(f"[TypoPilot] Error saving configuration: {e}")
            return False


# Global default instance
config = TypoPilotConfig.load()
