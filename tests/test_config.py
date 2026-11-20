"""Unit tests for configuration manager."""

import tempfile
from pathlib import Path
from config import TypoPilotConfig


def test_default_config():
    cfg = TypoPilotConfig()
    assert cfg.enabled is True
    assert cfg.word_correction_shortcut == "F2"
    assert cfg.sentence_correction_shortcut == "Ctrl+F2"
    assert cfg.cancel_shortcut == "Esc"
    assert cfg.max_edit_distance == 2
    assert cfg.max_suggestions == 5


def test_config_save_and_load():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "test_config.json"

        # Create custom config
        cfg = TypoPilotConfig(
            enabled=False,
            word_correction_shortcut="F3",
            max_edit_distance=1,
            max_suggestions=8,
        )
        assert cfg.save(config_path) is True

        # Load back
        loaded = TypoPilotConfig.load(config_path)
        assert loaded.enabled is False
        assert loaded.word_correction_shortcut == "F3"
        assert loaded.max_edit_distance == 1
        assert loaded.max_suggestions == 8
