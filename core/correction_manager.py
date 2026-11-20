"""Correction manager for TypoPilot.

Coordinates global keyboard shortcuts, text detection, NLP candidate generation,
two-way prediction cycling (Next / Previous), and restoration of original text.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import List, Optional
from pynput.keyboard import Key

from config import TypoPilotConfig
from core.keyboard_manager import KeyboardManager
from core.text_handler import DetectedWord, TextHandler, preserve_capitalization
from core.undo_manager import UndoManager
from nlp.spell_checker import SpellChecker


@dataclass
class ActiveSession:
    """Represents an ongoing word correction cycling session."""
    original_word: str              # Original clean word before any replacement
    detected_token: DetectedWord     # Boundary and punctuation information
    candidates: List[str]            # List of ranked suggestions
    current_index: int               # Current index in candidates list
    last_replaced_token: str         # The exact text currently on screen in the active app
    last_active_time: float          # Timestamp to expire stale sessions


class CorrectionManager:
    """Coordinates real-time word correction and cycling."""

    def __init__(
        self,
        config: TypoPilotConfig,
        keyboard_manager: KeyboardManager,
        text_handler: Optional[TextHandler] = None,
        spell_checker: Optional[SpellChecker] = None,
        undo_manager: Optional[UndoManager] = None,
    ):
        self.config = config
        self.keyboard_manager = keyboard_manager
        self.text_handler = text_handler or TextHandler()
        self.spell_checker = spell_checker or SpellChecker(config)
        self.undo_manager = undo_manager or UndoManager()

        self._active_session: Optional[ActiveSession] = None
        self._lock = threading.Lock()
        self.session_timeout = 8.0  # seconds before cycling session expires

        # Wire callbacks to keyboard manager
        self.keyboard_manager.on_word_correction_next = self.handle_next_prediction
        self.keyboard_manager.on_word_correction_prev = self.handle_prev_prediction
        self.keyboard_manager.on_cancel_restore = self.handle_cancel_restore

    def _is_session_valid(self) -> bool:
        """Checks if current session is active and not timed out."""
        if self._active_session is None:
            return False
        if (time.time() - self._active_session.last_active_time) > self.session_timeout:
            self._active_session = None
            return False
        return True

    def handle_next_prediction(self) -> None:
        """Handles F2 (Next Prediction or Initial Activation)."""
        if not self.config.enabled:
            return

        with self._lock:
            # Case 1: Already cycling an active word
            if self._is_session_valid():
                session = self._active_session
                assert session is not None
                new_index = (session.current_index + 1) % len(session.candidates)
                self._apply_candidate(session, new_index)
                return

            # Case 2: New correction activation at cursor
            detected = self.text_handler.detect_word_at_cursor()
            if detected is None:
                return

            # Query NLP suggestions with preceding context
            suggestions = self.spell_checker.get_suggestions(
                word=detected.raw_word,
                context_before=detected.context_before,
                max_suggestions=self.config.max_suggestions,
            )

            if not suggestions:
                return

            # Calculate first replacement token
            cased = preserve_capitalization(detected.raw_word, suggestions[0])
            first_token = f"{detected.leading_punctuation}{cased}{detected.trailing_punctuation}"

            # Create new session
            session = ActiveSession(
                original_word=detected.raw_word,
                detected_token=detected,
                candidates=suggestions,
                current_index=0,
                last_replaced_token=first_token,
                last_active_time=time.time(),
            )
            self._active_session = session

            # Record in undo history
            self.undo_manager.record_correction(
                original=detected.raw_word,
                replaced=suggestions[0],
                token=detected,
            )

            # Perform replacement in target application with suppressed hooks
            self._execute_replacement(
                old_token=detected.full_token,
                new_token=first_token,
                method=detected.method,
            )

    def handle_prev_prediction(self) -> None:
        """Handles Shift+F2 (Previous Prediction)."""
        if not self.config.enabled:
            return

        with self._lock:
            if not self._is_session_valid():
                return

            session = self._active_session
            assert session is not None
            new_index = (session.current_index - 1) % len(session.candidates)
            self._apply_candidate(session, new_index)

    def handle_cancel_restore(self) -> None:
        """Handles Esc (Restore Original Misspelled Word)."""
        if not self.config.enabled:
            return

        with self._lock:
            if not self._is_session_valid():
                return

            session = self._active_session
            assert session is not None

            # Original token restoration
            orig_token = session.detected_token.full_token

            # Replace current candidate with original token
            self._execute_replacement(
                old_token=session.last_replaced_token,
                new_token=orig_token,
                method="uia",  # After cycling, cursor is positioned at end of replaced word
            )

            # Reset active session
            self._active_session = None

    def _apply_candidate(self, session: ActiveSession, new_index: int) -> None:
        """Replaces the currently displayed candidate with the candidate at new_index."""
        candidate = session.candidates[new_index]
        cased = preserve_capitalization(session.original_word, candidate)
        new_token = f"{session.detected_token.leading_punctuation}{cased}{session.detected_token.trailing_punctuation}"

        old_token = session.last_replaced_token

        session.current_index = new_index
        session.last_replaced_token = new_token
        session.last_active_time = time.time()

        self._execute_replacement(
            old_token=old_token,
            new_token=new_token,
            method="uia",  # Subsequent cycles use backspace from caret
        )

    def _execute_replacement(self, old_token: str, new_token: str, method: str) -> None:
        """Safely executes text replacement while suppressing global keyboard hooks."""
        self.keyboard_manager.suppress_hooks = True
        try:
            if method == "fallback":
                # In fallback mode for 1st activation, text is selected in target app
                self.text_handler.type_string(new_token)
            else:
                # In UIA or subsequent cycles, cursor is immediately after old_token
                for _ in range(len(old_token)):
                    self.text_handler.keyboard_controller.tap(Key.backspace)
                    time.sleep(0.004)
                self.text_handler.type_string(new_token)
        finally:
            self.keyboard_manager.suppress_hooks = False
