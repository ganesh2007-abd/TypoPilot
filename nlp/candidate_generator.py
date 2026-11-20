"""Candidate generation engine using SymSpell (Symmetric Delete Edit Distance)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import pkg_resources
from symspellpy import SymSpell, Verbosity


@dataclass
class CandidateItem:
    """Represents a potential spelling correction candidate."""
    word: str
    edit_distance: int
    frequency: int
    score: float = 0.0


class CandidateGenerator:
    """Generates and ranks spelling correction candidates using SymSpell and word frequency."""

    def __init__(self, max_edit_distance: int = 2, prefix_length: int = 7):
        self.max_edit_distance = max_edit_distance
        self.prefix_length = prefix_length
        self.sym_spell = SymSpell(
            max_dictionary_edit_distance=self.max_edit_distance,
            prefix_length=self.prefix_length,
        )
        self._loaded = False
        self._load_dictionaries()

    def _load_dictionaries(self) -> None:
        """Loads the standard English frequency dictionary (82,765 words)."""
        if self._loaded:
            return

        dict_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_dictionary_en_82_765.txt"
        )
        # term_index=0, count_index=1
        self.sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
        self._loaded = True

    def is_known_word(self, word: str) -> bool:
        """Checks if a word is in the dictionary."""
        return word.lower() in self.sym_spell.words

    def generate(
        self,
        word: str,
        max_edit_distance: Optional[int] = None,
        max_suggestions: int = 5,
    ) -> List[CandidateItem]:
        """Generates ranked correction candidates for a target word.

        Returns candidates sorted primarily by edit distance, secondarily by frequency.
        """
        if not word:
            return []

        dist = max_edit_distance if max_edit_distance is not None else self.max_edit_distance
        clean_word = word.lower()

        suggestions = self.sym_spell.lookup(
            clean_word,
            Verbosity.ALL,  # Return all candidates within edit distance
            max_edit_distance=dist,
            include_unknown=False,
        )

        candidates: List[CandidateItem] = []
        for s in suggestions:
            # Skip if suggestion is identical to input word and user explicitly triggered correction
            # (unless it's the only one)
            candidates.append(
                CandidateItem(
                    word=s.term,
                    edit_distance=s.distance,
                    frequency=s.count,
                    score=float(s.count),
                )
            )

        # Sort primarily by edit distance (ascending), then by frequency (descending)
        candidates.sort(key=lambda c: (c.edit_distance, -c.frequency))

        # Filter out identical words if multiple candidates exist
        filtered = [c for c in candidates if c.word != clean_word]
        if not filtered and candidates:
            filtered = candidates

        return filtered[:max_suggestions]
