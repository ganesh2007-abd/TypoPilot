"""Unit tests for NLP spelling checker, candidate generation, and context ranking."""

from config import TypoPilotConfig
from nlp.candidate_generator import CandidateGenerator
from nlp.context_ranker import ContextRanker
from nlp.spell_checker import SpellChecker
from nlp.text_preprocessor import clean_and_normalize, extract_words, get_preceding_word


def test_text_preprocessor():
    assert clean_and_normalize("  hello ’world‘  ") == "hello 'world'"
    words = extract_words("I will recieve the document tomorrow, don't forget.")
    assert "recieve" in words
    assert "don't" in words

    assert get_preceding_word("I will") == "will"
    assert get_preceding_word("He said: ") == "said"


def test_core_test_words_correction():
    cfg = TypoPilotConfig()
    checker = SpellChecker(cfg)

    # Core required test cases from specification
    test_cases = {
        "recieve": "receive",
        "teh": "the",
        "accomodate": "accommodate",
        "definately": "definitely",
        "seperate": "separate",
    }

    for typo, expected in test_cases.items():
        suggestions = checker.get_suggestions(typo)
        assert len(suggestions) > 0, f"No suggestions for '{typo}'"
        assert suggestions[0] == expected, f"Expected '{expected}' for '{typo}', got '{suggestions[0]}'"


def test_multiple_suggestions_cycling_support():
    cfg = TypoPilotConfig(max_suggestions=5)
    checker = SpellChecker(cfg)

    # A typo that has multiple reasonable candidates (e.g. 'catt')
    suggestions = checker.get_suggestions("catt")
    assert len(suggestions) >= 2, "Should return multiple suggestions for cycling"


def test_context_aware_ranking():
    cfg = TypoPilotConfig()
    checker = SpellChecker(cfg)

    # Context: "I will recieve" -> bigram "will receive" should be strongly boosted
    suggestions_with_context = checker.get_suggestions(
        word="recieve",
        context_before="I will",
    )
    assert suggestions_with_context[0] == "receive"
