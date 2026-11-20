"""Context-aware candidate ranking module for TypoPilot.

Uses N-gram (bigram) transition frequencies and language modelling
to rank candidate words given their preceding sentence context.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional
import pkg_resources
from symspellpy import SymSpell

from nlp.candidate_generator import CandidateItem
from nlp.text_preprocessor import get_preceding_word


class ContextRanker:
    """Ranks spelling candidates using edit distance, unigram frequency, and bigram context."""

    def __init__(self, sym_spell: Optional[SymSpell] = None):
        if sym_spell is not None:
            self.sym_spell = sym_spell
        else:
            self.sym_spell = SymSpell(max_dictionary_edit_distance=2)
            dict_path = pkg_resources.resource_filename(
                "symspellpy", "frequency_dictionary_en_82_765.txt"
            )
            self.sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)

        self._load_bigrams()

    def _load_bigrams(self) -> None:
        """Loads English bigram frequency dictionary (243,342 bigrams)."""
        if hasattr(self.sym_spell, "bigrams") and self.sym_spell.bigrams:
            return

        bigram_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_bigramdictionary_en_243_342.txt"
        )
        self.sym_spell.load_bigram_dictionary(bigram_path, term_index=0, count_index=2)

    def calculate_score(
        self,
        candidate: CandidateItem,
        preceding_word: str = "",
    ) -> float:
        """Calculates a composite NLP score for a candidate.

        Score components:
        1. Edit Distance Penalty: Lower edit distance gets higher baseline.
        2. Unigram Frequency: Log frequency of the word in English corpus.
        3. Bigram Context Boost: Log frequency of (preceding_word + candidate).
        """
        # Distance factor: penalty scales with distance (0 dist -> 1.0, 1 dist -> 0.6, 2 dist -> 0.3)
        dist_factor = 1.0 / (1.0 + candidate.edit_distance * 0.7)

        # Unigram score
        unigram_score = math.log10(max(candidate.frequency, 1))

        # Bigram context score
        bigram_boost = 0.0
        if preceding_word:
            bigram_term = f"{preceding_word.lower()} {candidate.word.lower()}"
            bigram_count = self.sym_spell.bigrams.get(bigram_term, 0)
            if bigram_count > 0:
                # Log scale for bigram count with higher weight
                bigram_boost = 2.5 * math.log10(bigram_count)

        # Composite score
        total_score = (dist_factor * unigram_score) + bigram_boost
        return total_score

    def rank_candidates(
        self,
        candidates: List[CandidateItem],
        context_before: str = "",
    ) -> List[CandidateItem]:
        """Re-ranks candidate words based on composite context scores."""
        if not candidates:
            return []

        prev_word = get_preceding_word(context_before)

        for cand in candidates:
            cand.score = self.calculate_score(cand, prev_word)

        # Sort by total composite score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates
