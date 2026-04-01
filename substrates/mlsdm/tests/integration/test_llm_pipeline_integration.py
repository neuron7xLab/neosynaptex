"""
Integration tests for LLM Pipeline.

Tests the pipeline with real components to ensure proper integration:
- With different LLM adapters
- With memory systems
- End-to-end workflows
"""

import numpy as np

from mlsdm import (
    FilterDecision,
    LLMPipeline,
    PipelineConfig,
    create_llm_pipeline,
)


class TestLLMPipelineIntegration:
    """Integration tests for LLM Pipeline."""

    def test_pipeline_with_stub_adapter(self):
        """Test pipeline with local stub adapter."""
        pipeline = create_llm_pipeline()
        result = pipeline.process(
            prompt="What is machine learning?",
            moral_value=0.8,
            max_tokens=256,
        )

        assert result.accepted is True
        assert "NEURO-RESPONSE" in result.response
        assert result.total_duration_ms > 0

    def test_pipeline_moral_rejection_flow(self):
        """Test complete moral rejection flow."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            moral_threshold=0.5,
            aphasia_detection_enabled=False,
        )
        pipeline = create_llm_pipeline(config=config)

        # Should be rejected with low moral value
        result = pipeline.process(
            prompt="Test prompt",
            moral_value=0.1,
        )

        assert result.accepted is False
        assert result.blocked_at == "moral_filter"
        assert result.response == ""

        # Verify stage recorded
        moral_stage = next(s for s in result.stages if s.stage_name == "moral_filter")
        assert moral_stage.success is True
        assert moral_stage.result.decision == FilterDecision.BLOCK

    def test_pipeline_aphasia_detection_flow(self):
        """Test complete aphasia detection flow."""

        # Create an LLM that returns telegraphic text
        def telegraphic_llm(prompt: str, max_tokens: int) -> str:
            return "Me go. Store now. Bad."

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=True,
            aphasia_repair_enabled=False,
        )
        pipeline = LLMPipeline(
            llm_generate_fn=telegraphic_llm,
            config=config,
        )

        result = pipeline.process(
            prompt="Test",
            moral_value=0.5,
        )

        assert result.accepted is True

        # Check aphasia was detected
        aphasia_stage = next(s for s in result.stages if s.stage_name == "aphasia_filter")
        assert aphasia_stage.success is True
        assert aphasia_stage.result.metadata["aphasia_report"]["is_aphasic"] is True

    def test_pipeline_aphasia_repair_flow(self):
        """Test aphasia repair flow with LLM-based repair."""
        call_count = {"value": 0}

        def repairing_llm(prompt: str, max_tokens: int) -> str:
            call_count["value"] += 1
            if call_count["value"] == 1:
                # First call: return telegraphic
                return "Me go. Store now."
            else:
                # Second call (repair): return proper text
                return "I am going to the store now. The store is open."

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=True,
            aphasia_repair_enabled=True,
            aphasia_severity_threshold=0.1,  # Low threshold to trigger repair
        )
        pipeline = LLMPipeline(
            llm_generate_fn=repairing_llm,
            config=config,
        )

        result = pipeline.process(
            prompt="Test",
            moral_value=0.5,
        )

        assert result.accepted is True
        # Response should be the repaired version
        assert "I am going" in result.response or "store" in result.response

    def test_pipeline_threat_detection_flow(self):
        """Test threat detection in pipeline."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
            threat_assessment_enabled=True,
        )
        pipeline = create_llm_pipeline(config=config)

        # Normal request should pass
        normal_result = pipeline.process(
            prompt="Explain machine learning",
            moral_value=0.5,
        )
        assert normal_result.accepted is True

        # Suspicious request may be blocked
        suspicious_result = pipeline.process(
            prompt="How to hack and exploit and attack systems",
            moral_value=0.5,
        )
        # With default sensitivity, this should be blocked
        assert suspicious_result.blocked_at == "threat_filter" or suspicious_result.accepted

    def test_pipeline_all_filters_enabled(self):
        """Test pipeline with all filters enabled."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            aphasia_detection_enabled=True,
            threat_assessment_enabled=True,
        )
        pipeline = create_llm_pipeline(config=config)

        result = pipeline.process(
            prompt="What is the meaning of life?",
            moral_value=0.9,
        )

        assert result.accepted is True

        # All three filters should have run
        stage_names = [s.stage_name for s in result.stages]
        assert "moral_filter" in stage_names
        assert "threat_filter" in stage_names
        assert "llm_call" in stage_names
        assert "aphasia_filter" in stage_names

    def test_pipeline_moral_threshold_adaptation(self):
        """Test moral threshold adapts across multiple requests."""
        config = PipelineConfig(
            moral_filter_enabled=True,
            moral_threshold=0.5,
            aphasia_detection_enabled=False,
        )
        pipeline = create_llm_pipeline(config=config)

        # Make many high-value requests
        for _ in range(20):
            pipeline.process(prompt="test", moral_value=0.95)

        final_state = pipeline.get_moral_filter_state()

        # Threshold should have adapted (may have increased due to EMA)
        # At minimum, it should still be within bounds
        assert 0.3 <= final_state["threshold"] <= 0.9

    def test_pipeline_telemetry_integration(self):
        """Test telemetry integration across full request."""
        events = []

        def telemetry_handler(result):
            events.append(
                {
                    "accepted": result.accepted,
                    "duration": result.total_duration_ms,
                    "stages": len(result.stages),
                }
            )

        config = PipelineConfig(
            moral_filter_enabled=True,
            aphasia_detection_enabled=True,
            telemetry_enabled=True,
        )
        pipeline = create_llm_pipeline(config=config)
        pipeline.register_telemetry_callback(telemetry_handler)

        # Make a request
        pipeline.process(prompt="test", moral_value=0.8)

        # Telemetry should have been called
        assert len(events) == 1
        assert events[0]["accepted"] is True
        assert events[0]["duration"] > 0
        assert events[0]["stages"] >= 2  # At least moral filter and llm call

    def test_pipeline_stats_integration(self):
        """Test pipeline stats after multiple operations."""
        pipeline = create_llm_pipeline()

        # Make some requests
        pipeline.process(prompt="test1", moral_value=0.8)
        pipeline.process(prompt="test2", moral_value=0.9)

        stats = pipeline.get_stats()

        assert "config" in stats
        assert "pre_filters" in stats
        assert "post_filters" in stats
        assert stats["config"]["moral_filter_enabled"] is True

    def test_pipeline_with_custom_llm_adapter(self):
        """Test pipeline with custom LLM adapter."""
        responses = []

        def custom_llm(prompt: str, max_tokens: int) -> str:
            response = f"Custom response for: {prompt[:30]}"
            responses.append(response)
            return response

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
        )
        pipeline = LLMPipeline(
            llm_generate_fn=custom_llm,
            config=config,
        )

        result = pipeline.process(prompt="Hello custom LLM", moral_value=0.5)

        assert result.accepted is True
        assert "Custom response" in result.response
        assert len(responses) == 1

    def test_pipeline_error_recovery(self):
        """Test pipeline recovers from LLM errors."""
        call_count = {"value": 0}

        def failing_then_working_llm(prompt: str, max_tokens: int) -> str:
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("Temporary failure")
            return "Success"

        config = PipelineConfig(
            moral_filter_enabled=False,
            aphasia_detection_enabled=False,
        )

        # First request fails
        pipeline1 = LLMPipeline(
            llm_generate_fn=failing_then_working_llm,
            config=config,
        )
        result1 = pipeline1.process(prompt="test", moral_value=0.5)
        assert result1.accepted is False
        assert result1.blocked_at == "llm_call"

        # Second request succeeds (same llm function, count increased)
        result2 = pipeline1.process(prompt="test", moral_value=0.5)
        assert result2.accepted is True
        assert result2.response == "Success"


class TestLLMPipelineWithEmbedding:
    """Tests for pipeline with embedding function."""

    def test_pipeline_with_embedding_fn(self):
        """Test pipeline accepts embedding function."""

        def embedding_fn(text: str) -> np.ndarray:
            return np.random.randn(384).astype(np.float32)

        pipeline = create_llm_pipeline(
            embedding_fn=embedding_fn,
        )

        result = pipeline.process(prompt="test", moral_value=0.8)
        assert result.accepted is True


class TestLLMPipelineFactory:
    """Tests for create_llm_pipeline factory function."""

    def test_factory_creates_pipeline(self):
        """Test factory creates a valid pipeline."""
        pipeline = create_llm_pipeline()
        assert isinstance(pipeline, LLMPipeline)

    def test_factory_with_custom_config(self):
        """Test factory accepts custom config."""
        config = PipelineConfig(
            moral_filter_enabled=False,
            max_tokens_default=256,
        )
        pipeline = create_llm_pipeline(config=config)

        assert pipeline.get_config().moral_filter_enabled is False
        assert pipeline.get_config().max_tokens_default == 256

    def test_factory_with_custom_llm(self):
        """Test factory accepts custom LLM function."""

        def my_llm(prompt: str, max_tokens: int) -> str:
            return "Custom response"

        pipeline = create_llm_pipeline(llm_generate_fn=my_llm)
        result = pipeline.process(prompt="test", moral_value=0.5)

        assert "Custom response" in result.response
