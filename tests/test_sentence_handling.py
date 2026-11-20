"""Unit tests for selected text detection, sentence records, and replacement."""

from config import TypoPilotConfig
from core.correction_manager import CorrectionManager
from core.keyboard_manager import KeyboardManager
from core.text_handler import TextHandler
from core.undo_manager import UndoManager


class MockSentenceTextHandler(TextHandler):
    def __init__(self, selected_text: str = ""):
        super().__init__()
        self.mock_selected = selected_text
        self.replaced_texts = []

    def get_selected_text(self):
        return self.mock_selected, "original_clipboard_data"

    def replace_selected_text(self, new_text: str, clipboard_backup: str = None) -> bool:
        self.replaced_texts.append(new_text)
        return True


def test_sentence_undo_manager():
    um = UndoManager()
    um.record_sentence_correction(
        original="He go to college.",
        corrected="He goes to college.",
    )
    assert len(um._sentence_history) == 1
    last = um.peek_last_sentence()
    assert last.original_text == "He go to college."
    assert last.corrected_text == "He goes to college."

    popped = um.pop_last_sentence()
    assert popped.original_text == "He go to college."
    assert len(um._sentence_history) == 0


def test_selected_text_baseline_spelling_pass():
    cfg = TypoPilotConfig()
    km = KeyboardManager(cfg)
    mock_handler = MockSentenceTextHandler("I will recieve the documnts tomorrow.")

    cm = CorrectionManager(
        config=cfg,
        keyboard_manager=km,
        text_handler=mock_handler,
    )

    # Trigger sentence correction
    cm.handle_sentence_correction()

    assert len(mock_handler.replaced_texts) == 1
    # "recieve" should be corrected to "receive"
    assert "receive" in mock_handler.replaced_texts[0]
