"""Unit tests for UI components (Tray Icon & Settings Window)."""

import os
import pytest
from PyQt6.QtWidgets import QApplication

from config import TypoPilotConfig
from ui.tray_manager import create_tray_icon
from ui.settings_window import SettingsWindow


@pytest.fixture(scope="session")
def qapp():
    # Use offscreen platform for headless test execution
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_tray_icon_generation(qapp):
    icon_enabled = create_tray_icon(enabled=True)
    assert not icon_enabled.isNull()

    icon_disabled = create_tray_icon(enabled=False)
    assert not icon_disabled.isNull()


def test_settings_window_initialization(qapp):
    cfg = TypoPilotConfig(
        word_correction_shortcut="F4",
        max_edit_distance=3,
    )
    window = SettingsWindow(cfg)
    assert window.word_shortcut_input.text() == "F4"
    assert window.edit_distance_spin.value() == 3
