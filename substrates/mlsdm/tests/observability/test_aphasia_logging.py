"""
Tests for Aphasia Observability and Logging

This test suite validates that aphasia detection and repair decisions are properly
logged for observability and audit purposes.
"""

import logging

import numpy as np
import pytest

from mlsdm.extensions import NeuroLangWrapper
from mlsdm.observability.aphasia_logging import LOGGER_NAME


def telegraphic_llm(prompt: str, max_tokens: int) -> str:
    """Simulates an LLM producing aphasic (telegraphic) output."""
    return "This short. No connect. Bad."


def normal_llm(prompt: str, max_tokens: int) -> str:
    """Simulates an LLM producing normal, coherent output."""
    return (
        "This is a coherent answer that uses normal grammar and function words "
        "to describe the system behaviour in a clear way."
    )


def dummy_embedder(text: str):
    """Generate deterministic embeddings for testing."""
    vec = np.ones(384, dtype=np.float32)
    return vec / np.linalg.norm(vec)


@pytest.mark.parametrize(
    "llm_fn, expected_decision_contains",
    [
        (telegraphic_llm, "repaired"),
        (normal_llm, "skip"),
    ],
)
def test_aphasia_logging_decision_emitted(caplog, llm_fn, expected_decision_contains):
    """Test that aphasia logging emits the correct decision for different LLM outputs."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=llm_fn,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test aphasia logging.", moral_value=0.8, max_tokens=64)

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "Expected at least one aphasia log record"

    joined_messages = " ".join(r.getMessage() for r in records)
    assert "[APHASIA]" in joined_messages
    assert f"decision={expected_decision_contains}" in joined_messages


def test_aphasia_logging_includes_config_flags(caplog):
    """Test that aphasia logs include configuration flags (detect/repair enabled, severity threshold)."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=normal_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=False,
        aphasia_severity_threshold=0.7,
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test config logging.", moral_value=0.8, max_tokens=64)

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "Expected at least one aphasia log record"

    joined_messages = " ".join(r.getMessage() for r in records)
    assert "detect_enabled=True" in joined_messages
    assert "repair_enabled=False" in joined_messages
    assert "severity_threshold=0.700" in joined_messages


def test_aphasia_logging_includes_severity_and_flags(caplog):
    """Test that aphasia logs include severity scores and detected flags."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test severity and flags.", moral_value=0.8, max_tokens=64)

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "Expected at least one aphasia log record"

    joined_messages = " ".join(r.getMessage() for r in records)
    assert "severity=" in joined_messages
    assert "is_aphasic=True" in joined_messages
    assert "flags=" in joined_messages


def test_no_logging_when_detection_disabled(caplog):
    """Test that no aphasia logging occurs when detection is disabled."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=False,
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test disabled detection.", moral_value=0.8, max_tokens=64)

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert len(records) == 0, "Expected no aphasia log records when detection is disabled"


def test_detected_no_repair_decision(caplog):
    """Test that detected_no_repair decision is logged when repair is disabled but aphasia detected."""
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    wrapper = NeuroLangWrapper(
        llm_generate_fn=telegraphic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=256,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=False,  # Repair disabled
        neurolang_mode="disabled",
    )

    _ = wrapper.generate(prompt="Test detected no repair.", moral_value=0.8, max_tokens=64)

    records = [r for r in caplog.records if r.name == LOGGER_NAME]
    assert records, "Expected at least one aphasia log record"

    joined_messages = " ".join(r.getMessage() for r in records)
    assert "decision=detected_no_repair" in joined_messages
    assert "is_aphasic=True" in joined_messages
