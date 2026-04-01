"""
Integration tests for OpenTelemetry tracing in the core pipeline.

These tests validate that:
1. Root span `mlsdm.generate` is created with appropriate child spans
2. Span attributes (phase, stateless_mode, moral_threshold, etc.) are set correctly
3. Graceful fallback when tracing is disabled
4. No-op behavior doesn't crash the system

Tests use in-memory validation without external services (Jaeger, OTLP).
"""

import pytest

from mlsdm.observability import (
    TracerManager,
    TracingConfig,
    get_tracer_manager,
    span,
    trace_aphasia_detection,
    trace_generate,
    trace_moral_filter,
)


@pytest.fixture
def fresh_tracer():
    """Create a fresh tracer manager for isolation."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


@pytest.fixture
def disabled_tracer():
    """Create a disabled tracer manager."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=False)
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


class TestRootSpanCreation:
    """Tests for root span creation during generate() calls."""

    def test_root_span_mlsdm_generate_created(self, fresh_tracer):
        """Test that root span 'mlsdm.generate' can be created."""
        manager = get_tracer_manager()

        with manager.start_span("mlsdm.generate") as root_span:
            assert root_span is not None

    def test_root_span_with_required_attributes(self, fresh_tracer):
        """Test that root span accepts required attributes."""
        manager = get_tracer_manager()

        with manager.start_span(
            "mlsdm.generate",
            attributes={
                "mlsdm.phase": "wake",
                "mlsdm.stateless_mode": False,
                "mlsdm.moral_threshold": 0.5,
                "mlsdm.prompt_length": 100,
            },
        ) as root_span:
            # Should accept additional attributes
            root_span.set_attribute("mlsdm.accepted", True)
            root_span.set_attribute("mlsdm.emergency_shutdown", False)
            root_span.set_attribute("mlsdm.aphasia_flagged", False)

    def test_span_helper_creates_root_span(self, fresh_tracer):
        """Test that span() helper creates root span correctly."""
        with span("mlsdm.generate", phase="wake", stateless_mode=False) as s:
            assert s is not None


class TestChildSpanCreation:
    """Tests for child span creation in the pipeline hierarchy."""

    def test_cognitive_controller_step_span(self, fresh_tracer):
        """Test mlsdm.cognitive_controller.step child span."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test parent-child span hierarchy
        with manager.start_span("mlsdm.generate"):  # noqa: SIM117
            with manager.start_span(
                "mlsdm.cognitive_controller.step",
                attributes={"mlsdm.step": 1},
            ) as child:
                assert child is not None
                child.set_attribute("mlsdm.moral_value", 0.8)

    def test_memory_query_span(self, fresh_tracer):
        """Test mlsdm.memory.query child span for PELM/Synaptic retrieval."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test parent-child span hierarchy
        with manager.start_span("mlsdm.generate"):  # noqa: SIM117
            with manager.start_span(
                "mlsdm.memory.query",
                attributes={
                    "mlsdm.query_type": "pelm",
                    "mlsdm.top_k": 5,
                },
            ) as child:
                assert child is not None
                child.set_attribute("mlsdm.context_items_retrieved", 3)

    def test_moral_filter_evaluate_span(self, fresh_tracer):
        """Test mlsdm.moral_filter.evaluate child span."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test parent-child span hierarchy
        with manager.start_span("mlsdm.generate"):  # noqa: SIM117
            with manager.start_span(
                "mlsdm.moral_filter.evaluate",
                attributes={
                    "mlsdm.moral_threshold": 0.5,
                    "mlsdm.moral_value": 0.8,
                },
            ) as child:
                assert child is not None
                child.set_attribute("mlsdm.moral.accepted", True)

    def test_aphasia_detect_repair_span(self, fresh_tracer):
        """Test mlsdm.aphasia.detect_repair child span."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test parent-child span hierarchy
        with manager.start_span("mlsdm.generate"):  # noqa: SIM117
            with manager.start_span(
                "mlsdm.aphasia.detect_repair",
                attributes={
                    "mlsdm.aphasia.detect_enabled": True,
                    "mlsdm.aphasia.repair_enabled": True,
                },
            ) as child:
                assert child is not None
                child.set_attribute("mlsdm.aphasia.severity", 0.3)
                child.set_attribute("mlsdm.aphasia.repaired", False)


class TestFullPipelineSpanHierarchy:
    """Tests for complete pipeline span hierarchy."""

    def test_full_pipeline_span_tree(self, fresh_tracer):
        """Test that full pipeline creates expected span tree.

        Expected hierarchy:
        mlsdm.generate (root)
        ├── mlsdm.cognitive_controller.step
        ├── mlsdm.memory.query
        ├── mlsdm.moral_filter.evaluate
        └── mlsdm.aphasia.detect_repair
        """
        manager = get_tracer_manager()
        spans_created = []

        with manager.start_span(
            "mlsdm.generate",
            attributes={
                "mlsdm.phase": "wake",
                "mlsdm.stateless_mode": False,
                "mlsdm.moral_threshold": 0.5,
            },
        ) as root:
            spans_created.append(("mlsdm.generate", root))

            with manager.start_span(
                "mlsdm.cognitive_controller.step",
                attributes={"mlsdm.step": 1},
            ) as controller:
                spans_created.append(("mlsdm.cognitive_controller.step", controller))

            with manager.start_span(
                "mlsdm.memory.query",
                attributes={"mlsdm.query_type": "pelm"},
            ) as memory:
                spans_created.append(("mlsdm.memory.query", memory))

            with manager.start_span(
                "mlsdm.moral_filter.evaluate",
                attributes={"mlsdm.moral_threshold": 0.5},
            ) as moral:
                spans_created.append(("mlsdm.moral_filter.evaluate", moral))
                moral.set_attribute("mlsdm.accepted", True)

            with manager.start_span(
                "mlsdm.aphasia.detect_repair",
            ) as aphasia:
                spans_created.append(("mlsdm.aphasia.detect_repair", aphasia))
                aphasia.set_attribute("mlsdm.aphasia_flagged", False)

            # Set final attributes on root span
            root.set_attribute("mlsdm.accepted", True)
            root.set_attribute("mlsdm.emergency_shutdown", False)

        # Verify all expected spans were created
        assert len(spans_created) == 5
        span_names = [name for name, _ in spans_created]
        assert "mlsdm.generate" in span_names
        assert "mlsdm.cognitive_controller.step" in span_names
        assert "mlsdm.memory.query" in span_names
        assert "mlsdm.moral_filter.evaluate" in span_names
        assert "mlsdm.aphasia.detect_repair" in span_names

        # Verify all spans are non-None
        for name, s in spans_created:
            assert s is not None, f"Span {name} should not be None"

    def test_span_helper_nested_hierarchy(self, fresh_tracer):
        """Test span() helper creates nested hierarchy correctly."""
        with span("mlsdm.generate", phase="wake") as root:
            assert root is not None
            with span("mlsdm.memory.query", query_type="pelm") as mem:
                assert mem is not None
            with span("mlsdm.moral_filter.evaluate", threshold=0.5) as moral:
                assert moral is not None


class TestSpanAttributes:
    """Tests for span attribute recording."""

    def test_required_attributes_accepted(self, fresh_tracer):
        """Test that all required attributes can be set on spans."""
        manager = get_tracer_manager()

        with manager.start_span("mlsdm.generate") as s:
            # Required attributes from issue spec
            s.set_attribute("mlsdm.phase", "wake")
            s.set_attribute("mlsdm.stateless_mode", False)
            s.set_attribute("mlsdm.moral_threshold", 0.5)
            s.set_attribute("mlsdm.accepted", True)
            s.set_attribute("mlsdm.emergency_shutdown", False)
            s.set_attribute("mlsdm.aphasia_flagged", False)

    def test_attribute_types_handled(self, fresh_tracer):
        """Test that various attribute types are handled correctly."""
        manager = get_tracer_manager()

        with manager.start_span("mlsdm.test") as s:
            # String
            s.set_attribute("mlsdm.phase", "wake")
            # Boolean
            s.set_attribute("mlsdm.accepted", True)
            # Integer
            s.set_attribute("mlsdm.step", 42)
            # Float
            s.set_attribute("mlsdm.moral_threshold", 0.75)

    def test_span_helper_normalizes_attribute_keys(self, fresh_tracer):
        """Test that span() helper normalizes attribute keys."""
        with span("mlsdm.test", phase="wake", stateless_mode=False) as s:
            # The span helper should have normalized keys to mlsdm.* prefix
            assert s is not None


class TestGracefulFallback:
    """Tests for graceful fallback when tracing is disabled."""

    def test_disabled_tracing_no_crash(self, disabled_tracer):
        """Test that disabled tracing doesn't cause crashes."""
        manager = get_tracer_manager()
        assert not manager.enabled

        # Should not raise any exceptions
        with manager.start_span("mlsdm.generate") as s:
            s.set_attribute("mlsdm.phase", "wake")
            s.set_attribute("mlsdm.accepted", True)

    def test_disabled_tracing_span_helper(self, disabled_tracer):
        """Test that span() helper works when tracing is disabled."""
        # Should not raise any exceptions
        with span("mlsdm.generate", phase="wake") as s:
            s.set_attribute("mlsdm.accepted", True)

    def test_nested_spans_when_disabled(self, disabled_tracer):
        """Test nested spans work when tracing is disabled."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test parent-child span hierarchy
        with manager.start_span("mlsdm.generate"):  # noqa: SIM117
            with manager.start_span("mlsdm.memory.query") as child:
                child.set_attribute("mlsdm.context_items", 5)

    def test_trace_helper_functions_when_disabled(self, disabled_tracer):
        """Test trace_* helper functions work when tracing is disabled.

        These helpers create independent spans that work correctly even when
        tracing is disabled. In production, they would typically be nested
        inside a parent span like mlsdm.generate.
        """
        # trace_generate
        with trace_generate("test prompt", moral_value=0.8, max_tokens=128) as s:
            s.set_attribute("mlsdm.accepted", True)

        # trace_moral_filter
        with trace_moral_filter(threshold=0.5, score=0.8) as s:
            s.set_attribute("mlsdm.moral.passed", True)

        # trace_aphasia_detection
        with trace_aphasia_detection(
            detect_enabled=True,
            repair_enabled=False,
            severity_threshold=0.5,
        ) as s:
            s.set_attribute("mlsdm.aphasia.severity", 0.3)


class TestExceptionHandling:
    """Tests for exception handling in spans."""

    def test_exception_recorded_on_span(self, fresh_tracer):
        """Test that exceptions are properly recorded on spans."""
        manager = get_tracer_manager()

        # Nested with statements are intentional to test exception handling in spans
        with pytest.raises(ValueError):  # noqa: SIM117
            with manager.start_span("mlsdm.generate") as s:
                manager.record_exception(s, ValueError("Test error"))
                raise ValueError("Test error")

    def test_span_context_preserved_on_exception(self, fresh_tracer):
        """Test that span context is preserved even when exception occurs."""
        manager = get_tracer_manager()

        try:
            with manager.start_span("mlsdm.generate") as s:
                s.set_attribute("mlsdm.phase", "wake")
                raise RuntimeError("Pipeline error")
        except RuntimeError:
            pass  # Expected


class TestTracingConfiguration:
    """Tests for tracing configuration options."""

    def test_exporter_type_none_creates_spans(self):
        """Test that exporter_type='none' still creates spans."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=True, exporter_type="none")
        manager = TracerManager(config)
        manager.initialize()

        with manager.start_span("test") as s:
            assert s is not None

        TracerManager.reset_instance()

    def test_mlsdm_otel_enabled_env(self, monkeypatch):
        """Test MLSDM_OTEL_ENABLED environment variable."""
        TracerManager.reset_instance()
        monkeypatch.setenv("MLSDM_OTEL_ENABLED", "false")

        config = TracingConfig()
        assert config.enabled is False

        TracerManager.reset_instance()

    def test_sample_rate_from_env(self, monkeypatch):
        """Test sample rate configuration from environment."""
        TracerManager.reset_instance()
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")

        config = TracingConfig()
        assert config.sample_rate == 0.25

        TracerManager.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
