"""Unified spelling correction engine for TypoPilot.

Combines Symmetric Delete candidate generation with N-gram context ranking.
"""

from __future__ import annotations

from typing import List, Optional

from config import TypoPilotConfig
from nlp.candidate_generator import CandidateGenerator, CandidateItem
from nlp.context_ranker import ContextRanker


class SpellChecker:
    """Coordinates word-level spelling candidate generation and contextual re-ranking."""

    def __init__(self, config: TypoPilotConfig):
        self.config = config
        self.generator = CandidateGenerator(
            max_edit_distance=self.config.max_edit_distance,
            prefix_length=self.config.prefix_length,
        )
        self.ranker = ContextRanker(sym_spell=self.generator.sym_spell)

    def is_correct(self, word: str) -> bool:
        """Returns True if the word is found in the dictionary."""
        return self.generator.is_known_word(word)

    def get_suggestions(
        self,
        word: str,
        context_before: str = "",
        max_suggestions: Optional[int] = None,
    ) -> List[str]:
        """Generates context-aware, ranked spelling suggestions for a word.

        Returns:
            A list of suggested replacement words (e.g. ['receive', 'relieve', ...])
        """
        limit = max_suggestions if max_suggestions is not None else self.config.max_suggestions

        # 1. Generate candidates within edit distance
        candidates = self.generator.generate(
            word=word,
            max_edit_distance=self.config.max_edit_distance,
            max_suggestions=limit * 2,  # Fetch slightly more to allow context re-ranking
        )

        if not candidates:
            return []

        # 2. Context-aware ranking if context is available
        if context_before:
            candidates = self.ranker.rank_candidates(candidates, context_before=context_before)

        # 3. Extract unique word list up to limit
        seen = set()
        unique_results: List[str] = []
        for c in candidates:
            if c.word not in seen:
                seen.add(c.word)
                unique_results.append(c.word)
            if len(unique_results) >= limit:
                break

        return unique_results
