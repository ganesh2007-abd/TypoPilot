"""TypoPilot - Intelligent Desktop-Based NLP Assistant.

Main entry point for the background application, floating desktop toolbar, and system tray.
"""

from __future__ import annotations

import sys
import win32api
import win32event
import winerror
from PyQt6.QtWidgets import QApplication, QMessageBox

from config import TypoPilotConfig
from core.correction_manager import CorrectionManager
from core.keyboard_manager import KeyboardManager
from nlp.sentence_corrector import SentenceCorrector
from nlp.spell_checker import SpellChecker
from ui.floating_widget import FloatingWidget
from ui.settings_window import SettingsWindow
from ui.tray_manager import TrayManager

SINGLE_INSTANCE_MUTEX_NAME = "TypoPilot_SingleInstance_Mutex_Running"


class TypoPilotApp:
    """Core application wrapper managing the background lifecycle."""

    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.config = TypoPilotConfig.load()

        # Initialize System Tray
        self.tray_manager = TrayManager(self.config)

        # Initialize Global Keyboard Listener
        self.keyboard_manager = KeyboardManager(self.config)

        # Initialize Correction Manager (Word-level real-time NLP coordinator)
        self.correction_manager = CorrectionManager(self.config, self.keyboard_manager)

        # Start keyboard hook
        self.keyboard_manager.start()

        # Initialize Floating Draggable Desktop Toolbar
        self.floating_widget = FloatingWidget(self.config)
        self.floating_widget.pause_toggled.connect(self._on_status_changed)
        self.floating_widget.settings_clicked.connect(self.show_settings)
        self.floating_widget.quit_clicked.connect(self._on_quit)
        self.floating_widget.show()

        # Settings window reference (created on demand)
        self.settings_window: SettingsWindow | None = None

        # Wire up tray events
        self.tray_manager.settings_requested.connect(self.show_settings)
        self.tray_manager.status_changed.connect(self._on_status_changed)
        self.tray_manager.quit_requested.connect(self._on_quit)

        # Show welcome notification on startup
        if self.config.tray_notifications:
            self.tray_manager.show_notification(
                "TypoPilot Running",
                f"TypoPilot is active! Use the floating widget at the bottom of your screen to pause or stop anytime.",
            )

    def show_settings(self) -> None:
        """Opens or brings to front the settings dialog."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.config)
            self.settings_window.settings_saved.connect(self._on_settings_saved)

        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _on_settings_saved(self, updated_config: TypoPilotConfig) -> None:
        """Called when settings are updated and saved."""
        self.config = updated_config
        self.tray_manager.update_icon()
        self.floating_widget.update_status(self.config.enabled)
        self.keyboard_manager.reload_bindings()
        self.correction_manager.spell_checker = SpellChecker(updated_config)
        self.correction_manager.sentence_corrector = SentenceCorrector(
            updated_config, self.correction_manager.spell_checker
        )
        if self.config.tray_notifications:
            self.tray_manager.show_notification(
                "TypoPilot Settings", "Settings have been updated successfully."
            )

    def _on_status_changed(self, enabled: bool) -> None:
        """Called when enabled state is toggled from tray menu or floating toolbar."""
        self.config.enabled = enabled
        self.config.save()
        self.tray_manager.update_icon()
        self.floating_widget.update_status(enabled)
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.enabled_cb.setChecked(enabled)

    def _on_quit(self) -> None:
        """Clean shutdown hook."""
        self.keyboard_manager.stop()
        if hasattr(self, "floating_widget") and self.floating_widget:
            self.floating_widget.close()
        self.qapp.quit()


def main() -> int:
    """Main application execution function with Single-Instance Mutex protection."""
    # Enforce Single-Instance: Multiple simultaneous instances cause keyboard hook chaos
    mutex = win32event.CreateMutex(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        print("[TypoPilot] An instance of TypoPilot is already running! Exiting duplicate.")
        # If launched by double-clicking run.bat, notify the user
        app = QApplication(sys.argv)
        QMessageBox.information(
            None,
            "TypoPilot Already Running",
            "TypoPilot is already running on your desktop!\n\n"
            "Look for the floating widget at the bottom of your screen or the tray icon near your clock.\n"
            "To restart it completely, run stop.bat first.",
        )
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("TypoPilot")
    app.setApplicationDisplayName("TypoPilot")

    # Prevent app from terminating when individual dialogs close
    app.setQuitOnLastWindowClosed(False)

    pilot_app = TypoPilotApp(app)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
