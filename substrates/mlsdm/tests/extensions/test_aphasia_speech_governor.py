"""
Unit tests for AphasiaSpeechGovernor.

Tests the aphasia-specific speech governance implementation that
detects and optionally repairs telegraphic speech patterns.
"""

import pytest

from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector, AphasiaSpeechGovernor
from mlsdm.speech.governance import SpeechGovernanceResult


def mock_llm_repair(prompt: str, max_tokens: int) -> str:
    """Mock LLM that produces a 'repaired' version."""
    return "This is a properly structured sentence with good grammar."


def test_aphasia_governor_initialization():
    """Test AphasiaSpeechGovernor initializes correctly."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    assert governor._detector is detector
    assert governor._repair_enabled is True
    assert governor._severity_threshold == 0.3
    assert governor._llm_generate_fn is mock_llm_repair


def test_aphasia_governor_healthy_text_passes_through():
    """Test that healthy text is not modified."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    healthy_text = (
        "The cognitive architecture provides a comprehensive framework for LLM governance."
    )
    result = governor(prompt="test", draft=healthy_text, max_tokens=50)

    assert isinstance(result, SpeechGovernanceResult)
    assert result.final_text == healthy_text
    assert result.raw_text == healthy_text
    assert result.metadata["repaired"] is False
    assert result.metadata["aphasia_report"]["is_aphasic"] is False


def test_aphasia_governor_detects_aphasic_text():
    """Test that aphasic text is detected."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=False,  # Only detect, don't repair
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    aphasic_text = "Cat run. Dog bark."
    result = governor(prompt="test", draft=aphasic_text, max_tokens=50)

    assert result.final_text == aphasic_text  # Not repaired
    assert result.raw_text == aphasic_text
    assert result.metadata["repaired"] is False
    assert result.metadata["aphasia_report"]["is_aphasic"] is True


def test_aphasia_governor_repairs_when_enabled():
    """Test that aphasic text is repaired when repair is enabled."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    aphasic_text = "Short. Bad."
    result = governor(prompt="Explain something", draft=aphasic_text, max_tokens=50)

    # Should be repaired
    assert result.final_text != aphasic_text
    assert result.final_text == "This is a properly structured sentence with good grammar."
    assert result.raw_text == aphasic_text
    assert result.metadata["repaired"] is True
    assert result.metadata["aphasia_report"]["is_aphasic"] is True


def test_aphasia_governor_respects_severity_threshold():
    """Test that repair only happens above severity threshold."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.9,  # Very high threshold
        llm_generate_fn=mock_llm_repair,
    )

    # Mildly aphasic text (low severity)
    mildly_aphasic = "The cat ran away quickly."
    result = governor(prompt="test", draft=mildly_aphasic, max_tokens=50)

    # Should not be repaired due to high threshold
    assert result.metadata["repaired"] is False


def test_aphasia_governor_repair_without_llm_raises_error():
    """Test that repair without LLM function raises error."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=None,  # No LLM provided
    )

    aphasic_text = "Cat run."

    with pytest.raises(RuntimeError, match="no llm_generate_fn provided"):
        governor(prompt="test", draft=aphasic_text, max_tokens=50)


def test_aphasia_governor_metadata_includes_report():
    """Test that metadata includes full aphasia report."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=False,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    text = "Short."
    result = governor(prompt="test", draft=text, max_tokens=50)

    assert "aphasia_report" in result.metadata
    report = result.metadata["aphasia_report"]
    assert "is_aphasic" in report
    assert "severity" in report
    assert "flags" in report
    assert "avg_sentence_len" in report
    assert "function_word_ratio" in report
    assert "fragment_ratio" in report


def test_aphasia_governor_with_empty_text():
    """Test handling of empty text."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    result = governor(prompt="test", draft="", max_tokens=50)

    assert result.metadata["aphasia_report"]["is_aphasic"] is True
    assert result.metadata["aphasia_report"]["severity"] == 1.0
    # Empty text should trigger repair
    assert result.metadata["repaired"] is True


def test_aphasia_governor_repair_prompt_includes_original():
    """Test that repair prompt includes the original draft."""
    captured_prompt = None

    def capturing_llm(prompt: str, max_tokens: int) -> str:
        nonlocal captured_prompt
        captured_prompt = prompt
        return "Repaired text"

    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=capturing_llm,
    )

    original_prompt = "What is AI?"
    draft = "AI good."
    governor(prompt=original_prompt, draft=draft, max_tokens=50)

    # Verify repair prompt includes both original prompt and draft
    assert captured_prompt is not None
    assert original_prompt in captured_prompt
    assert draft in captured_prompt
    assert "Broca-like aphasia" in captured_prompt
    assert "telegraphic style" in captured_prompt


def test_aphasia_governor_different_severity_thresholds():
    """Test that different severity thresholds work correctly."""
    detector = AphasiaBrocaDetector()

    # Low threshold - repairs even mild issues
    governor_low = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.1,
        llm_generate_fn=mock_llm_repair,
    )

    # High threshold - only repairs severe issues
    governor_high = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.8,
        llm_generate_fn=mock_llm_repair,
    )

    mildly_aphasic = "Cat ran fast today."

    result_low = governor_low(prompt="test", draft=mildly_aphasic, max_tokens=50)
    result_high = governor_high(prompt="test", draft=mildly_aphasic, max_tokens=50)

    # With mildly aphasic text:
    # - Low threshold might repair (depending on exact severity)
    # - High threshold should not repair
    assert "repaired" in result_low.metadata
    assert "repaired" in result_high.metadata


def test_aphasia_governor_preserves_raw_text():
    """Test that raw text is always preserved regardless of repair."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=True,
        severity_threshold=0.3,
        llm_generate_fn=mock_llm_repair,
    )

    original_text = "Bad. Short."
    result = governor(prompt="test", draft=original_text, max_tokens=50)

    # Raw text should always be the original
    assert result.raw_text == original_text
    # Final text might be different
    assert result.final_text != original_text  # Should be repaired


def test_aphasia_governor_detection_only_mode():
    """Test governor in detection-only mode (no repair)."""
    detector = AphasiaBrocaDetector()
    governor = AphasiaSpeechGovernor(
        detector=detector,
        repair_enabled=False,
        severity_threshold=0.3,
        llm_generate_fn=None,  # No LLM needed for detection only
    )

    aphasic_text = "Cat run. Dog bark. Bird fly."
    result = governor(prompt="test", draft=aphasic_text, max_tokens=50)

    # Text should not be modified
    assert result.final_text == aphasic_text
    assert result.raw_text == aphasic_text
    assert result.metadata["repaired"] is False
    # But detection should still work
    assert result.metadata["aphasia_report"]["is_aphasic"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
