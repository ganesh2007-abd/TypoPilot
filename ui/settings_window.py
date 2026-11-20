"""Settings window for TypoPilot.

Provides a clean, compact settings dialog to configure shortcuts, NLP parameters, and general behavior.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import TypoPilotConfig


class SettingsWindow(QDialog):
    """Compact settings dialog for TypoPilot."""

    settings_saved = pyqtSignal(TypoPilotConfig)

    def __init__(self, config: TypoPilotConfig, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("TypoPilot - Settings")
        self.setFixedSize(480, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_values()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # Tabs for clean grouping
        tabs = QTabWidget(self)

        # Tab 1: Shortcuts
        shortcuts_tab = QWidget()
        shortcuts_layout = QVBoxLayout(shortcuts_tab)

        shortcuts_group = QGroupBox("Global Keyboard Shortcuts")
        shortcuts_form = QFormLayout(shortcuts_group)

        self.word_shortcut_input = QLineEdit()
        self.word_shortcut_input.setPlaceholderText("e.g. F2")
        shortcuts_form.addRow("Word Correction / Cycle:", self.word_shortcut_input)

        self.sentence_shortcut_input = QLineEdit()
        self.sentence_shortcut_input.setPlaceholderText("e.g. Ctrl+F2")
        shortcuts_form.addRow("Sentence Correction:", self.sentence_shortcut_input)

        self.cancel_shortcut_input = QLineEdit()
        self.cancel_shortcut_input.setPlaceholderText("e.g. Esc")
        shortcuts_form.addRow("Cancel / Restore Original:", self.cancel_shortcut_input)

        shortcuts_layout.addWidget(shortcuts_group)
        shortcuts_layout.addStretch()
        tabs.addTab(shortcuts_tab, "Shortcuts")

        # Tab 2: NLP Settings
        nlp_tab = QWidget()
        nlp_layout = QVBoxLayout(nlp_tab)

        word_nlp_group = QGroupBox("Word Correction (SymSpell)")
        word_nlp_form = QFormLayout(word_nlp_group)

        self.edit_distance_spin = QSpinBox()
        self.edit_distance_spin.setRange(1, 3)
        self.edit_distance_spin.setValue(2)
        word_nlp_form.addRow("Max Edit Distance:", self.edit_distance_spin)

        self.max_suggestions_spin = QSpinBox()
        self.max_suggestions_spin.setRange(1, 10)
        self.max_suggestions_spin.setValue(5)
        word_nlp_form.addRow("Max Suggestions to Cycle:", self.max_suggestions_spin)

        self.case_preservation_cb = QCheckBox("Preserve original capitalization (Title / UPPER / lower)")
        word_nlp_form.addRow(self.case_preservation_cb)

        nlp_layout.addWidget(word_nlp_group)

        sentence_nlp_group = QGroupBox("Sentence Correction (Grammar)")
        sentence_nlp_form = QFormLayout(sentence_nlp_group)

        self.sentence_enabled_cb = QCheckBox("Enable sentence & paragraph grammar correction")
        sentence_nlp_form.addRow(self.sentence_enabled_cb)

        self.gpu_cb = QCheckBox("Use GPU acceleration when available (Phase 8)")
        sentence_nlp_form.addRow(self.gpu_cb)

        nlp_layout.addWidget(sentence_nlp_group)
        nlp_layout.addStretch()
        tabs.addTab(nlp_tab, "NLP Engine")

        # Tab 3: General Behavior
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        general_group = QGroupBox("Behavior & Notifications")
        general_form = QFormLayout(general_group)

        self.enabled_cb = QCheckBox("TypoPilot Active (Enabled)")
        general_form.addRow(self.enabled_cb)

        self.notifications_cb = QCheckBox("Show tray balloon notifications on status changes")
        general_form.addRow(self.notifications_cb)

        general_layout.addWidget(general_group)
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")

        main_layout.addWidget(tabs)

        # Dialog Buttons (Save / Cancel)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        self.save_button = QPushButton("Save Settings")
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self._on_save)
        buttons_layout.addWidget(self.save_button)

        main_layout.addLayout(buttons_layout)

    def _load_values(self) -> None:
        """Populates UI widgets with current configuration."""
        self.word_shortcut_input.setText(self.config.word_correction_shortcut)
        self.sentence_shortcut_input.setText(self.config.sentence_correction_shortcut)
        self.cancel_shortcut_input.setText(self.config.cancel_shortcut)

        self.edit_distance_spin.setValue(self.config.max_edit_distance)
        self.max_suggestions_spin.setValue(self.config.max_suggestions)
        self.case_preservation_cb.setChecked(self.config.case_sensitive_preservation)

        self.sentence_enabled_cb.setChecked(self.config.sentence_correction_enabled)
        self.gpu_cb.setChecked(self.config.use_gpu_if_available)

        self.enabled_cb.setChecked(self.config.enabled)
        self.notifications_cb.setChecked(self.config.tray_notifications)

    def _on_save(self) -> None:
        """Persists values to config object and saves to disk."""
        self.config.word_correction_shortcut = self.word_shortcut_input.text().strip() or "F2"
        self.config.sentence_correction_shortcut = self.sentence_shortcut_input.text().strip() or "Ctrl+F2"
        self.config.cancel_shortcut = self.cancel_shortcut_input.text().strip() or "Esc"

        self.config.max_edit_distance = self.edit_distance_spin.value()
        self.config.max_suggestions = self.max_suggestions_spin.value()
        self.config.case_sensitive_preservation = self.case_preservation_cb.isChecked()

        self.config.sentence_correction_enabled = self.sentence_enabled_cb.isChecked()
        self.config.use_gpu_if_available = self.gpu_cb.isChecked()

        self.config.enabled = self.enabled_cb.isChecked()
        self.config.tray_notifications = self.notifications_cb.isChecked()

        self.config.save()
        self.settings_saved.emit(self.config)
        self.accept()
