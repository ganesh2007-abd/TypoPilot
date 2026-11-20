"""Unit tests for sentence-level grammar and spelling correction."""

from config import TypoPilotConfig
from nlp.sentence_corrector import SentenceCorrector
from nlp.spell_checker import SpellChecker


def test_core_sentence_grammar_corrections():
    cfg = TypoPilotConfig()
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    # 1. Subject-verb agreement (3rd person singular)
    res1 = corrector.correct_text("He go to college every day.")
    assert "He goes to college every day." in res1

    # 2. Contraction agreement (She don't -> She doesn't)
    res2 = corrector.correct_text("She don't like mathematics.")
    assert "She doesn't like mathematics." in res2

    # 3. Plural past tense (They was -> They were)
    res3 = corrector.correct_text("They was playing football.")
    assert "They were playing football." in res3

    # 4. First person present perfect (I has -> I have)
    res4 = corrector.correct_text("I has completed my assignment.")
    assert "I have completed my assignment." in res4

    # 5. Compound sentence with adverbial "everyday" and coordination
    res5 = corrector.correct_text("He go to college everyday and attend classes regularly.")
    assert "He goes to college every day and attends classes regularly." in res5


def test_sentence_with_spelling_mistakes():
    cfg = TypoPilotConfig()
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    sentence = "I will recieve the documnts tomorrow."
    corrected = corrector.correct_text(sentence)
    assert "receive" in corrected
    assert "documents" in corrected


def test_preserve_sentence_meaning_and_punctuation():
    cfg = TypoPilotConfig()
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    clean_sentence = "This is an already perfectly written sentence!"
    assert corrector.correct_text(clean_sentence) == clean_sentence
