"""Text preprocessing and tokenization utilities for TypoPilot NLP engines."""

from __future__ import annotations

import re
from typing import List, Tuple


def clean_and_normalize(text: str) -> str:
    """Normalizes whitespace and standardizes unicode apostrophes/quotes."""
    if not text:
        return ""
    # Standardize curly quotes and apostrophes to standard ASCII
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return text.strip()


def extract_words(text: str) -> List[str]:
    """Tokenizes text into individual words while preserving contractions (e.g. don't)."""
    clean = clean_and_normalize(text)
    # Match words and internal apostrophes/hyphens
    return re.findall(r"\b[\w'-]+\b", clean, re.UNICODE)


def get_preceding_word(context: str) -> str:
    """Extracts the immediate word prior to the target word from context string."""
    words = extract_words(context)
    return words[-1].lower() if words else ""
