"""Unit tests for text detection, casing preservation, and word boundary splitting."""

from core.text_handler import DetectedWord, preserve_capitalization, split_word_and_punctuation


def test_split_word_and_punctuation():
    # Plain word
    leading, word, trailing = split_word_and_punctuation("recieved")
    assert leading == ""
    assert word == "recieved"
    assert trailing == ""

    # Trailing comma
    leading, word, trailing = split_word_and_punctuation("recieved,")
    assert leading == ""
    assert word == "recieved"
    assert trailing == ","

    # Enclosed in parentheses
    leading, word, trailing = split_word_and_punctuation("(definately)")
    assert leading == "("
    assert word == "definately"
    assert trailing == ")"

    # Word with apostrophe
    leading, word, trailing = split_word_and_punctuation("don't.")
    assert leading == ""
    assert word == "don't"
    assert trailing == "."


def test_preserve_capitalization():
    # Lowercase
    assert preserve_capitalization("recieve", "receive") == "receive"
    assert preserve_capitalization("teh", "the") == "the"

    # Title Case
    assert preserve_capitalization("Recieve", "receive") == "Receive"
    assert preserve_capitalization("Accomodate", "accommodate") == "Accommodate"

    # All Uppercase
    assert preserve_capitalization("RECIEVE", "receive") == "RECEIVE"
    assert preserve_capitalization("DEFINATELY", "definitely") == "DEFINITELY"

    # Mixed or empty
    assert preserve_capitalization("", "word") == "word"
    assert preserve_capitalization("word", "") == ""


def test_detected_word_model():
    dw = DetectedWord(
        raw_word="recieved",
        full_token="recieved,",
        trailing_punctuation=",",
        leading_punctuation="",
        context_before="I have",
        context_after="yesterday",
        method="uia",
    )
    assert dw.raw_word == "recieved"
    assert dw.full_token == "recieved,"
    assert dw.trailing_punctuation == ","
    assert dw.context_before == "I have"
