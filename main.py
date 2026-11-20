"""TypoPilot - Intelligent Desktop-Based NLP Assistant.

Main entry point for the background application and system tray.
"""

from __future__ import annotations

import sys
from PyQt6.QtWidgets import QApplication

from config import TypoPilotConfig
from core.keyboard_manager import KeyboardManager
from ui.settings_window import SettingsWindow
from ui.tray_manager import TrayManager


class TypoPilotApp:
    """Core application wrapper managing the background lifecycle."""

    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.config = TypoPilotConfig.load()

        # Initialize System Tray
        self.tray_manager = TrayManager(self.config)

        # Initialize Global Keyboard Listener
        self.keyboard_manager = KeyboardManager(self.config)
        self.keyboard_manager.start()

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
                f"TypoPilot is active in the background. Press {self.config.word_correction_shortcut} to correct words.",
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
        self.keyboard_manager.reload_bindings()

    def _on_status_changed(self, enabled: bool) -> None:
        """Called when enabled state is toggled from tray menu."""
        if self.settings_window and self.settings_window.isVisible():
            self.settings_window.enabled_cb.setChecked(enabled)

    def _on_quit(self) -> None:
        """Clean shutdown hook."""
        self.keyboard_manager.stop()


def main() -> int:
    """Main application execution function."""
    app = QApplication(sys.argv)
    app.setApplicationName("TypoPilot")
    app.setApplicationDisplayName("TypoPilot")

    # Crucial: Prevent app from terminating when settings window is closed
    app.setQuitOnLastWindowClosed(False)

    pilot_app = TypoPilotApp(app)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
