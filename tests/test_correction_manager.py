"""Unit tests for the correction manager, cycling, and undo system."""

from typing import Optional
from config import TypoPilotConfig
from core.correction_manager import CorrectionManager
from core.keyboard_manager import KeyboardManager
from core.text_handler import DetectedWord, TextHandler
from core.undo_manager import UndoManager
from nlp.spell_checker import SpellChecker


class MockTextHandler(TextHandler):
    """Mock text handler to test replacement and cycling in-memory without OS keystrokes."""

    def __init__(self, detected_word: Optional[DetectedWord] = None):
        super().__init__()
        self.mock_detected = detected_word
        self.typed_strings = []
        self.backspaces_tapped = 0

    def detect_word_at_cursor(self) -> Optional[DetectedWord]:
        return self.mock_detected

    def type_string(self, text: str) -> None:
        self.typed_strings.append(text)


class MockKeyboardController:
    def __init__(self, handler):
        self.handler = handler

    def tap(self, key):
        self.handler.backspaces_tapped += 1


def test_undo_manager():
    um = UndoManager(max_history=5)
    token = DetectedWord("recieve", "recieve", "", "", "", "", "uia")

    um.record_correction("recieve", "receive", token)
    assert len(um._history) == 1
    assert um.peek_last().original_word == "recieve"

    popped = um.pop_last()
    assert popped.replaced_word == "receive"
    assert len(um._history) == 0


def test_correction_manager_cycling_and_restore():
    cfg = TypoPilotConfig(max_suggestions=5)
    km = KeyboardManager(cfg)

    # Initial typo token
    detected = DetectedWord(
        raw_word="recieve",
        full_token="recieve,",
        trailing_punctuation=",",
        leading_punctuation="",
        context_before="I will",
        context_after="",
        method="uia",
    )

    mock_handler = MockTextHandler(detected)
    mock_handler.keyboard_controller = MockKeyboardController(mock_handler)

    cm = CorrectionManager(
        config=cfg,
        keyboard_manager=km,
        text_handler=mock_handler,
    )

    # 1. First press F2: Initial correction
    cm.handle_next_prediction()
    assert cm._active_session is not None
    assert cm._active_session.original_word == "recieve"
    assert cm._active_session.current_index == 0
    # Suggestions should start with "receive"
    assert cm._active_session.candidates[0] == "receive"
    assert mock_handler.typed_strings[-1] == "receive,"

    # 2. Second press F2: Cycle to next suggestion
    first_candidate = cm._active_session.candidates[0]
    cm.handle_next_prediction()
    assert cm._active_session.current_index == 1
    second_candidate = cm._active_session.candidates[1]
    assert mock_handler.typed_strings[-1] == f"{second_candidate},"

    # 3. Press Shift+F2: Cycle back to previous suggestion
    cm.handle_prev_prediction()
    assert cm._active_session.current_index == 0
    assert mock_handler.typed_strings[-1] == f"{first_candidate},"

    # 4. Press Esc: Restore original misspelled word
    cm.handle_cancel_restore()
    assert cm._active_session is None  # Session cleared
    assert mock_handler.typed_strings[-1] == "recieve,"  # Restored!


def test_correction_preserves_surrounding_whitespace():
    """Verify that spacing before and after the misspelled word is strictly preserved."""
    cfg = TypoPilotConfig(max_suggestions=3)
    km = KeyboardManager(cfg)

    # Word preceded by space and followed by space (e.g. "I will recieve ")
    detected = DetectedWord(
        raw_word="recieve",
        full_token="recieve",
        trailing_punctuation="",
        leading_punctuation="",
        leading_whitespace=" ",
        trailing_whitespace=" ",
        chars_to_delete=9,
        chars_after_cursor=0,
        context_before="I will",
        context_after="",
        method="uia",
    )

    mock_handler = MockTextHandler(detected)
    mock_handler.keyboard_controller = MockKeyboardController(mock_handler)

    cm = CorrectionManager(
        config=cfg,
        keyboard_manager=km,
        text_handler=mock_handler,
    )

    # First F2 activation
    cm.handle_next_prediction()
    assert mock_handler.typed_strings[-1] == " receive "
    assert mock_handler.backspaces_tapped == 9

    # Cycle F2
    cm.handle_next_prediction()
    second_candidate = cm._active_session.candidates[1]
    assert mock_handler.typed_strings[-1] == f" {second_candidate} "

    # Esc restoration
    cm.handle_cancel_restore()
    assert mock_handler.typed_strings[-1] == " recieve "

