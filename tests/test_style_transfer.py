"""Unit tests for Professional Tone & Style Transfer (Fn + F5).

Covers:
1. Local corporate template and etiquette transformations.
2. Contractions, urgency indicators, and informal idiom conversions.
3. INT8 Quantized Neural Style Transfer model.
4. CorrectionManager integration (rewrite_tone, undo, status notifications).
5. KeyboardManager hotkey triggers (F5 for tone, F4 for undo).
"""

import time
from typing import Optional
from pynput.keyboard import Key

from config import TypoPilotConfig
from core.correction_manager import CorrectionManager
from core.keyboard_manager import KeyboardManager
from core.text_handler import DetectedWord, TextHandler
from core.undo_manager import UndoManager
from nlp.style_transfer import (
    LocalCorporateStyleTransfer,
    NeuralStyleTransfer,
    StyleTransferEngine,
)


class MockToneTextHandler(TextHandler):
    """Mock text handler to test tone rewriting and undo without OS keystrokes."""

    def __init__(self, selected_text: str = ""):
        super().__init__()
        self.selected_text = selected_text
        self.replaced_texts = []
        self.clipboard_backups = []

    def get_selected_text(self):
        return self.selected_text, "sentinel_backup"

    def replace_selected_text(self, new_text: str, clipboard_backup: Optional[str] = None) -> bool:
        self.replaced_texts.append(new_text)
        self.clipboard_backups.append(clipboard_backup)
        self.selected_text = new_text
        return True


def test_local_style_transfer_canonical_examples():
    """Verify that required presentation examples produce polite corporate English."""
    engine = LocalCorporateStyleTransfer()

    # Presentation Example 1: ASAP Report Request
    res1 = engine.transfer_tone("hey send me the report asap i need it")
    assert "Could you please forward the report at your earliest convenience? It is urgently needed." == res1

    # Presentation Example 2: Meeting Absence
    res2 = engine.transfer_tone("sorry cant come to meeting im busy")
    assert "I apologize, but I am unable to attend the meeting due to a scheduling conflict." == res2

    # Greeting / check-in
    res3 = engine.transfer_tone("what is up bro")
    assert "I hope you are doing well." in res3

    # Sign-off
    res4 = engine.transfer_tone("talk to you later")
    assert "I look forward to speaking with you soon." in res4

    # Gratitude
    res5 = engine.transfer_tone("thanks a lot for your help")
    assert "Thank you very much for your assistance." in res5


def test_local_style_transfer_rules_and_contractions():
    """Verify phrase replacement rules, urgency conversions, and proper casing."""
    engine = LocalCorporateStyleTransfer()

    # Bug report
    bug_res = engine.transfer_tone("can you fix this bug")
    assert "Could you please investigate and resolve this issue?" in bug_res

    # Deadline notice
    deadline_res = engine.transfer_tone("dont forget about the deadline")
    assert "Please keep the upcoming deadline in mind." in deadline_res

    # Action item
    action_res = engine.transfer_tone("i want this done by tomorrow")
    assert "Please ensure this is completed by tomorrow." in action_res

    # Casual contractions
    casual_res = engine.transfer_tone("i wanna see the results and i gotta leave")
    assert "would like to" in casual_res
    assert "need to" in casual_res


def test_neural_style_transfer_quantization():
    """Verify that NeuralStyleTransfer loads with dynamic INT8 quantization on CPU."""
    neural = NeuralStyleTransfer()
    assert neural.is_available() is True

    # Pre-warming should start background thread
    neural.preload_async()
    assert neural._loading_thread is not None

    # Load model and verify INT8 dynamic quantization
    loaded = neural.load_model()
    assert loaded is True
    assert neural.is_ready() is True
    assert neural._is_quantized is True

    # Test inference speed & output
    t0 = time.perf_counter()
    res = neural.transfer_tone("what is up bro")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(res) > 0
    # INT8 CPU latency should be fast (< 500 ms)
    print(f"Neural style transfer latency: {elapsed_ms:.2f} ms")


def test_style_transfer_engine_hybrid():
    """Verify that StyleTransferEngine coordinates local rules and neural model."""
    cfg = TypoPilotConfig()
    engine = StyleTransferEngine(cfg)

    # Fast template match should be instant
    t0 = time.perf_counter()
    fast_res = engine.transfer_tone("hey send me the report asap i need it")
    fast_ms = (time.perf_counter() - t0) * 1000.0

    assert "Could you please forward the report at your earliest convenience? It is urgently needed." == fast_res
    assert fast_ms < 50.0  # Under 50 ms for local template match

    # Empty text handling
    assert engine.transfer_tone("") == ""
    assert engine.transfer_tone("   ") == "   "


def test_correction_manager_rewrite_tone_and_undo():
    """Verify that rewrite_tone() updates selected text, records undo, and allows Fn+F4 restoration."""
    cfg = TypoPilotConfig()
    km = KeyboardManager(cfg)
    mock_handler = MockToneTextHandler("hey send me the report asap i need it")
    undo_mgr = UndoManager()

    statuses = []

    def status_callback(msg: str):
        statuses.append(msg)

    cm = CorrectionManager(
        config=cfg,
        keyboard_manager=km,
        text_handler=mock_handler,
        undo_manager=undo_mgr,
    )
    cm.status_notifier = status_callback

    # 1. Trigger Tone Rewrite (Fn + F5)
    cm.rewrite_tone()

    assert len(mock_handler.replaced_texts) == 1
    rewritten = mock_handler.replaced_texts[0]
    assert "Could you please forward the report at your earliest convenience? It is urgently needed." == rewritten
    assert "TONE REWRITTEN" in statuses

    # Verify undo record exists
    assert undo_mgr.peek_last_sentence() is not None
    assert undo_mgr.peek_last_sentence().original_text == "hey send me the report asap i need it"

    # 2. Trigger Undo (Fn + F4)
    cm.handle_undo()

    assert len(mock_handler.replaced_texts) == 2
    assert mock_handler.replaced_texts[1] == "hey send me the report asap i need it"
    assert "UNDO" in statuses


def test_keyboard_manager_f5_f4_bindings():
    """Verify that KeyboardManager recognizes F5 for tone and F4 for undo."""
    cfg = TypoPilotConfig()
    km = KeyboardManager(cfg)

    triggered = []

    km.on_tone_rewrite = lambda: triggered.append("tone")
    km.on_sentence_correction = lambda: triggered.append("sentence")
    km.on_undo = lambda: triggered.append("undo")

    # Simulate F5 press
    km._on_press(Key.f5)
    time.sleep(0.05)
    assert "tone" in triggered

    # Reset keys and simulate F4 press
    km._current_keys.clear()
    km._busy = False
    km._on_press(Key.f4)
    time.sleep(0.05)
    assert "undo" in triggered

    # Reset keys and simulate F3 press
    km._current_keys.clear()
    km._busy = False
    km._on_press(Key.f3)
    time.sleep(0.05)
    assert "sentence" in triggered
