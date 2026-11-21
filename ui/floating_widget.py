"""Floating Draggable Desktop Widget for TypoPilot.

Provides an always-on-top, draggable desktop toolbar for instant status visibility,
one-click emergency pausing/disabling, and quick access to settings and clean shutdown.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from config import TypoPilotConfig


class FloatingWidget(QWidget):
    """Compact, draggable, always-on-top pill widget positioned at the bottom of the screen."""

    pause_toggled = pyqtSignal(bool)   # Emits new enabled state (True=Active, False=Paused)
    settings_clicked = pyqtSignal()     # Emits when settings button is clicked
    quit_clicked = pyqtSignal()         # Emits when emergency stop/quit is clicked

    def __init__(self, config: TypoPilotConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config
        self._drag_pos = QPoint()

        # Window flags: Frameless, Always on Top, Tool window, Does NOT steal focus when clicked!
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._init_ui()
        self._position_at_bottom()
        self.update_status(self.config.enabled)

    def _init_ui(self) -> None:
        self.setFixedSize(360, 48)

        # Main background container frame
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 360, 48)
        self.container.setObjectName("container")

        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 1. Drag Handle / App Label
        self.logo_label = QLabel("✈ <b>TypoPilot</b>")
        self.logo_label.setStyleSheet("color: #60a5fa; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.logo_label)

        # 2. Status Dot & Text
        self.status_label = QLabel("ACTIVE")
        self.status_label.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 3. Emergency PAUSE / RESUME Toggle Button
        self.toggle_btn = QPushButton("PAUSE")
        self.toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setToolTip("Click to instantly pause or resume TypoPilot shortcuts")
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.toggle_btn)

        # 4. Settings Button
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setToolTip("Open TypoPilot Settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #272732;
                color: #e2e8f0;
                border: 1px solid #3f3f50;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3b3b4f;
            }
        """)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

        # 5. Emergency STOP / QUIT Button
        self.quit_btn = QPushButton("✕")
        self.quit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.quit_btn.setFixedSize(28, 28)
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.setToolTip("Stop TypoPilot completely")
        self.quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.quit_btn.clicked.connect(self.quit_clicked.emit)
        layout.addWidget(self.quit_btn)

        self._apply_styles()

    def _apply_styles(self) -> None:
        self.container.setStyleSheet("""
            QFrame#container {
                background-color: rgba(24, 24, 32, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
            }
        """)

    def _position_at_bottom(self) -> None:
        """Positions the widget at the bottom center of the active screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
            y = screen_geo.y() + screen_geo.height() - self.height() - 20
            self.move(x, y)

    def update_status(self, enabled: bool) -> None:
        """Updates colors and labels according to active/paused state."""
        if enabled:
            self.status_label.setText("● ACTIVE")
            self.status_label.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
            self.toggle_btn.setText("PAUSE")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #eab308;
                    color: #0f172a;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #facc15;
                }
            """)
        else:
            self.status_label.setText("● PAUSED")
            self.status_label.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold;")
            self.toggle_btn.setText("RESUME")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22c55e;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #16a34a;
                }
            """)

    def _on_toggle_clicked(self) -> None:
        new_state = not self.config.enabled
        self.config.enabled = new_state
        self.config.save()
        self.update_status(new_state)
        self.pause_toggled.emit(new_state)

    # --- Drag and Drop Handling ---
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
