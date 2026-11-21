"""Unit tests for the global keyboard manager."""

from pynput.keyboard import Key, KeyCode
from config import TypoPilotConfig
from core.keyboard_manager import KeyboardManager, normalize_key, parse_hotkey_string


def test_parse_hotkeys():
    f2_keys = parse_hotkey_string("F2")
    assert Key.f2 in f2_keys

    shift_f2_keys = parse_hotkey_string("Shift+F2")
    assert Key.shift in shift_f2_keys
    assert Key.f2 in shift_f2_keys

    ctrl_f2_keys = parse_hotkey_string("Ctrl+F2")
    assert Key.ctrl_l in ctrl_f2_keys
    assert Key.f2 in ctrl_f2_keys

    esc_keys = parse_hotkey_string("Esc")
    assert Key.esc in esc_keys


def test_normalize_key():
    assert normalize_key(Key.ctrl_r) == Key.ctrl_l
    assert normalize_key(Key.alt_r) == Key.alt_l
    assert normalize_key(Key.shift_r) == Key.shift
    assert normalize_key(Key.f2) == Key.f2


def test_keyboard_manager_matching_and_priority():
    cfg = TypoPilotConfig()
    km = KeyboardManager(cfg)

    triggered = []

    km.on_word_correction_next = lambda: triggered.append("next")
    km.on_word_correction_prev = lambda: triggered.append("prev")
    km.on_sentence_correction = lambda: triggered.append("sentence")
    km.on_cancel_restore = lambda: triggered.append("cancel")

    import time

    # 1. Test next candidate (bare F2)
    km._on_press(Key.f2)
    time.sleep(0.05)
    assert triggered == ["next"]
    # Simulate callback finished by clearing _busy
    km._busy = False
    km._on_release(Key.f2)

    # 2. Test previous candidate (Shift + F2)
    triggered.clear()
    km._on_press(Key.shift)
    km._on_press(Key.f2)
    time.sleep(0.05)
    assert triggered == ["prev"]
    km._busy = False
    km._on_release(Key.f2)
    km._on_release(Key.shift)

    # 3. Test cancel (Esc)
    triggered.clear()
    km._on_press(Key.esc)
    time.sleep(0.05)
    assert triggered == ["cancel"]
    km._busy = False
    km._on_release(Key.esc)

    # 4. Test suppression
    triggered.clear()
    km.suppress_hooks = True
    km._on_press(Key.f2)
    time.sleep(0.05)
    assert triggered == []
    km.suppress_hooks = False

    # 5. Test disabled config
    triggered.clear()
    cfg.enabled = False
    km._on_press(Key.f2)
    time.sleep(0.05)
    assert triggered == []

    # 6. Test _busy prevents duplicate triggers
    cfg.enabled = True
    triggered.clear()
    km._busy = True
    km._on_press(Key.f2)
    time.sleep(0.05)
    assert triggered == []  # Blocked because _busy is True
    km._busy = False

    # 7. Test _on_release works even during suppress (key tracking)
    km._current_keys.clear()
    km.suppress_hooks = True
    km._on_press(Key.f2)      # ignored, not added to _current_keys
    km._current_keys.add(Key.f2)  # simulate it being there
    km._on_release(Key.f2)    # should still remove from _current_keys
    assert Key.f2 not in km._current_keys  # Key properly cleaned up
    km.suppress_hooks = False
