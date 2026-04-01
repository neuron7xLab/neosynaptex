"""
Security tests for MLSDM secure mode functionality.

This test suite validates that when MLSDM_SECURE_MODE is enabled:
- NeuroLang training and checkpoint loading are disabled
- Aphasia repair is disabled (detection only)
- The system operates in a security-hardened mode
- Logs and telemetry are scrubbed of sensitive data
"""

import os
from unittest.mock import patch

import numpy as np
import pytest

from mlsdm.extensions.neuro_lang_extension import (
    TORCH_AVAILABLE,
    NeuroLangWrapper,
    is_secure_mode_enabled,
)
from mlsdm.security.payload_scrubber import (
    is_secure_mode,
    scrub_log_record,
    scrub_request_payload,
)


def dummy_llm(prompt: str, max_tokens: int) -> str:
    """Dummy LLM for testing."""
    return "This is a test response with proper grammar and function words."


def dummy_embedder(text: str):
    """Generate deterministic embeddings for testing."""
    vec = np.ones(384, dtype=np.float32)
    return vec / np.linalg.norm(vec)


@pytest.mark.security
def test_is_secure_mode_enabled_returns_true_when_env_is_1():
    """Test that secure mode is detected when MLSDM_SECURE_MODE=1."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        assert is_secure_mode_enabled() is True


@pytest.mark.security
def test_is_secure_mode_enabled_returns_true_when_env_is_true():
    """Test that secure mode is detected when MLSDM_SECURE_MODE=true."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "true"}):
        assert is_secure_mode_enabled() is True


@pytest.mark.security
def test_is_secure_mode_enabled_returns_true_when_env_is_TRUE():
    """Test that secure mode is detected when MLSDM_SECURE_MODE=TRUE."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "TRUE"}):
        assert is_secure_mode_enabled() is True


@pytest.mark.security
def test_is_secure_mode_enabled_returns_false_by_default():
    """Test that secure mode is disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_secure_mode_enabled() is False


@pytest.mark.security
def test_is_secure_mode_enabled_returns_false_when_env_is_0():
    """Test that secure mode is disabled when MLSDM_SECURE_MODE=0."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "0"}):
        assert is_secure_mode_enabled() is False


@pytest.mark.security
def test_secure_mode_forces_neurolang_disabled():
    """Test that secure mode forces neurolang_mode to 'disabled'."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            neurolang_mode="eager_train",  # Try to enable training
        )

        # Verify that secure mode overrode the setting
        assert wrapper.neurolang_mode == "disabled"
        assert wrapper.actor is None
        assert wrapper.critic is None
        assert wrapper.trainer is None


@pytest.mark.security
def test_secure_mode_ignores_checkpoint_path():
    """Test that secure mode ignores checkpoint_path even if provided."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            neurolang_mode="eager_train",
            neurolang_checkpoint_path="config/neurolang_grammar.pt",
        )

        # Verify neurolang is disabled
        assert wrapper.neurolang_mode == "disabled"
        assert wrapper.actor is None
        assert wrapper.critic is None


@pytest.mark.security
def test_secure_mode_disables_aphasia_repair():
    """Test that secure mode disables aphasia repair (detection only)."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            aphasia_repair_enabled=True,  # Try to enable repair
        )

        # Verify that secure mode disabled repair
        assert wrapper.aphasia_repair_enabled is False
        # Detection should still work
        assert wrapper.aphasia_detect_enabled is True


@pytest.mark.security
def test_secure_mode_generate_works_without_training():
    """Test that generate() works in secure mode without attempting to train."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            neurolang_mode="eager_train",
        )

        # Should not raise any errors
        result = wrapper.generate(
            prompt="Test secure mode generation", moral_value=0.7, max_tokens=50
        )

        assert result is not None
        assert "response" in result
        assert result["accepted"] is True
        # Neuro enhancement should indicate disabled state
        assert "disabled" in result["neuro_enhancement"].lower()


@pytest.mark.security
def test_secure_mode_preserves_explicit_detect_disabled():
    """Test that if detection is explicitly disabled, secure mode respects it."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            aphasia_detect_enabled=False,  # Explicitly disable detection
            aphasia_repair_enabled=True,
        )

        # Detection should remain disabled
        assert wrapper.aphasia_detect_enabled is False
        # Repair should be disabled by secure mode
        assert wrapper.aphasia_repair_enabled is False


@pytest.mark.security
@pytest.mark.skipif(not TORCH_AVAILABLE, reason="NeuroLang training requires PyTorch")
def test_without_secure_mode_training_works_normally():
    """Test that without secure mode, normal training/checkpoint loading works."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "0"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            neurolang_mode="eager_train",
            aphasia_repair_enabled=True,
        )

        # Normal mode should allow training and repair
        assert wrapper.neurolang_mode == "eager_train"
        assert wrapper.aphasia_repair_enabled is True
        assert wrapper.actor is not None
        assert wrapper.critic is not None


@pytest.mark.security
def test_secure_mode_generate_returns_valid_response_structure():
    """Test that generate() in secure mode returns valid response structure."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
        )

        result = wrapper.generate(
            prompt="Test prompt for secure mode", moral_value=0.8, max_tokens=100
        )

        # Verify response structure
        assert result is not None
        assert isinstance(result, dict)
        assert "response" in result
        assert "phase" in result
        assert "accepted" in result
        assert "neuro_enhancement" in result
        assert "aphasia_flags" in result

        # Verify response is valid (not an error)
        assert result["accepted"] is True
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0


@pytest.mark.security
def test_secure_mode_scrubbing_removes_prompt_from_log_records():
    """Test that secure mode scrubbing removes prompt from log records."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        assert is_secure_mode() is True

        log_record = {
            "message": "Processing request",
            "prompt": "This is a secret prompt that should not be logged",
            "user_id": "user123",
        }

        scrubbed = scrub_log_record(log_record)

        # Prompt and user_id should be scrubbed
        assert scrubbed["prompt"] == "***REDACTED***"
        assert scrubbed["user_id"] == "***REDACTED***"
        # Message should be preserved
        assert scrubbed["message"] == "Processing request"


@pytest.mark.security
def test_secure_mode_scrubbing_removes_response_from_telemetry():
    """Test that secure mode scrubbing removes full response from telemetry."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        telemetry = {
            "event": "generation_complete",
            "full_response": "This is the complete LLM response",
            "full_prompt": "This is the complete user prompt",
            "latency_ms": 150,
        }

        scrubbed = scrub_request_payload(telemetry)

        # Full response and prompt should be scrubbed
        assert scrubbed["full_response"] == "***REDACTED***"
        assert scrubbed["full_prompt"] == "***REDACTED***"
        # Metadata should be preserved
        assert scrubbed["latency_ms"] == 150
        assert scrubbed["event"] == "generation_complete"


@pytest.mark.security
def test_secure_mode_does_not_break_normal_generation():
    """Test that secure mode doesn't break normal text generation."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
        )

        # Multiple generations should work without exceptions
        for i in range(3):
            result = wrapper.generate(prompt=f"Test prompt {i}", moral_value=0.7, max_tokens=50)
            assert result["accepted"] is True
            assert "Rejected" not in result["response"]


@pytest.mark.security
def test_secure_mode_neuro_enhancement_shows_disabled():
    """Test that neuro_enhancement field indicates disabled state in secure mode."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=256,
            neurolang_mode="eager_train",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # neuro_enhancement should indicate disabled state
        assert result["neuro_enhancement"] == "NeuroLang disabled"


@pytest.mark.security
def test_secure_mode_function_matches_extension_function():
    """Test that security module is_secure_mode matches extension is_secure_mode_enabled."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        assert is_secure_mode() is True
        assert is_secure_mode_enabled() is True

    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "0"}):
        assert is_secure_mode() is False
        assert is_secure_mode_enabled() is False

    with patch.dict(os.environ, {}, clear=True):
        assert is_secure_mode() is False
        assert is_secure_mode_enabled() is False


@pytest.mark.security
def test_secure_mode_scrubber_handles_nested_sensitive_data():
    """Test that scrubber handles nested sensitive data in secure mode."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        nested_data = {
            "request": {
                "user_id": "user123",
                "input": {"prompt": "Secret prompt", "raw_input": "Raw sensitive data"},
            },
            "network": {"ip_address": "192.168.1.1", "session_id": "sess_abc123"},
        }

        scrubbed = scrub_request_payload(nested_data)

        # All nested sensitive fields should be scrubbed
        assert scrubbed["request"]["user_id"] == "***REDACTED***"
        assert scrubbed["request"]["input"]["prompt"] == "***REDACTED***"
        assert scrubbed["request"]["input"]["raw_input"] == "***REDACTED***"
        assert scrubbed["network"]["ip_address"] == "***REDACTED***"
        assert scrubbed["network"]["session_id"] == "***REDACTED***"


@pytest.mark.security
def test_secure_mode_scrubs_metadata_at_top_level():
    """Test that metadata field itself is scrubbed (it's in forbidden fields)."""
    with patch.dict(os.environ, {"MLSDM_SECURE_MODE": "1"}):
        data = {"event": "request", "metadata": {"user_info": "sensitive"}}

        scrubbed = scrub_request_payload(data)

        # metadata field itself is in FORBIDDEN_FIELDS, so it's scrubbed entirely
        assert scrubbed["metadata"] == "***REDACTED***"
        assert scrubbed["event"] == "request"
