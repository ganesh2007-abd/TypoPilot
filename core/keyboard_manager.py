"""Global Keyboard Shortcut Manager for TypoPilot.

Listens for user-configured hotkeys across all active Windows applications
using low-level hooks while avoiding infinite loops from simulated typing.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Set
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from config import TypoPilotConfig


def parse_hotkey_string(hotkey_str: str) -> Set[Key | KeyCode]:
    """Parses human-readable shortcut string (e.g. 'Shift+F2', 'Ctrl+F2', 'Esc')

    into a set of pynput Key / KeyCode items.
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
    key_set: Set[Key | KeyCode] = set()

    modifier_map = {
        "ctrl": Key.ctrl_l,  # we also handle right ctrl in matching
        "control": Key.ctrl_l,
        "alt": Key.alt_l,
        "shift": Key.shift,
        "esc": Key.esc,
        "escape": Key.esc,
    }

    # Special function keys
    for i in range(1, 25):
        modifier_map[f"f{i}"] = getattr(Key, f"f{i}", None)

    for part in parts:
        if part in modifier_map and modifier_map[part] is not None:
            key_set.add(modifier_map[part])
        elif len(part) == 1:
            key_set.add(KeyCode.from_char(part))
        else:
            # Try getting named key from pynput.keyboard.Key
            try:
                named_key = getattr(Key, part, None)
                if named_key is not None:
                    key_set.add(named_key)
                else:
                    key_set.add(KeyCode.from_char(part))
            except Exception:
                pass

    return key_set


def normalize_key(key: Key | KeyCode | None) -> Key | KeyCode | None:
    """Normalizes left/right modifier variants so Ctrl_L and Ctrl_R match 'ctrl'."""
    if key in (Key.ctrl_l, Key.ctrl_r):
        return Key.ctrl_l
    if key in (Key.alt_l, Key.alt_r, Key.alt_gr):
        return Key.alt_l
    if key in (Key.shift_l, Key.shift_r):
        return Key.shift
    return key


class KeyboardManager:
    """Manages global keyboard listeners and dispatches TypoPilot hotkey events."""

    def __init__(self, config: TypoPilotConfig):
        self.config = config
        self._listener: keyboard.Listener | None = None
        self._current_keys: Set[Key | KeyCode] = set()
        self._lock = threading.Lock()

        # Flag to prevent handling keystrokes generated synthetically by TypoPilot
        self.suppress_hooks = False

        # Callbacks
        self.on_word_correction_next: Callable[[], None] | None = None
        self.on_word_correction_prev: Callable[[], None] | None = None
        self.on_sentence_correction: Callable[[], None] | None = None
        self.on_cancel_restore: Callable[[], None] | None = None

        # Key state tracking to prevent repeated triggers on key-hold
        self._active_triggered_action: str | None = None
        self._last_trigger_time: float = 0.0
        self._debounce_interval: float = 0.15  # seconds debounce to avoid typematic repeats

        self._hotkey_bindings: Dict[str, Set[Key | KeyCode]] = {}
        self.reload_bindings()

    def reload_bindings(self) -> None:
        """Parses current hotkey configurations from config."""
        with self._lock:
            self._hotkey_bindings = {
                "next": parse_hotkey_string(self.config.word_correction_shortcut),
                "prev": parse_hotkey_string(self.config.word_correction_prev_shortcut),
                "sentence": parse_hotkey_string(self.config.sentence_correction_shortcut),
                "cancel": parse_hotkey_string(self.config.cancel_shortcut),
            }

    def start(self) -> None:
        """Starts the global background keyboard listener."""
        if self._listener is not None and self._listener.is_alive():
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        """Stops the global keyboard listener."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        with self._lock:
            self._current_keys.clear()
            self._active_triggered_action = None

    def _matches_binding(self, binding_keys: Set[Key | KeyCode]) -> bool:
        """Checks if all keys in the target binding are currently held down."""
        if not binding_keys:
            return False
        # Normalize currently pressed keys
        normalized_pressed = {normalize_key(k) for k in self._current_keys if k is not None}
        return binding_keys.issubset(normalized_pressed)

    def _on_press(self, raw_key: Key | KeyCode | None) -> None:
        """Internal callback when a key is physically pressed."""
        if self.suppress_hooks or not self.config.enabled:
            return

        normalized = normalize_key(raw_key)
        if normalized is None:
            return

        with self._lock:
            self._current_keys.add(normalized)

            now = time.time()

            # Check if any action matched (check more specific modifiers first)
            # Priority 1: Sentence correction (usually Ctrl+F2)
            if self._matches_binding(self._hotkey_bindings.get("sentence", set())):
                if self._active_triggered_action != "sentence":
                    if (now - self._last_trigger_time) < self._debounce_interval:
                        return
                    self._active_triggered_action = "sentence"
                    self._last_trigger_time = now
                    self._trigger_callback(self.on_sentence_correction)
                return

            # Priority 2: Word correction previous (usually Shift+F2)
            if self._matches_binding(self._hotkey_bindings.get("prev", set())):
                if self._active_triggered_action != "prev":
                    if (now - self._last_trigger_time) < self._debounce_interval:
                        return
                    self._active_triggered_action = "prev"
                    self._last_trigger_time = now
                    self._trigger_callback(self.on_word_correction_prev)
                return

            # Priority 3: Word correction next / activate (usually F2)
            if self._matches_binding(self._hotkey_bindings.get("next", set())):
                if self._active_triggered_action != "next":
                    if (now - self._last_trigger_time) < self._debounce_interval:
                        return
                    self._active_triggered_action = "next"
                    self._last_trigger_time = now
                    self._trigger_callback(self.on_word_correction_next)
                return

            # Priority 4: Cancel / Restore original (usually Esc)
            if self._matches_binding(self._hotkey_bindings.get("cancel", set())):
                if self._active_triggered_action != "cancel":
                    if (now - self._last_trigger_time) < self._debounce_interval:
                        return
                    self._active_triggered_action = "cancel"
                    self._last_trigger_time = now
                    self._trigger_callback(self.on_cancel_restore)
                return

    def _on_release(self, raw_key: Key | KeyCode | None) -> None:
        """Internal callback when a key is released."""
        if self.suppress_hooks:
            return

        normalized = normalize_key(raw_key)
        with self._lock:
            if normalized in self._current_keys:
                self._current_keys.discard(normalized)

            # Always clear active triggered action on key release so next press responds
            self._active_triggered_action = None

    def _trigger_callback(self, callback: Callable[[], None] | None) -> None:
        """Executes the action callback in a separate thread so listener is never blocked."""
        if callback is not None:
            threading.Thread(target=callback, daemon=True).start()
