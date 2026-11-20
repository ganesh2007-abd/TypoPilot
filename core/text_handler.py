"""Cursor-aware text detection and manipulation module for TypoPilot.

Implements Windows UI Automation TextPattern inspection for cursor-level
detection and a non-destructive clipboard backup/restore fallback.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional, Tuple
import uiautomation as auto
import pyperclip
from pynput.keyboard import Controller, Key


@dataclass
class DetectedWord:
    """Represents a word detected at or immediately before the cursor."""
    raw_word: str              # The extracted word characters (e.g. "recieved")
    full_token: str            # Token including any trailing punctuation (e.g. "recieved,")
    trailing_punctuation: str  # Any trailing punctuation (e.g. ",")
    leading_punctuation: str   # Any leading punctuation (e.g. "(")
    context_before: str = ""   # Preceding words for context-aware NLP ranking
    context_after: str = ""    # Subsequent words for context-aware NLP ranking
    method: str = "uia"        # "uia" or "fallback"


def split_word_and_punctuation(token: str) -> Tuple[str, str, str]:
    """Splits a raw token into (leading_punct, clean_word, trailing_punct).

    Example: '"recieved",' -> ('"', 'recieved', '",')
    """
    match = re.match(r"^([^\w]*)([\w\'-]+)([^\w]*)$", token, re.UNICODE)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return "", token.strip(), ""


class TextHandler:
    """Handles cursor-level text detection, selection, and non-destructive replacement."""

    def __init__(self):
        self.keyboard_controller = Controller()

    def get_focused_element(self) -> Optional[auto.Control]:
        """Returns the currently active / focused Windows control."""
        try:
            return auto.GetFocusedControl()
        except Exception:
            return None

    def is_secure_or_password_field(self, element: Optional[auto.Control] = None) -> bool:
        """Checks if the focused control is a password or secure field to protect user privacy."""
        if element is None:
            element = self.get_focused_element()
        if element is None:
            return False
        try:
            # Check native UIA IsPassword property
            if getattr(element, "IsPassword", False):
                return True
            # Also check control type or class name patterns
            control_type = getattr(element, "ControlTypeName", "")
            class_name = getattr(element, "ClassName", "").lower()
            if "password" in class_name or "secure" in class_name:
                return True
        except Exception:
            pass
        return False

    def detect_word_via_uia(self) -> Optional[DetectedWord]:
        """Attempts to detect the word immediately preceding the cursor using UI Automation TextPattern."""
        try:
            element = self.get_focused_element()
            if element is None or self.is_secure_or_password_field(element):
                return None

            pattern = element.GetPattern(auto.PatternId.TextPattern)
            if pattern is None:
                return None

            # Get selection range (a zero-length range represents the caret/cursor)
            selection = pattern.GetSelection()
            if not selection or len(selection) == 0:
                return None

            caret_range = selection[0]
            # Clone range to inspect text preceding caret
            doc_range = pattern.DocumentRange.Clone()

            # Move an inspection range back by up to 60 characters to capture preceding context
            inspect_range = caret_range.Clone()
            inspect_range.MoveEndpointByUnit(
                auto.TextPatternRangeEndpoint.Start,
                auto.TextUnit.Character,
                -60,
            )
            text_before = inspect_range.GetText(-1)

            if not text_before:
                return None

            # Find the last word token immediately before cursor
            tokens = text_before.split()
            if not tokens:
                return None

            last_token = tokens[-1]
            leading, clean_word, trailing = split_word_and_punctuation(last_token)

            if not clean_word or not clean_word[0].isalpha():
                return None

            # Context before is everything prior to the last token in text_before
            context_before = text_before[: -len(last_token)].strip()

            return DetectedWord(
                raw_word=clean_word,
                full_token=last_token,
                trailing_punctuation=trailing,
                leading_punctuation=leading,
                context_before=context_before,
                context_after="",
                method="uia",
            )
        except Exception:
            return None

    def detect_word_via_selection_fallback(self) -> Optional[DetectedWord]:
        """Fallback method: Selects the word preceding the cursor using Ctrl+Shift+Left,

        reads it via a non-destructive clipboard backup/restore, and returns the DetectedWord.
        """
        # Step 1: Backup existing clipboard content
        clipboard_backup = ""
        try:
            clipboard_backup = pyperclip.paste()
        except Exception:
            pass

        try:
            # Step 2: Select preceding word: Ctrl+Shift+Left
            # Press Ctrl+Shift+Left
            with self.keyboard_controller.pressed(Key.ctrl, Key.shift):
                self.keyboard_controller.tap(Key.left)
            time.sleep(0.04)

            # Step 3: Copy selected text: Ctrl+C
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.tap("c")
            time.sleep(0.04)

            selected_text = pyperclip.paste()

            # Validate that selected text is a valid single word (not whole paragraph/empty)
            if not selected_text or "\n" in selected_text or " " in selected_text.strip():
                # Deselect by pressing Right arrow to restore cursor
                self.keyboard_controller.tap(Key.right)
                return None

            leading, clean_word, trailing = split_word_and_punctuation(selected_text)
            if not clean_word or not any(c.isalpha() for c in clean_word):
                # Deselect and return cursor
                self.keyboard_controller.tap(Key.right)
                return None

            return DetectedWord(
                raw_word=clean_word,
                full_token=selected_text,
                trailing_punctuation=trailing,
                leading_punctuation=leading,
                context_before="",
                context_after="",
                method="fallback",
            )
        finally:
            # Step 4: Always restore the user's original clipboard content
            try:
                pyperclip.copy(clipboard_backup)
            except Exception:
                pass

    def detect_word_at_cursor(self) -> Optional[DetectedWord]:
        """Primary entry point: Attempts UIA detection first; falls back to selection if needed."""
        # Check security
        if self.is_secure_or_password_field():
            return None

        # Try UIA first
        word = self.detect_word_via_uia()
        if word is not None:
            return word

        # Fallback to selection-based word detection
        return self.detect_word_via_selection_fallback()

    def get_selected_text(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieves currently highlighted/selected text in the active window.

        Returns:
            Tuple of (selected_text, clipboard_backup_to_restore_later).
        """
        if self.is_secure_or_password_field():
            return None, None

        # 1. Try via UI Automation TextPattern (zero clipboard impact)
        try:
            element = self.get_focused_element()
            if element is not None:
                pattern = element.GetPattern(auto.PatternId.TextPattern)
                if pattern is not None:
                    selection = pattern.GetSelection()
                    if selection and len(selection) > 0:
                        text = selection[0].GetText(-1)
                        if text and text.strip():
                            # Successfully got selected text with 0 clipboard modification
                            return text, None
        except Exception:
            pass

        # 2. Universal fallback: Ctrl+C with clipboard backup
        clipboard_backup = ""
        try:
            clipboard_backup = pyperclip.paste()
        except Exception:
            pass

        try:
            # Tap Ctrl+C
            with self.keyboard_controller.pressed(Key.ctrl):
                self.keyboard_controller.tap("c")
            time.sleep(0.04)

            selected_text = pyperclip.paste()
            if selected_text and selected_text.strip():
                return selected_text, clipboard_backup
        except Exception:
            pass

        # If nothing was selected, restore clipboard immediately
        try:
            pyperclip.copy(clipboard_backup)
        except Exception:
            pass

        return None, None

    def replace_selected_text(self, new_text: str, clipboard_backup: Optional[str] = None) -> bool:
        """Replaces currently selected text with new_text and restores original clipboard."""
        if not new_text:
            return False

        orig_clipboard = clipboard_backup
        if orig_clipboard is None:
            try:
                orig_clipboard = pyperclip.paste()
            except Exception:
                orig_clipboard = ""

        try:
            # Copy new text to clipboard
            try:
                pyperclip.copy(new_text)
                time.sleep(0.02)
                # Paste into target application (Ctrl+V)
                with self.keyboard_controller.pressed(Key.ctrl):
                    self.keyboard_controller.tap("v")
                time.sleep(0.04)
                return True
            except Exception:
                # Fallback: if clipboard is locked or restricted, type directly
                self.type_string(new_text)
                return True
        finally:
            # Always restore user's original clipboard
            try:
                if orig_clipboard is not None:
                    pyperclip.copy(orig_clipboard)
            except Exception:
                pass

    def replace_word(self, detected: DetectedWord, new_word: str) -> bool:
        """Replaces the detected misspelled word with the new word,

        preserving original casing and trailing punctuation.
        """
        # Preserve capitalization
        cased_replacement = preserve_capitalization(detected.raw_word, new_word)
        final_token = f"{detected.leading_punctuation}{cased_replacement}{detected.trailing_punctuation}"

        # If detected via fallback, the word is currently selected in the target app!
        # Typing replacement or pasting replaces the selected text immediately.
        # If detected via UIA, we select backspace characters and insert.
        try:
            if detected.method == "fallback":
                # Text is currently selected, simply type replacement or paste
                self.type_string(final_token)
                return True
            else:
                # In UIA mode, cursor is after the word. Backspace the token length and type new word.
                chars_to_delete = len(detected.full_token)
                for _ in range(chars_to_delete):
                    self.keyboard_controller.tap(Key.backspace)
                    time.sleep(0.005)

                self.type_string(final_token)
                return True
        except Exception as e:
            print(f"[TypoPilot] Error during text replacement: {e}")
            return False

    def type_string(self, text: str) -> None:
        """Types a string into the currently focused window."""
        self.keyboard_controller.type(text)


def preserve_capitalization(original: str, candidate: str) -> str:
    """Matches the capitalization pattern of the original word onto the candidate.

    Examples:
        'recieve' -> 'receive' (all lowercase)
        'Recieve' -> 'Receive' (Title Case)
        'RECIEVE' -> 'RECEIVE' (ALL UPPERCASE)
    """
    if not original or not candidate:
        return candidate

    if original.isupper():
        return candidate.upper()
    elif original.istitle() or (original[0].isupper() and original[1:].islower()):
        return candidate.capitalize()
    return candidate.lower()
