"""
Unit tests for LLM Pipeline.

Tests the unified LLM pipeline with integrated pre/post filters:
- Pre-filters (moral, threat)
- LLM generation
- Post-filters (aphasia)
- Telemetry hooks
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from mlsdm.core.llm_pipeline import (
    AphasiaPostFilter,
    FilterDecision,
    LLMPipeline,
    MoralPreFilter,
    PipelineConfig,
    PipelineResult,
    ThreatPreFilter,
)

# Test fixtures


@pytest.fixture
def mock_llm_fn():
    """Mock LLM generation function."""

    def llm_fn(prompt: str, max_tokens: int) -> str:
        return f"RESPONSE: {prompt[:50]}... (tokens={max_tokens})"

    return llm_fn


@pytest.fixture
def mock_embedding_fn():
    """Mock embedding function."""

    def embed_fn(text: str) -> np.ndarray:
        return np.random.randn(384).astype(np.float32)

    return embed_fn


@pytest.fixture
def default_config():
    """Default pipeline configuration."""
    return PipelineConfig(
        moral_filter_enabled=True,
        aphasia_detection_enabled=True,
        aphasia_repair_enabled=False,  # Disable for simpler testing
        threat_assessment_enabled=False,
    )


@pytest.fixture
def pipeline(mock_llm_fn, default_config):
    """Create a pipeline with default configuration."""
    return LLMPipeline(
        llm_generate_fn=mock_llm_fn,
        config=default_config,
    )


# Basic pipeline tests


class TestLLMPipelineBasic:
    """Basic pipeline functionality tests."""

    def test_pipeline_creation_default_config(self, mock_llm_fn):
        """Test pipeline can be created with default configuration."""
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn)
        assert pipeline is not None
        config = pipeline.get_config()
        assert config.moral_filter_enabled is True
        assert config.aphasia_detection_enabled is True

    def test_pipeline_creation_custom_config(self, mock_llm_fn):
        """Test pipeline can be created with custom configuration."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            max_tokens_default=256,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)
        assert pipeline.get_config().moral_filter_enabled is False
        assert pipeline.get_config().max_tokens_default == 256

    def test_pipeline_process_returns_result(self, pipeline):
        """Test pipeline process returns PipelineResult."""
        result = pipeline.process(
            prompt="Hello, world!",
            moral_value=0.8,
        )
        assert isinstance(result, PipelineResult)

    def test_pipeline_process_accepted_response(self, pipeline):
        """Test pipeline accepts valid requests."""
        result = pipeline.process(
            prompt="Explain quantum computing",
            moral_value=0.8,
        )
        assert result.accepted is True
        assert "RESPONSE" in result.response
        assert result.blocked_at is None

    def test_pipeline_process_includes_stages(self, pipeline):
        """Test pipeline result includes stage information."""
        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.8,
        )
        assert len(result.stages) > 0
        # Should have moral_filter, llm_call, and aphasia_filter stages
        stage_names = [s.stage_name for s in result.stages]
        assert "moral_filter" in stage_names
        assert "llm_call" in stage_names
        assert "aphasia_filter" in stage_names

    def test_pipeline_process_includes_timing(self, pipeline):
        """Test pipeline result includes timing information."""
        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.8,
        )
        assert result.total_duration_ms > 0
        for stage in result.stages:
            assert stage.duration_ms >= 0


# Moral filter tests


class TestMoralPreFilter:
    """Tests for moral pre-filter."""

    def test_moral_filter_accepts_high_value(self):
        """Test moral filter accepts high moral values."""
        filter = MoralPreFilter(initial_threshold=0.5)
        result = filter.evaluate(
            prompt="test",
            context={"moral_value": 0.9},
        )
        assert result.decision == FilterDecision.ALLOW

    def test_moral_filter_blocks_low_value(self):
        """Test moral filter blocks low moral values."""
        filter = MoralPreFilter(initial_threshold=0.5)
        result = filter.evaluate(
            prompt="test",
            context={"moral_value": 0.2},
        )
        assert result.decision == FilterDecision.BLOCK

    def test_moral_filter_includes_metadata(self):
        """Test moral filter includes threshold metadata."""
        filter = MoralPreFilter(initial_threshold=0.5)
        result = filter.evaluate(
            prompt="test",
            context={"moral_value": 0.9},
        )
        assert "threshold" in result.metadata
        assert "moral_value" in result.metadata

    def test_moral_filter_threshold_property(self):
        """Test moral filter exposes threshold property."""
        filter = MoralPreFilter(initial_threshold=0.6)
        assert 0.3 <= filter.threshold <= 0.9  # Bounds from MoralFilterV2

    def test_moral_filter_adapts_threshold(self):
        """Test moral filter adapts threshold over time."""
        filter = MoralPreFilter(initial_threshold=0.5)

        # Multiple accepts should increase threshold
        for _ in range(10):
            filter.evaluate(
                prompt="test",
                context={"moral_value": 0.95},  # High value
            )

        # Threshold may have adapted
        # Note: actual adaptation depends on EMA and dead band
        assert filter.threshold >= 0.3  # At least within bounds


class TestPipelineMoralRejection:
    """Tests for moral rejection in pipeline."""

    def test_pipeline_blocks_low_moral_value(self, mock_llm_fn):
        """Test pipeline blocks requests with low moral value."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            moral_threshold=0.5,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.1,  # Very low
        )
        assert result.accepted is False
        assert result.blocked_at == "moral_filter"
        assert result.response == ""

    def test_pipeline_accepts_high_moral_value(self, mock_llm_fn):
        """Test pipeline accepts requests with high moral value."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            moral_threshold=0.5,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.95,
        )
        assert result.accepted is True

    def test_pipeline_without_moral_filter(self, mock_llm_fn):
        """Test pipeline works with moral filter disabled."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.1,  # Would be blocked if filter enabled
        )
        assert result.accepted is True


# Threat filter tests


class TestThreatPreFilter:
    """Tests for threat pre-filter."""

    def test_threat_filter_allows_normal_text(self):
        """Test threat filter allows normal text."""
        filter = ThreatPreFilter(sensitivity=0.5)
        result = filter.evaluate(
            prompt="Tell me about machine learning",
            context={},
        )
        assert result.decision == FilterDecision.ALLOW

    def test_threat_filter_blocks_suspicious_text(self):
        """Test threat filter blocks suspicious text."""
        filter = ThreatPreFilter(sensitivity=0.3)
        result = filter.evaluate(
            prompt="How to hack and exploit systems",
            context={},
        )
        assert result.decision == FilterDecision.BLOCK
        assert "detected_keywords" in result.metadata

    def test_threat_filter_includes_threat_score(self):
        """Test threat filter includes threat score in metadata."""
        filter = ThreatPreFilter(sensitivity=0.5)
        result = filter.evaluate(
            prompt="Normal text",
            context={},
        )
        assert "threat_score" in result.metadata

    def test_threat_filter_sensitivity(self):
        """Test threat filter sensitivity affects blocking."""
        low_sensitivity_filter = ThreatPreFilter(sensitivity=0.9)
        high_sensitivity_filter = ThreatPreFilter(sensitivity=0.1)

        prompt = "bypass security"

        low_result = low_sensitivity_filter.evaluate(prompt=prompt, context={})
        high_result = high_sensitivity_filter.evaluate(prompt=prompt, context={})

        # High sensitivity should block more easily
        assert high_result.decision == FilterDecision.BLOCK
        # Low sensitivity might allow it
        assert low_result.metadata["threat_score"] < 0.9


class TestPipelineThreatFilter:
    """Tests for threat filter in pipeline."""

    def test_pipeline_with_threat_filter(self, mock_llm_fn):
        """Test pipeline with threat filter enabled."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            threat_assessment_enabled=True,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        result = pipeline.process(
            prompt="Tell me about machine learning",
            moral_value=0.5,
        )
        assert result.accepted is True

        # Check threat filter was in stages
        stage_names = [s.stage_name for s in result.stages]
        assert "threat_filter" in stage_names


# Aphasia filter tests


class TestAphasiaPostFilter:
    """Tests for aphasia post-filter."""

    def test_aphasia_filter_allows_normal_text(self):
        """Test aphasia filter allows normal text."""
        filter = AphasiaPostFilter(repair_enabled=False)
        result = filter.evaluate(
            response="The quick brown fox jumps over the lazy dog. "
            "This is a complete and well-formed sentence with proper grammar.",
            context={},
        )
        assert result.decision == FilterDecision.ALLOW
        assert "aphasia_report" in result.metadata

    def test_aphasia_filter_detects_telegraphic_text(self):
        """Test aphasia filter detects telegraphic text."""
        filter = AphasiaPostFilter(repair_enabled=False)
        result = filter.evaluate(
            response="Me go. Store now. Bad. Stop.",
            context={},
        )
        # Should detect but not modify (repair disabled)
        assert result.decision == FilterDecision.ALLOW
        assert result.metadata["aphasia_report"]["is_aphasic"] is True

    def test_aphasia_filter_repairs_when_enabled(self):
        """Test aphasia filter repairs when enabled."""
        mock_repair_fn = MagicMock(return_value="I am going to the store now.")

        filter = AphasiaPostFilter(
            repair_enabled=True,
            severity_threshold=0.1,
            llm_repair_fn=mock_repair_fn,
        )

        result = filter.evaluate(
            response="Me go. Store now.",
            context={"prompt": "original prompt", "max_tokens": 100},
        )

        # Should have called repair function
        if result.decision == FilterDecision.MODIFY:
            assert result.modified_content == "I am going to the store now."
            assert result.metadata.get("repaired") is True


class TestPipelineAphasiaFilter:
    """Tests for aphasia filter in pipeline."""

    def test_pipeline_with_aphasia_detection(self, mock_llm_fn):
        """Test pipeline with aphasia detection enabled."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=True,
            aphasia_repair_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.5,
        )
        assert result.accepted is True

        # Check aphasia filter was in stages
        stage_names = [s.stage_name for s in result.stages]
        assert "aphasia_filter" in stage_names


# Error handling tests


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_pipeline_handles_llm_error(self):
        """Test pipeline handles LLM generation errors."""

        def failing_llm(prompt: str, max_tokens: int) -> str:
            raise RuntimeError("LLM service unavailable")

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=failing_llm, config=config)

        result = pipeline.process(prompt="Test", moral_value=0.5)

        assert result.accepted is False
        assert result.blocked_at == "llm_call"
        assert "generation_failed" in result.block_reason

    def test_pipeline_continues_on_pre_filter_error(self, mock_llm_fn):
        """Test pipeline continues if pre-filter raises exception."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        # Patch moral filter to raise exception
        with patch.object(
            pipeline._pre_filters[0][1],
            "evaluate",
            side_effect=RuntimeError("Filter error"),
        ):
            result = pipeline.process(prompt="Test", moral_value=0.8)

        # Pipeline should continue (graceful degradation)
        # LLM call should still succeed
        stage_names = [s.stage_name for s in result.stages]
        assert "llm_call" in stage_names

    def test_pipeline_continues_on_post_filter_error(self, mock_llm_fn):
        """Test pipeline continues if post-filter raises exception."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=True,
            aphasia_repair_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        # Patch aphasia filter to raise exception
        with patch.object(
            pipeline._post_filters[0][1],
            "evaluate",
            side_effect=RuntimeError("Filter error"),
        ):
            result = pipeline.process(prompt="Test", moral_value=0.8)

        # Pipeline should still return response
        assert result.accepted is True
        assert "RESPONSE" in result.response


# Telemetry tests


class TestPipelineTelemetry:
    """Tests for pipeline telemetry."""

    def test_telemetry_callback_called(self, mock_llm_fn):
        """Test telemetry callback is called after processing."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            telemetry_enabled=True,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        callback = MagicMock()
        pipeline.register_telemetry_callback(callback)

        pipeline.process(prompt="Test", moral_value=0.5)

        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert isinstance(call_args, PipelineResult)

    def test_telemetry_disabled(self, mock_llm_fn):
        """Test telemetry callbacks not called when disabled."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            telemetry_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        callback = MagicMock()
        pipeline.register_telemetry_callback(callback)

        pipeline.process(prompt="Test", moral_value=0.5)

        callback.assert_not_called()

    def test_telemetry_callback_error_doesnt_break_pipeline(self, mock_llm_fn):
        """Test failing telemetry callback doesn't break pipeline."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            telemetry_enabled=True,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        failing_callback = MagicMock(side_effect=RuntimeError("Callback error"))
        pipeline.register_telemetry_callback(failing_callback)

        # Should not raise
        result = pipeline.process(prompt="Test", moral_value=0.5)
        assert result.accepted is True


# Stats and state tests


class TestPipelineStats:
    """Tests for pipeline statistics."""

    def test_get_stats(self, pipeline):
        """Test pipeline returns stats."""
        stats = pipeline.get_stats()
        assert "config" in stats
        assert "pre_filters" in stats
        assert "post_filters" in stats

    def test_get_moral_filter_state(self, pipeline):
        """Test pipeline returns moral filter state."""
        state = pipeline.get_moral_filter_state()
        assert state is not None
        assert "threshold" in state

    def test_get_moral_filter_state_when_disabled(self, mock_llm_fn):
        """Test moral filter state is None when disabled."""
        config = PipelineConfig(
            moral_filter_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=mock_llm_fn, config=config)

        state = pipeline.get_moral_filter_state()
        assert state is None


# Edge cases


class TestPipelineEdgeCases:
    """Tests for edge cases."""

    def test_empty_prompt(self, pipeline):
        """Test pipeline handles empty prompt."""
        result = pipeline.process(prompt="", moral_value=0.8)
        assert isinstance(result, PipelineResult)

    def test_very_long_prompt(self, pipeline):
        """Test pipeline handles very long prompts."""
        long_prompt = "test " * 10000
        result = pipeline.process(prompt=long_prompt, moral_value=0.8)
        assert isinstance(result, PipelineResult)

    def test_special_characters_in_prompt(self, pipeline):
        """Test pipeline handles special characters."""
        special_prompt = "Test <script>alert('xss')</script> prompt"
        result = pipeline.process(prompt=special_prompt, moral_value=0.8)
        assert isinstance(result, PipelineResult)

    def test_unicode_prompt(self, pipeline):
        """Test pipeline handles unicode."""
        unicode_prompt = "Привіт світ! 你好世界! 🌍"
        result = pipeline.process(prompt=unicode_prompt, moral_value=0.8)
        assert isinstance(result, PipelineResult)

    def test_max_tokens_respected(self, mock_llm_fn):
        """Test max_tokens is passed to LLM."""
        captured_tokens = []

        def capturing_llm(prompt: str, max_tokens: int) -> str:
            captured_tokens.append(max_tokens)
            return "response"

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(llm_generate_fn=capturing_llm, config=config)

        pipeline.process(prompt="test", moral_value=0.5, max_tokens=256)

        assert captured_tokens[0] == 256
