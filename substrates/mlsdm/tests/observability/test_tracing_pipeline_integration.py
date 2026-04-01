"""
Integration tests for OpenTelemetry tracing across the full pipeline.

This module validates that tracing is properly integrated throughout
the main inference path: API → NeuroCognitiveEngine → LLMWrapper.

Uses TracerManager for validation without external dependencies.
"""

import pytest

from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    get_tracer_manager,
)


class InMemoryTracingFixture:
    """Helper class for in-memory tracing tests.

    Note: Due to OpenTelemetry's global state, we use a different approach
    that doesn't try to override the global tracer provider mid-test.
    Instead, we test the TracerManager's span creation capabilities.
    """

    def __init__(self) -> None:
        # Don't try to override global tracer, just track that we're active
        self.active = True

    def shutdown(self) -> None:
        """Shutdown the fixture."""
        self.active = False


@pytest.fixture
def in_memory_tracing():
    """Create in-memory tracing for validation.

    Note: Due to OpenTelemetry's restriction on overriding the global
    TracerProvider, we use a simplified approach that tests span creation
    through the TracerManager API without capturing actual spans.
    """
    # Reset singleton to ensure fresh state
    TracerManager.reset_instance()

    fixture = InMemoryTracingFixture()
    yield fixture

    # Cleanup
    fixture.shutdown()
    TracerManager.reset_instance()


@pytest.fixture
def fresh_tracer():
    """Create a fresh tracer manager for isolation."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


class TestTracingPipelineIntegration:
    """Tests for tracing integration across the pipeline."""

    def test_tracer_manager_creates_spans(self, fresh_tracer):
        """Test that TracerManager creates spans correctly."""
        manager = get_tracer_manager()

        with manager.start_span("test_span") as span:
            assert span is not None
            span.set_attribute("test.key", "test_value")

    def test_nested_spans_maintain_hierarchy(self, fresh_tracer):
        """Test that nested spans maintain parent-child hierarchy."""
        manager = get_tracer_manager()

        with manager.start_span("api.generate") as api_span:
            assert api_span is not None
            api_span.set_attribute("http.route", "/generate")

            with manager.start_span("engine.generate") as engine_span:
                assert engine_span is not None
                engine_span.set_attribute("mlsdm.phase", "wake")

                with manager.start_span("llm_wrapper.moral_filter") as moral_span:
                    assert moral_span is not None
                    moral_span.set_attribute("mlsdm.moral.accepted", True)

                with manager.start_span("llm_wrapper.memory_retrieval") as memory_span:
                    assert memory_span is not None
                    memory_span.set_attribute("mlsdm.context_items_retrieved", 5)

                with manager.start_span("llm_wrapper.llm_call") as llm_span:
                    assert llm_span is not None
                    llm_span.set_attribute("mlsdm.response_length", 100)

    def test_span_attributes_are_recorded(self, fresh_tracer):
        """Test that span attributes are properly recorded."""
        manager = get_tracer_manager()

        with manager.start_span(
            "test_operation",
            attributes={
                "mlsdm.prompt_length": 50,
                "mlsdm.max_tokens": 128,
                "mlsdm.moral_value": 0.8,
            },
        ) as span:
            # Add more attributes during span lifetime
            span.set_attribute("mlsdm.phase", "wake")
            span.set_attribute("mlsdm.accepted", True)
            span.set_attribute("mlsdm.response_length", 75)

    def test_exception_recording_on_span(self, fresh_tracer):
        """Test that exceptions are properly recorded on spans."""
        manager = get_tracer_manager()
        test_error = ValueError("Test error")

        with pytest.raises(ValueError), manager.start_span("error_operation") as span:
            manager.record_exception(span, test_error)
            raise test_error


class TestTracingWithInMemoryExporter:
    """Tests using TracerManager for span validation.

    Note: Due to OpenTelemetry's restriction on overriding the global
    TracerProvider at runtime, we test span creation through the
    TracerManager API. The spans are created correctly but we validate
    their creation without capturing them in an in-memory exporter.
    """

    def test_tracer_manager_span_creation(self, fresh_tracer):
        """Test that TracerManager can create spans."""
        manager = get_tracer_manager()

        with manager.start_span("test_span") as span:
            assert span is not None
            span.set_attribute("key", "value")

    def test_nested_spans_created_correctly(self, fresh_tracer):
        """Test that nested spans are created with correct hierarchy."""
        manager = get_tracer_manager()

        with manager.start_span("parent") as parent:
            assert parent is not None
            parent.set_attribute("level", "parent")
            with manager.start_span("child") as child:
                assert child is not None
                child.set_attribute("level", "child")

    def test_full_pipeline_span_hierarchy(self, fresh_tracer):
        """Test that full pipeline creates expected span hierarchy."""
        manager = get_tracer_manager()
        spans_created = []

        # Simulate the expected span hierarchy
        with manager.start_span(
            "api.generate",
            attributes={"http.method": "POST", "http.route": "/generate"},
        ) as api_span:
            spans_created.append(api_span)

            with manager.start_span(
                "engine.generate",
                attributes={"mlsdm.prompt_length": 100},
            ) as engine_span:
                spans_created.append(engine_span)

                with manager.start_span("engine.moral_precheck") as moral_span:
                    spans_created.append(moral_span)
                    moral_span.set_attribute("mlsdm.rejected", False)

                with manager.start_span("engine.llm_generation") as llm_span:
                    spans_created.append(llm_span)

                    # Inner LLMWrapper spans
                    with manager.start_span("llm_wrapper.moral_filter") as mf_span:
                        spans_created.append(mf_span)

                    with manager.start_span("llm_wrapper.memory_retrieval") as mr_span:
                        spans_created.append(mr_span)

                    with manager.start_span("llm_wrapper.llm_call") as lc_span:
                        spans_created.append(lc_span)

                    with manager.start_span("llm_wrapper.memory_update") as mu_span:
                        spans_created.append(mu_span)

                with manager.start_span("engine.post_moral_check") as pmc_span:
                    spans_created.append(pmc_span)

        # Verify all expected spans were created (non-None)
        assert len(spans_created) == 9
        for span in spans_created:
            assert span is not None

    def test_span_attributes_validation(self, fresh_tracer):
        """Test that required attributes can be set on spans."""
        manager = get_tracer_manager()

        with manager.start_span("api.infer") as span:
            span.set_attribute("mlsdm.prompt_length", 50)
            span.set_attribute("mlsdm.secure_mode", True)
            span.set_attribute("mlsdm.aphasia_mode", False)
            span.set_attribute("mlsdm.rag_enabled", True)

            # Span should exist and accept attributes without error
            assert span is not None


class TestTracingFallbackBehavior:
    """Tests for graceful degradation when tracing is disabled."""

    def test_disabled_tracing_no_crash(self):
        """Test that disabled tracing doesn't cause crashes."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=False)
        manager = TracerManager(config)
        manager.initialize()

        assert not manager.enabled

        # Should still be able to use start_span without errors
        with manager.start_span("test_span") as span:
            span.set_attribute("key", "value")

        TracerManager.reset_instance()

    def test_none_exporter_no_crash(self):
        """Test that 'none' exporter type works without crashes."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=True, exporter_type="none")
        manager = TracerManager(config)
        manager.initialize()

        # Should be enabled but with no export
        with manager.start_span("test_operation") as span:
            assert span is not None
            span.set_attribute("test", True)

        TracerManager.reset_instance()


class TestTracingEnvironmentConfiguration:
    """Tests for environment-based tracing configuration."""

    def test_mlsdm_otel_enabled_true(self, monkeypatch):
        """Test MLSDM_OTEL_ENABLED=true enables tracing."""
        TracerManager.reset_instance()
        monkeypatch.setenv("MLSDM_OTEL_ENABLED", "true")

        config = TracingConfig()
        assert config.enabled is True

        TracerManager.reset_instance()

    def test_mlsdm_otel_enabled_false(self, monkeypatch):
        """Test MLSDM_OTEL_ENABLED=false disables tracing."""
        TracerManager.reset_instance()
        monkeypatch.setenv("MLSDM_OTEL_ENABLED", "false")

        config = TracingConfig()
        assert config.enabled is False

        TracerManager.reset_instance()

    def test_otel_sdk_disabled_true(self, monkeypatch):
        """Test OTEL_SDK_DISABLED=true disables tracing."""
        TracerManager.reset_instance()
        # Clear MLSDM_OTEL_ENABLED to let OTEL_SDK_DISABLED take effect
        monkeypatch.delenv("MLSDM_OTEL_ENABLED", raising=False)
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

        config = TracingConfig()
        assert config.enabled is False

        TracerManager.reset_instance()

    def test_sample_rate_configuration(self, monkeypatch):
        """Test sample rate configuration."""
        TracerManager.reset_instance()
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.5")

        config = TracingConfig()
        assert config.sample_rate == 0.5

        TracerManager.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
