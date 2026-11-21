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
from nlp.sentence_corrector import SentenceCorrector
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
        self.keyboard_manager.on_sentence_correction = self.handle_sentence_correction

        # Sentence corrector engine (Dual-mode: local CPU rules + GPU neural adapter)
        self.sentence_corrector = SentenceCorrector(self.config, self.spell_checker)

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
            print("[TypoPilot] Key received, but TypoPilot is disabled in config.")
            return

        with self._lock:
            # Case 1: Already cycling an active word
            if self._is_session_valid():
                session = self._active_session
                assert session is not None
                new_index = (session.current_index + 1) % len(session.candidates)
                print(f"[TypoPilot] Cycling candidate: '{session.candidates[new_index]}'")
                self._apply_candidate(session, new_index)
                return

            # Case 2: New correction activation at cursor
            detected = self.text_handler.detect_word_at_cursor()
            if detected is None:
                print("[TypoPilot] F2 pressed, but no word detected at cursor.")
                return

            print(f"[TypoPilot] Detected word at cursor: '{detected.raw_word}' (Method: {detected.method})")

            # Guard: skip if the word is already correctly spelled
            if self.spell_checker.is_correct(detected.raw_word):
                print(f"[TypoPilot] '{detected.raw_word}' is already correct. Skipping.")
                # If word was selected in fallback mode, restore cursor position
                if detected.method == "fallback":
                    self.text_handler.keyboard_controller.tap(Key.right)
                return

            # Query NLP suggestions with preceding context
            suggestions = self.spell_checker.get_suggestions(
                word=detected.raw_word,
                context_before=detected.context_before,
                max_suggestions=self.config.max_suggestions,
            )

            if not suggestions:
                if detected.method == "fallback":
                    self.text_handler.keyboard_controller.tap(Key.right)
                return

            # Build the clean replacement token
            cased = preserve_capitalization(detected.raw_word, suggestions[0])
            first_clean_token = (
                f"{detected.leading_punctuation}"
                f"{cased}"
                f"{detected.trailing_punctuation}"
                f"{detected.trailing_whitespace}"
            )
            # In fallback mode, the Windows selection captured leading_whitespace,
            # so the replacement typed over the selection includes it to avoid eating spaces.
            first_typed_token = f"{detected.leading_whitespace}{first_clean_token}"

            # Create new session
            # Note: last_replaced_token stores the clean token so cycling only deletes the word!
            session = ActiveSession(
                original_word=detected.raw_word,
                detected_token=detected,
                candidates=suggestions,
                current_index=0,
                last_replaced_token=first_clean_token,
                last_active_time=time.time(),
            )
            self._active_session = session

            # Record in undo history
            self.undo_manager.record_correction(
                original=detected.raw_word,
                replaced=suggestions[0],
                token=detected,
            )

            # Perform replacement in target application
            self._execute_replacement(
                old_token=detected.full_token,
                new_token=first_typed_token if detected.method == "fallback" else first_clean_token,
                method=detected.method,
                chars_to_delete=detected.chars_to_delete,
                chars_after_cursor=detected.chars_after_cursor,
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

            # Build original token to restore
            orig_token = (
                f"{session.detected_token.leading_punctuation}"
                f"{session.original_word}"
                f"{session.detected_token.trailing_punctuation}"
                f"{session.detected_token.trailing_whitespace}"
            )

            # Replace current candidate with original token
            self._execute_replacement(
                old_token=session.last_replaced_token,
                new_token=orig_token,
                method="uia",
            )

            # Reset active session
            self._active_session = None

    def handle_sentence_correction(self) -> None:
        """Handles Ctrl+F2 (Sentence / Paragraph Correction)."""
        if not self.config.enabled:
            return

        with self._lock:
            # 1. Retrieve highlighted / selected text
            selected_text, clip_backup = self.text_handler.get_selected_text()
            if not selected_text or not selected_text.strip():
                return

            corrected_text = selected_text

            # 2. If dedicated sentence corrector is registered (Phase 8), run it
            if self.sentence_corrector is not None:
                try:
                    corrected_text = self.sentence_corrector.correct_text(selected_text)
                except Exception as e:
                    print(f"[TypoPilot] Sentence correction error: {e}")
                    return
            else:
                # Baseline multi-word spelling pass on selected text
                corrected_text = self._correct_sentence_spelling(selected_text)

            if not corrected_text or corrected_text == selected_text:
                return

            # 3. Store in undo history
            self.undo_manager.record_sentence_correction(
                original=selected_text,
                corrected=corrected_text,
            )

            # 4. Safely replace selected text while suppressing keyboard hooks
            self.keyboard_manager.suppress_hooks = True
            try:
                self.text_handler.replace_selected_text(
                    new_text=corrected_text,
                    clipboard_backup=clip_backup,
                )
            finally:
                self.keyboard_manager.suppress_hooks = False

    def _correct_sentence_spelling(self, text: str) -> str:
        """Baseline sentence tokenizer that fixes misspelled words within selected text."""
        import re
        tokens = re.split(r"(\w+)", text)
        result = []
        for token in tokens:
            if token.isalpha() and not self.spell_checker.is_correct(token):
                suggestions = self.spell_checker.get_suggestions(token, max_suggestions=1)
                if suggestions:
                    cased = preserve_capitalization(token, suggestions[0])
                    result.append(cased)
                else:
                    result.append(token)
            else:
                result.append(token)
        return "".join(result)

    def _apply_candidate(self, session: ActiveSession, new_index: int) -> None:
        """Replaces the currently displayed candidate with the candidate at new_index."""
        candidate = session.candidates[new_index]
        cased = preserve_capitalization(session.original_word, candidate)
        new_token = (
            f"{session.detected_token.leading_punctuation}"
            f"{cased}"
            f"{session.detected_token.trailing_punctuation}"
            f"{session.detected_token.trailing_whitespace}"
        )

        old_token = session.last_replaced_token

        session.current_index = new_index
        session.last_replaced_token = new_token
        session.last_active_time = time.time()

        self._execute_replacement(
            old_token=old_token,
            new_token=new_token,
            method="uia",  # Subsequent cycles: cursor is at end of last replacement
        )

    def _execute_replacement(
        self,
        old_token: str,
        new_token: str,
        method: str,
        chars_to_delete: int = 0,
        chars_after_cursor: int = 0,
    ) -> None:
        """Safely executes text replacement with proper timing to prevent character collisions."""
        self.keyboard_manager.suppress_hooks = True
        try:
            if method == "fallback":
                # In fallback mode for 1st activation, text is selected in target app
                self.text_handler.type_string(new_token)
            else:
                # In UIA or subsequent cycles:
                # If caret is inside word, move cursor right to the end of the word first
                if chars_after_cursor > 0:
                    for _ in range(chars_after_cursor):
                        self.text_handler.keyboard_controller.tap(Key.right)
                        time.sleep(0.01)

                # Delete old token with reliable keystroke timing
                num_deletions = chars_to_delete if chars_to_delete > 0 else len(old_token)
                for _ in range(num_deletions):
                    self.text_handler.keyboard_controller.tap(Key.backspace)
                    time.sleep(0.012)

                # Brief settle delay so the target window message loop updates the caret
                time.sleep(0.035)

                self.text_handler.type_string(new_token)
        finally:
            self.keyboard_manager.suppress_hooks = False
