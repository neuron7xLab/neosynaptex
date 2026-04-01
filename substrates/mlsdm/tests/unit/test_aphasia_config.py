"""
Unit tests for Aphasia-Broca configuration in NeuroLangWrapper.

Tests the configurable detection/repair gates and severity threshold.
Ensures backward compatibility and default behavior.
"""

import numpy as np
import pytest

from mlsdm.extensions import NeuroLangWrapper


def mock_llm_generate(prompt: str, max_tokens: int) -> str:
    """Mock LLM that returns telegraphic responses."""
    if "Rewrite it" in prompt or "aphasia" in prompt.lower():
        # This is a repair request - return corrected text
        return "The system is functioning correctly and all operations are proceeding as expected."
    # Return telegraphic response by default
    return "System work. Good. All fine."


def mock_llm_healthy(prompt: str, max_tokens: int) -> str:
    """Mock LLM that returns healthy responses."""
    return "The system is functioning correctly and all operations are proceeding as expected."


def mock_embedding(text: str) -> np.ndarray:
    """Mock embedding function."""
    return np.random.randn(384).astype(np.float32)


class TestAphasiaDetectionDisable:
    """Test suite for disabling aphasia detection."""

    def test_aphasia_detection_can_be_disabled(self):
        """Test that aphasia detection can be completely disabled."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            wake_duration=8,
            sleep_duration=3,
            aphasia_detect_enabled=False,
            aphasia_repair_enabled=True,  # Should have no effect if detection is off
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Detection disabled: should return raw LLM output
        assert result["accepted"] is True
        assert result["aphasia_flags"] is None
        # Should contain the telegraphic response, not the repaired one
        assert "work" in result["response"].lower() or "fine" in result["response"].lower()

    def test_default_detection_enabled(self):
        """Test that detection is enabled by default."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            neurolang_mode="disabled",
        )

        # Default should have detection enabled
        assert wrapper.aphasia_detect_enabled is True
        assert wrapper.aphasia_repair_enabled is True
        assert wrapper.aphasia_severity_threshold == 0.3


class TestAphasiaRepairDisable:
    """Test suite for disabling aphasia repair while keeping detection active."""

    def test_aphasia_repair_can_be_disabled(self):
        """Test that repair can be disabled independently of detection."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=False,
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Detection enabled, repair disabled
        assert result["accepted"] is True
        assert result["aphasia_flags"] is not None
        assert result["aphasia_flags"]["is_aphasic"] is True

        # Should NOT be repaired - should contain original telegraphic text
        assert "work" in result["response"].lower() or "fine" in result["response"].lower()
        # Should NOT contain the repair phrase
        assert "functioning correctly" not in result["response"].lower()

    def test_repair_enabled_with_detection(self):
        """Test that repair works when both detection and repair are enabled."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=True,
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Both enabled: should detect and repair
        assert result["accepted"] is True
        assert result["aphasia_flags"] is not None
        assert result["aphasia_flags"]["is_aphasic"] is True

        # Should be repaired
        assert "functioning correctly" in result["response"].lower()


class TestAphasiaSeverityThreshold:
    """Test suite for severity threshold configuration."""

    def test_low_threshold_triggers_repair(self):
        """Test that a very low threshold triggers repair for any detected aphasia."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=True,
            aphasia_severity_threshold=0.01,  # Very low threshold
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # With low threshold, any aphasic text should be repaired
        assert result["aphasia_flags"]["is_aphasic"] is True
        assert "functioning correctly" in result["response"].lower()

    def test_high_threshold_prevents_repair(self):
        """Test that a very high threshold prevents repair even for aphasic text."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=True,
            aphasia_severity_threshold=0.99,  # Very high threshold
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # With high threshold, repair should not trigger
        assert result["aphasia_flags"]["is_aphasic"] is True
        # Should NOT be repaired if severity < 0.99
        if result["aphasia_flags"]["severity"] < 0.99:
            assert "work" in result["response"].lower() or "fine" in result["response"].lower()

    def test_threshold_respected_at_boundary(self):
        """Test that threshold is respected at the boundary."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=True,
            aphasia_severity_threshold=0.5,  # Mid-range threshold
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Check that severity threshold logic is working
        assert result["aphasia_flags"] is not None
        if result["aphasia_flags"]["is_aphasic"]:
            severity = result["aphasia_flags"]["severity"]
            if severity >= 0.5:
                # Should be repaired
                assert "functioning correctly" in result["response"].lower()
            else:
                # Should NOT be repaired
                assert "work" in result["response"].lower() or "fine" in result["response"].lower()


class TestBackwardCompatibility:
    """Test suite for backward compatibility."""

    def test_default_behavior_unchanged(self):
        """Test that default behavior matches the original implementation."""
        # Create wrapper with no explicit aphasia config (all defaults)
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            neurolang_mode="disabled",
        )

        # Defaults should be: detection=True, repair=True, threshold=0.3
        assert wrapper.aphasia_detect_enabled is True
        assert wrapper.aphasia_repair_enabled is True
        assert wrapper.aphasia_severity_threshold == 0.3

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # With defaults, should detect and repair
        assert result["aphasia_flags"] is not None
        assert result["aphasia_flags"]["is_aphasic"] is True
        # Should be repaired with default threshold
        assert "functioning correctly" in result["response"].lower()

    def test_healthy_response_not_affected(self):
        """Test that healthy responses work correctly with all configurations."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_healthy,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=True,
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Healthy text should not be marked as aphasic
        assert result["aphasia_flags"] is not None
        assert result["aphasia_flags"]["is_aphasic"] is False
        assert "functioning correctly" in result["response"].lower()


class TestConfigurationValidation:
    """Test suite for configuration parameter validation."""

    def test_boolean_config_parameters(self):
        """Test that boolean parameters are properly converted."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=1,  # Non-boolean but truthy
            aphasia_repair_enabled=0,  # Non-boolean but falsy
            neurolang_mode="disabled",
        )

        assert wrapper.aphasia_detect_enabled is True
        assert wrapper.aphasia_repair_enabled is False

    def test_threshold_float_conversion(self):
        """Test that threshold is converted to float."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_severity_threshold=1,  # Integer
            neurolang_mode="disabled",
        )

        assert isinstance(wrapper.aphasia_severity_threshold, float)
        assert wrapper.aphasia_severity_threshold == 1.0


class TestMonitoringMode:
    """Test suite for monitoring-only mode (detect but don't repair)."""

    def test_monitoring_mode_configuration(self):
        """Test configuration for monitoring-only mode."""
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm_generate,
            embedding_fn=mock_embedding,
            dim=384,
            capacity=100,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=False,  # Monitoring only
            neurolang_mode="disabled",
        )

        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        # Should have aphasia flags for monitoring
        assert result["aphasia_flags"] is not None
        assert result["aphasia_flags"]["is_aphasic"] is True
        assert "flags" in result["aphasia_flags"]
        assert "severity" in result["aphasia_flags"]

        # But text should not be modified
        assert "work" in result["response"].lower() or "fine" in result["response"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
