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
        self.left_taps = 0

    def detect_word_at_cursor(self) -> Optional[DetectedWord]:
        return self.mock_detected

    def type_string(self, text: str) -> None:
        self.typed_strings.append(text)


class MockKeyboardController:
    def __init__(self, handler):
        self.handler = handler

    def tap(self, key):
        from pynput.keyboard import Key
        if key == Key.backspace:
            self.handler.backspaces_tapped += 1
        elif key == Key.left:
            self.handler.left_taps += 1

    def pressed(self, *keys):
        """Context manager that tracks Shift+Left selections."""
        return _MockPressed(self.handler, keys)


class _MockPressed:
    """Tracks Shift+Left presses for selection counting."""
    def __init__(self, handler, keys):
        self.handler = handler
        self.keys = keys
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


def test_undo_manager():
    um = UndoManager(max_history=5)
    token = DetectedWord("recieve", "recieve", "", "", "", "", 0, 0, "", "", "uia")

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

    # 2. Second press F2: Cycle to next suggestion
    first_candidate = cm._active_session.candidates[0]
    cm.handle_next_prediction()
    assert cm._active_session.current_index == 1
    second_candidate = cm._active_session.candidates[1]

    # 3. Press Shift+F2: Cycle back to previous suggestion
    cm.handle_prev_prediction()
    assert cm._active_session.current_index == 0

    # 4. Press Esc: Restore original misspelled word
    cm.handle_cancel_restore()
    assert cm._active_session is None  # Session cleared


def test_correct_word_is_skipped():
    """Verify that pressing F2 on an already correct word does nothing."""
    cfg = TypoPilotConfig(max_suggestions=3)
    km = KeyboardManager(cfg)

    # A correctly spelled word
    detected = DetectedWord(
        raw_word="receive",
        full_token="receive",
        trailing_punctuation="",
        leading_punctuation="",
        chars_to_delete=7,
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

    # F2 on a correct word should NOT create a session
    cm.handle_next_prediction()
    assert cm._active_session is None
    assert len(mock_handler.typed_strings) == 0


def test_cursor_moved_to_different_word_resets_session():
    """Verify that moving the cursor to a different word resets active cycling session."""
    cfg = TypoPilotConfig(max_suggestions=3)
    km = KeyboardManager(cfg)

    # Word 1: unforunately
    word1 = DetectedWord(
        raw_word="unforunately",
        full_token="unforunately",
        trailing_punctuation="",
        leading_punctuation="",
        context_before="accomodate seperate",
        context_after="",
        method="uia",
    )
    # Word 2: seperate
    word2 = DetectedWord(
        raw_word="seperate",
        full_token="seperate",
        trailing_punctuation="",
        leading_punctuation="",
        context_before="accomodate",
        context_after=" unforunately",
        method="uia",
    )

    mock_handler = MockTextHandler(word1)
    mock_handler.keyboard_controller = MockKeyboardController(mock_handler)

    cm = CorrectionManager(
        config=cfg,
        keyboard_manager=km,
        text_handler=mock_handler,
    )

    # 1. Press F2 on word 1 (unforunately)
    cm.handle_next_prediction()
    assert cm._active_session is not None
    assert cm._active_session.original_word == "unforunately"
    assert "unfortunately" in mock_handler.typed_strings[-1]

    # 2. User moves cursor backwards to word 2 (seperate)
    mock_handler.mock_detected = word2

    # 3. Press F2 on word 2 (seperate) within session timeout
    cm.handle_next_prediction()
    assert cm._active_session is not None
    # Session must now be for 'seperate', NOT cycling 'unforunately'
    assert cm._active_session.original_word == "seperate"
    assert "separate" in mock_handler.typed_strings[-1]
