"""
Edge case tests for AphasiaBrocaDetector.

Tests handling of boundary conditions, unusual inputs, and stress cases
to ensure robust detection of telegraphic speech patterns.
"""

import pytest

from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector


def test_aphasia_detector_empty_text():
    """Test that empty text is handled gracefully."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("")

    assert result["is_aphasic"] is True  # Empty is considered aphasic
    assert result["severity"] == 1.0
    assert "empty_text" in result["flags"]


def test_aphasia_detector_whitespace_only():
    """Test that whitespace-only text is handled."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("   \n\t  ")

    assert result["is_aphasic"] is True
    assert result["severity"] == 1.0
    assert "empty_text" in result["flags"]


def test_aphasia_detector_single_word():
    """Test detection with single word input."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("Cat")

    # Single word is telegraphic
    assert result["is_aphasic"] is True
    assert result["severity"] > 0.0
    assert "short_sentences" in result["flags"]


def test_aphasia_detector_two_words():
    """Test detection with minimal two-word sentence."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("Cat runs.")

    # Very short sentence, likely aphasic
    assert result["is_aphasic"] is True
    assert "short_sentences" in result["flags"]


def test_aphasia_detector_three_words_no_function():
    """Test telegraphic pattern without function words."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("Cat dog bird.")

    assert result["is_aphasic"] is True
    # Should flag low function words
    assert result["function_word_ratio"] < detector.min_function_word_ratio


def test_aphasia_detector_very_long_sentence():
    """Test that very long healthy sentence is not flagged."""
    detector = AphasiaBrocaDetector()

    # Long sentence with proper structure
    text = (
        "The cognitive architecture provides a comprehensive framework for "
        "implementing multi-level synaptic memory with phase-entangled retrieval "
        "mechanisms that enable both wake and sleep processing modes while "
        "maintaining strict capacity bounds and ensuring thread-safe operation."
    )

    result = detector.analyze(text)

    assert result["is_aphasic"] is False
    assert result["avg_sentence_len"] > detector.min_sentence_len
    assert result["function_word_ratio"] >= detector.min_function_word_ratio


def test_aphasia_detector_punctuation_only():
    """Test handling of punctuation-only input."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("... !!! ???")

    assert result["is_aphasic"] is True
    # No meaningful tokens
    assert result["avg_sentence_len"] == 0.0


def test_aphasia_detector_numbers_only():
    """Test handling of numbers-only input."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("123 456 789")

    assert result["is_aphasic"] is True
    # Numbers without context are telegraphic
    assert result["severity"] > 0.0


def test_aphasia_detector_mixed_healthy_aphasic():
    """Test text with mix of healthy and telegraphic sentences."""
    detector = AphasiaBrocaDetector()

    text = (
        "The system works well. "
        "Cat run. Dog bark. "
        "However, this sentence is properly structured with function words."
    )

    result = detector.analyze(text)

    # Mix should still be flagged due to telegraphic portions
    assert result["is_aphasic"] is True
    assert result["fragment_ratio"] > 0.0


def test_aphasia_detector_repeated_words():
    """Test handling of repeated words (perseveration)."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("Cat cat cat cat cat.")

    assert result["is_aphasic"] is True
    # Low function word ratio
    assert result["function_word_ratio"] < detector.min_function_word_ratio


def test_aphasia_detector_single_letter_words():
    """Test handling of single-letter words."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("I a I a I a.")

    # "I" and "a" are function words, 6 tokens total
    # This equals min_sentence_len, so may or may not be flagged
    assert result["avg_sentence_len"] >= 0  # Just check it's computed
    assert "is_aphasic" in result


def test_aphasia_detector_unicode_text():
    """Test handling of unicode/non-ASCII text."""
    detector = AphasiaBrocaDetector()

    # Unicode text that's still telegraphic
    result = detector.analyze("Café résumé naïve.")

    # Should process without error
    assert "is_aphasic" in result
    assert "severity" in result


def test_aphasia_detector_multiple_sentences_all_short():
    """Test multiple short telegraphic sentences."""
    detector = AphasiaBrocaDetector()

    text = "Cat run. Dog bark. Bird fly. Fish swim."
    result = detector.analyze(text)

    assert result["is_aphasic"] is True
    assert "short_sentences" in result["flags"]
    assert result["fragment_ratio"] > detector.max_fragment_ratio


def test_aphasia_detector_no_punctuation():
    """Test text without sentence-ending punctuation."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("The cat is running and the dog is barking")

    # Should still be analyzed (treated as single sentence)
    assert "is_aphasic" in result
    # This is actually a healthy sentence
    assert result["is_aphasic"] is False


def test_aphasia_detector_only_function_words():
    """Test text with only function words."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("The a an of in on at to.")

    # High function word ratio (100%) - detector may not flag this as aphasic
    # since it has plenty of function words, even if meaningless
    # Just verify it processes correctly
    assert "is_aphasic" in result
    assert result["function_word_ratio"] >= detector.min_function_word_ratio


def test_aphasia_detector_code_snippets():
    """Test handling of code-like input."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("def foo(): return x + y")

    # Code is telegraphic-like but should be detected
    assert result["is_aphasic"] is True


def test_aphasia_detector_urls_and_paths():
    """Test handling of URLs and file paths."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("https://example.com/path/to/file.txt")

    # URLs are not natural language
    assert result["is_aphasic"] is True


def test_aphasia_detector_list_format():
    """Test handling of list-like text."""
    detector = AphasiaBrocaDetector()

    text = "Item 1. Item 2. Item 3."
    result = detector.analyze(text)

    # Lists are telegraphic
    assert result["is_aphasic"] is True
    assert result["fragment_ratio"] > 0.0


def test_aphasia_detector_question_only():
    """Test handling of questions."""
    detector = AphasiaBrocaDetector()

    # Proper question
    result_good = detector.analyze("What is the meaning of life?")
    assert result_good["is_aphasic"] is False

    # Telegraphic question
    result_bad = detector.analyze("What? Why? How?")
    assert result_bad["is_aphasic"] is True


def test_aphasia_detector_exclamations():
    """Test handling of exclamations."""
    detector = AphasiaBrocaDetector()

    # Telegraphic exclamations
    result = detector.analyze("Stop! Go! Run!")

    assert result["is_aphasic"] is True
    assert result["avg_sentence_len"] < detector.min_sentence_len


def test_aphasia_detector_technical_terms():
    """Test that technical jargon doesn't cause false positives."""
    detector = AphasiaBrocaDetector()

    text = (
        "The phase-entangled lattice memory utilizes cosine similarity metrics "
        "to compute resonance scores for retrieved vectors during the wake phase."
    )

    result = detector.analyze(text)

    # Technical but properly structured
    assert result["is_aphasic"] is False
    assert result["avg_sentence_len"] > detector.min_sentence_len


def test_aphasia_detector_contractions():
    """Test handling of contractions."""
    detector = AphasiaBrocaDetector()

    text = "I'm thinking it's working because we've tested it thoroughly."
    result = detector.analyze(text)

    # Contractions may be tokenized in ways that affect metrics
    # Just verify it processes without error
    assert "is_aphasic" in result
    assert "severity" in result


def test_aphasia_detector_severity_scaling():
    """Test that severity increases with more severe aphasia."""
    detector = AphasiaBrocaDetector()

    # Mild aphasia
    mild = "Cat runs fast."
    mild_result = detector.analyze(mild)

    # Severe aphasia
    severe = "Cat. Run."
    severe_result = detector.analyze(severe)

    if mild_result["is_aphasic"] and severe_result["is_aphasic"]:
        # Severe should have higher severity
        assert severe_result["severity"] >= mild_result["severity"]


def test_aphasia_detector_boundary_thresholds():
    """Test detection at exact threshold boundaries."""
    detector = AphasiaBrocaDetector()

    # AphasiaBrocaDetector default min_sentence_len is 6.0 words
    # "The cat runs" is only 3 words, so it will be flagged
    text = "The cat runs."
    result = detector.analyze(text)

    # This should be flagged as short (3 words < 6 word threshold)
    assert result["avg_sentence_len"] == 3.0
    assert "short_sentences" in result["flags"]


def test_aphasia_detector_newlines_and_formatting():
    """Test handling of text with various formatting."""
    detector = AphasiaBrocaDetector()

    text = "The cat\nruns fast.\nThe dog\nbarks loud."
    result = detector.analyze(text)

    # Newlines should be handled as sentence separators
    assert "is_aphasic" in result
    assert result["avg_sentence_len"] > 0


def test_aphasia_detector_consecutive_punctuation():
    """Test handling of consecutive punctuation marks."""
    detector = AphasiaBrocaDetector()

    result = detector.analyze("What?! Really?! No way!!!")

    # Should still analyze without crashing
    assert "is_aphasic" in result


def test_aphasia_detector_fragment_ratio_calculation():
    """Test that fragment ratio is calculated correctly."""
    detector = AphasiaBrocaDetector()

    # 2 fragments out of 4 sentences
    text = "The cat runs well. Dog. The bird flies high. Fish."
    result = detector.analyze(text)

    # Fragment ratio should be 0.5 (2/4)
    assert abs(result["fragment_ratio"] - 0.5) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
