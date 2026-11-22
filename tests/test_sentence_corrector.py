"""Unit tests for sentence-level grammar and spelling correction."""

import time
from config import TypoPilotConfig
from nlp.sentence_corrector import NeuralSentenceCorrector, SentenceCorrector
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


def test_complex_grammar_neural_correction():
    cfg = TypoPilotConfig()
    cfg.sentence_correction_enabled = True
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    # Ensure neural engine is loaded
    corrector.neural_engine.load_model()

    # 1. "it go well for me." -> "It goes well for me."
    res1 = corrector.correct_text("it go well for me.")
    assert "It goes well for me." in res1

    # 2. "she do not likes apples" -> "She does not like apples."
    res2 = corrector.correct_text("she do not likes apples")
    assert "She does not like apples" in res2

    # 3. "the dogs was barking outside." -> "The dogs were barking outside."
    res3 = corrector.correct_text("the dogs was barking outside.")
    assert "The dogs were barking outside." in res3

    # 4. "she has went to the market yesterday." -> "She went to the market yesterday."
    res4 = corrector.correct_text("she has went to the market yesterday.")
    assert "She went to the market yesterday." in res4


def test_quantization_and_cpu_latency():
    cfg = TypoPilotConfig()
    cfg.sentence_correction_enabled = True
    cfg.use_gpu_if_available = False  # Force CPU execution
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    # Verify model is dynamically quantized on CPU
    assert corrector.neural_engine.load_model() is True
    assert corrector.neural_engine._is_quantized is True
    assert corrector.neural_engine.device == "cpu"

    # Measure CPU latency (must be < 2500 ms on laptop CPU)
    t0 = time.perf_counter()
    res = corrector.correct_text("it go well for me.")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000

    assert latency_ms < 2500.0, f"Inference took {latency_ms:.2f} ms (expected < 2500 ms)"
    assert "It goes well for me." in res


def test_async_prewarm_and_fallback():
    cfg = TypoPilotConfig()
    cfg.sentence_correction_enabled = True
    checker = SpellChecker(cfg)
    corrector = SentenceCorrector(cfg, checker)

    # Verify preload_async spawns a background thread
    corrector.preload_async()
    assert corrector.neural_engine._loading_thread is not None

    # Test fallback to local engine if neural is disabled
    cfg.sentence_correction_enabled = False
    res = corrector.correct_text("He go to college every day.")
    assert "He goes to college every day." in res


def test_keyboard_manager_f3_trigger():
    """Verify that Fn + F3 (Key.f3) triggers sentence correction without blocking."""
    from pynput.keyboard import Key
    from core.keyboard_manager import KeyboardManager

    cfg = TypoPilotConfig()
    km = KeyboardManager(cfg)
    triggered = []
    km.on_sentence_correction = lambda: triggered.append("sentence_f3")

    km._on_press(Key.f3)
    time.sleep(0.05)
    assert triggered == ["sentence_f3"]
    km._busy = False
    km._on_release(Key.f3)
