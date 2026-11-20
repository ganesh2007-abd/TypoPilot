"""Undo manager for TypoPilot.

Maintains history of active and completed corrections, allowing
instant restoration of original misspelled text or previous corrections.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional
from core.text_handler import DetectedWord


@dataclass
class CorrectionRecord:
    """Stores metadata about a single applied text replacement."""
    original_word: str
    replaced_word: str
    detected_token: DetectedWord
    timestamp: float = field(default_factory=time.time)


class UndoManager:
    """Manages undo history and active correction states."""

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self._history: List[CorrectionRecord] = []

    def record_correction(self, original: str, replaced: str, token: DetectedWord) -> None:
        """Pushes a completed correction to the undo stack."""
        record = CorrectionRecord(
            original_word=original,
            replaced_word=replaced,
            detected_token=token,
        )
        self._history.append(record)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def pop_last(self) -> Optional[CorrectionRecord]:
        """Pops and returns the most recent correction record."""
        return self._history.pop() if self._history else None

    def peek_last(self) -> Optional[CorrectionRecord]:
        """Returns the most recent correction record without removing it."""
        return self._history[-1] if self._history else None

    def clear(self) -> None:
        """Clears the history."""
        self._history.clear()
