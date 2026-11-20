"""System Tray Manager for TypoPilot.

Provides the background Windows system tray icon, context menu, and status notifications.
"""

from __future__ import annotations

from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QApplication

from config import TypoPilotConfig


def create_tray_icon(enabled: bool = True) -> QIcon:
    """Generates a high-DPI dynamic icon for the system tray.

    Blue/green theme when enabled, muted grey when disabled.
    """
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background circle
    bg_color = QColor(33, 115, 243) if enabled else QColor(120, 120, 120)
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 16, 16)

    # Text "TP"
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "TP")

    # Status indicator dot in bottom-right corner
    dot_color = QColor(76, 175, 80) if enabled else QColor(244, 67, 54)
    painter.setBrush(dot_color)
    painter.setPen(QColor(255, 255, 255))
    painter.drawEllipse(size - 18, size - 18, 14, 14)

    painter.end()
    return QIcon(pixmap)


class TrayManager(QObject):
    """Manages the Windows System Tray Icon and its context menu."""

    status_changed = pyqtSignal(bool)
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, config: TypoPilotConfig, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.config = config

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_tray_icon(self.config.enabled))
        self.tray_icon.setToolTip("TypoPilot - Intelligent Real-Time NLP Assistant")

        self._build_context_menu()
        self.tray_icon.show()

    def _build_context_menu(self) -> None:
        """Constructs the right-click menu for the tray icon."""
        self.menu = QMenu()

        # Title action (disabled, acts as header)
        self.title_action = QAction("TypoPilot v1.0", self.menu)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)
        self.menu.addSeparator()

        # Enable/Disable toggle action
        self.toggle_action = QAction("Active / Enabled", self.menu)
        self.toggle_action.setCheckable(True)
        self.toggle_action.setChecked(self.config.enabled)
        self.toggle_action.toggled.connect(self._on_toggle_enabled)
        self.menu.addAction(self.toggle_action)

        self.menu.addSeparator()

        # Settings action
        self.settings_action = QAction("Settings...", self.menu)
        self.settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # Quit action
        self.quit_action = QAction("Exit TypoPilot", self.menu)
        self.quit_action.triggered.connect(self._on_quit)
        self.menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _on_toggle_enabled(self, checked: bool) -> None:
        """Handles user clicking the enabled toggle in the tray menu."""
        self.config.enabled = checked
        self.config.save()
        self.update_icon()

        if self.config.tray_notifications:
            state_text = "Activated" if checked else "Suspended (Disabled)"
            self.show_notification("TypoPilot Status", f"TypoPilot is now {state_text}.")

        self.status_changed.emit(checked)

    def update_icon(self) -> None:
        """Refreshes the tray icon appearance based on current enabled state."""
        self.tray_icon.setIcon(create_tray_icon(self.config.enabled))
        status = "Active" if self.config.enabled else "Disabled"
        self.tray_icon.setToolTip(f"TypoPilot [{status}] - Real-Time NLP Assistant")
        self.toggle_action.setChecked(self.config.enabled)

    def show_notification(self, title: str, message: str, msec: int = 2500) -> None:
        """Shows an unobtrusive balloon notification above the system tray."""
        if self.config.tray_notifications and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                msec,
            )

    def _on_quit(self) -> None:
        """Gracefully quits the application."""
        self.quit_requested.emit()
        QApplication.quit()
