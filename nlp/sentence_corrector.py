"""Sentence and paragraph grammar correction module for TypoPilot.

Implements a dual-mode architecture:
1. Fast local rule & spelling pipeline (for zero-latency CPU execution).
2. Deep learning neural transformer adapter (ready for GPU workstations).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from config import TypoPilotConfig
from core.text_handler import preserve_capitalization
from nlp.spell_checker import SpellChecker


class BaseSentenceCorrector(ABC):
    """Abstract interface for sentence correction engines."""

    @abstractmethod
    def correct_text(self, text: str) -> str:
        """Corrects grammatical, spelling, and punctuation errors in the given text."""
        pass


class LocalRuleAndSpellingCorrector(BaseSentenceCorrector):
    """Zero-latency, offline grammar & spelling correction engine.

    Handles subject-verb agreement, common tense errors, spelling mistakes,
    and capitalization without requiring heavy neural dependencies.
    """

    def __init__(self, spell_checker: SpellChecker):
        self.spell_checker = spell_checker
        self._init_grammar_rules()

    def _init_grammar_rules(self) -> None:
        """Initializes regex patterns for common grammatical discrepancies."""
        # Common subject-verb agreement patterns (case-insensitive)
        self.agreement_rules: List[Tuple[re.Pattern, str]] = [
            # 3rd person singular + base verb
            (re.compile(r"\b(he|she|it)\s+go\b", re.IGNORECASE), r"\1 goes"),
            (re.compile(r"\b(he|she|it)\s+don't\b", re.IGNORECASE), r"\1 doesn't"),
            (re.compile(r"\b(he|she|it)\s+have\b", re.IGNORECASE), r"\1 has"),
            (re.compile(r"\b(he|she|it)\s+do\b", re.IGNORECASE), r"\1 does"),
            (re.compile(r"\b(he|she|it)\s+were\b", re.IGNORECASE), r"\1 was"),
            (re.compile(r"\b(he|she|it)\s+are\b", re.IGNORECASE), r"\1 is"),

            # Plural pronouns + singular verb
            (re.compile(r"\b(they|we|you)\s+was\b", re.IGNORECASE), r"\1 were"),
            (re.compile(r"\b(they|we|you)\s+has\b", re.IGNORECASE), r"\1 have"),
            (re.compile(r"\b(they|we|you)\s+is\b", re.IGNORECASE), r"\1 are"),
            (re.compile(r"\b(they|we|you)\s+does\b", re.IGNORECASE), r"\1 do"),
            (re.compile(r"\b(they|we|you)\s+doesn't\b", re.IGNORECASE), r"\1 don't"),

            # 1st person singular 'I'
            (re.compile(r"\b(I)\s+has\b", re.IGNORECASE), r"\1 have"),
            (re.compile(r"\b(I)\s+is\b", re.IGNORECASE), r"\1 am"),
            (re.compile(r"\b(I)\s+goes\b", re.IGNORECASE), r"\1 go"),
            (re.compile(r"\b(I)\s+doesn't\b", re.IGNORECASE), r"\1 don't"),

            # Adverbial "everyday" vs adjective "every day"
            (re.compile(r"\b(college|school|work|classes)\s+everyday\b", re.IGNORECASE), r"\1 every day"),
            (re.compile(r"\beveryday\s+and\s+attend\b", re.IGNORECASE), r"every day and attends"),
            (re.compile(r"\bevery day\s+and\s+attend\b", re.IGNORECASE), r"every day and attends"),
            (re.compile(r"\b(and)\s+attend\s+(classes|lectures|school)\b", re.IGNORECASE), r"\1 attends \2"),
        ]

    def correct_text(self, text: str) -> str:
        """Applies full spelling, grammar agreement, and punctuation correction."""
        if not text or not text.strip():
            return text

        # Step 1: Spelling correction across all tokens
        spelling_corrected = self._correct_spelling_in_sentence(text)

        # Step 2: Apply grammatical agreement rules
        grammar_corrected = spelling_corrected
        for pattern, replacement in self.agreement_rules:
            grammar_corrected = pattern.sub(self._rule_replacement_wrapper(replacement), grammar_corrected)

        # Step 3: Sentence casing and capitalization
        final_text = self._ensure_sentence_casing(grammar_corrected)
        return final_text

    def _rule_replacement_wrapper(self, replacement_template: str):
        """Helper to preserve the original casing of the matched pronoun."""
        def repl(match: re.Match) -> str:
            matched_str = match.group(0)
            result = match.expand(replacement_template)
            if matched_str[0].isupper():
                return result[0].upper() + result[1:]
            return result
        return repl

    def _correct_spelling_in_sentence(self, sentence: str) -> str:
        """Tokenizes and fixes spelling mistakes while preserving spaces and punctuation."""
        tokens = re.split(r"(\b[\w'-]+\b)", sentence, flags=re.UNICODE)
        result = []

        context_window: List[str] = []

        for token in tokens:
            if not token:
                continue

            # If it's a word token
            if any(c.isalpha() for c in token):
                clean_lower = token.lower()
                # Check if word is already correct
                if self.spell_checker.is_correct(clean_lower):
                    result.append(token)
                    context_window.append(token)
                else:
                    # Look up context-aware suggestions
                    context_before = " ".join(context_window[-3:])
                    suggestions = self.spell_checker.get_suggestions(
                        word=clean_lower,
                        context_before=context_before,
                        max_suggestions=1,
                    )
                    if suggestions:
                        cased = preserve_capitalization(token, suggestions[0])
                        result.append(cased)
                        context_window.append(cased)
                    else:
                        result.append(token)
                        context_window.append(token)
            else:
                # Punctuation / whitespace
                result.append(token)

        return "".join(result)

    def _ensure_sentence_casing(self, text: str) -> str:
        """Ensures that sentences begin with capital letters."""
        # Capitalize start of sentence following period/exclamation/question mark
        def cap(match: re.Match) -> str:
            prefix = match.group(1)
            letter = match.group(2)
            return f"{prefix}{letter.upper()}"

        # Beginning of text
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # After sentence boundary
        text = re.sub(r"([.!?]\s+)([a-z])", cap, text)
        return text


class NeuralSentenceCorrector(BaseSentenceCorrector):
    """Deep Learning Transformer Adapter for GPU workstations.

    Pre-configured to load Seq2Seq grammar error correction models
    (such as FLAN-T5 or T5-Grammar) when running on a GPU machine.
    """

    def __init__(self, model_name: str = "google/flan-t5-base", use_gpu: bool = True):
        self.model_name = model_name
        self.use_gpu = use_gpu
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        self._initialized = False

    def is_available(self) -> bool:
        """Checks if PyTorch and Transformers are installed."""
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def load_model(self) -> bool:
        """Lazy loads the transformer pipeline onto GPU/CPU."""
        if self._initialized:
            return True
        if not self.is_available():
            return False

        try:
            import torch
            from transformers import pipeline

            device = 0 if (self.use_gpu and torch.cuda.is_available()) else -1
            self._pipeline = pipeline(
                "text2text-generation",
                model=self.model_name,
                device=device,
            )
            self._initialized = True
            return True
        except Exception as e:
            print(f"[TypoPilot Neural] Failed to load transformer model: {e}")
            return False

    def correct_text(self, text: str) -> str:
        """Runs neural transformer inference."""
        if not self._initialized:
            if not self.load_model():
                return text

        try:
            prompt = f"grammar: {text.strip()}"
            outputs = self._pipeline(prompt, max_length=128, num_beams=4, early_stopping=True)
            if outputs and len(outputs) > 0:
                return outputs[0].get("generated_text", text)
        except Exception as e:
            print(f"[TypoPilot Neural] Inference error: {e}")
        return text


class SentenceCorrector(BaseSentenceCorrector):
    """Unified sentence corrector that routes between local rules and neural models."""

    def __init__(self, config: TypoPilotConfig, spell_checker: SpellChecker):
        self.config = config
        self.spell_checker = spell_checker
        self.local_engine = LocalRuleAndSpellingCorrector(spell_checker)
        self.neural_engine = NeuralSentenceCorrector(
            model_name=self.config.sentence_model_name,
            use_gpu=self.config.use_gpu_if_available,
        )

    def correct_text(self, text: str) -> str:
        """Executes correction using the best available engine."""
        # If neural engine is available and enabled
        if self.config.sentence_correction_enabled and self.neural_engine.is_available():
            result = self.neural_engine.correct_text(text)
            if result and result != text:
                return result

        # Default to local rule and spelling pipeline
        return self.local_engine.correct_text(text)
