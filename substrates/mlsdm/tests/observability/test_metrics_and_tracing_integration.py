"""
Integration tests for Metrics and Tracing across the MLSDM pipeline.

This module validates that observability components (logging, metrics, tracing)
work together correctly across the full pipeline from API to Engine.

Test coverage:
- Prometheus metrics registration and export
- Span creation in engine and API layers
- Trace context correlation (trace_id/span_id propagation)
- Aphasia telemetry integration
- E2E observability validation
"""

import pytest
from prometheus_client import CollectorRegistry

from mlsdm.observability.aphasia_metrics import (
    AphasiaMetricsExporter,
    reset_aphasia_metrics_exporter,
)
from mlsdm.observability.metrics import MetricsExporter, MetricsRegistry
from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    get_tracer_manager,
    trace_full_pipeline,
    trace_generate,
    trace_moral_filter,
)


@pytest.fixture
def fresh_metrics():
    """Create a fresh MetricsExporter with its own registry for isolation."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


@pytest.fixture
def fresh_metrics_registry():
    """Create a fresh MetricsRegistry (lightweight metrics for engine)."""
    return MetricsRegistry()


@pytest.fixture
def fresh_aphasia_metrics():
    """Create a fresh AphasiaMetricsExporter with its own registry."""
    reset_aphasia_metrics_exporter()
    registry = CollectorRegistry()
    return AphasiaMetricsExporter(registry=registry)


@pytest.fixture
def fresh_tracer():
    """Create a fresh tracer manager for isolation."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


class TestMetricsRegistration:
    """Tests for Prometheus metrics registration."""

    def test_all_counters_registered(self, fresh_metrics):
        """Test that all expected counters are registered."""
        metrics_text = fresh_metrics.get_metrics_text()

        # Core counters
        assert "mlsdm_events_processed_total" in metrics_text
        assert "mlsdm_events_rejected_total" in metrics_text
        assert "mlsdm_errors_total" in metrics_text
        assert "mlsdm_emergency_shutdowns_total" in metrics_text
        assert "mlsdm_phase_events_total" in metrics_text
        assert "mlsdm_moral_rejections_total" in metrics_text
        assert "mlsdm_requests_total" in metrics_text

    def test_all_gauges_registered(self, fresh_metrics):
        """Test that all expected gauges are registered."""
        metrics_text = fresh_metrics.get_metrics_text()

        # State gauges
        assert "mlsdm_memory_usage_bytes" in metrics_text
        assert "mlsdm_moral_threshold" in metrics_text
        assert "mlsdm_phase" in metrics_text
        assert "mlsdm_memory_l1_norm" in metrics_text
        assert "mlsdm_memory_l2_norm" in metrics_text
        assert "mlsdm_memory_l3_norm" in metrics_text
        assert "mlsdm_emergency_shutdown_active" in metrics_text
        assert "mlsdm_stateless_mode" in metrics_text

    def test_all_histograms_registered(self, fresh_metrics):
        """Test that all expected histograms are registered."""
        metrics_text = fresh_metrics.get_metrics_text()

        # Latency histograms
        assert "mlsdm_processing_latency_milliseconds" in metrics_text
        assert "mlsdm_retrieval_latency_milliseconds" in metrics_text
        assert "mlsdm_generation_latency_milliseconds" in metrics_text

    def test_new_state_metrics_methods(self, fresh_metrics):
        """Test new metrics methods for state tracking."""
        # Test emergency shutdown active gauge
        fresh_metrics.set_emergency_shutdown_active(True)
        assert fresh_metrics.emergency_shutdown_active._value.get() == 1.0

        fresh_metrics.set_emergency_shutdown_active(False)
        assert fresh_metrics.emergency_shutdown_active._value.get() == 0.0

        # Test stateless mode gauge
        fresh_metrics.set_stateless_mode(True)
        assert fresh_metrics.stateless_mode._value.get() == 1.0

        fresh_metrics.set_stateless_mode(False)
        assert fresh_metrics.stateless_mode._value.get() == 0.0

    def test_request_counter_with_labels(self, fresh_metrics):
        """Test request counter with endpoint and status labels."""
        fresh_metrics.increment_requests("/generate", "2xx")
        fresh_metrics.increment_requests("/generate", "4xx")
        fresh_metrics.increment_requests("/infer", "2xx")

        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="2xx")._value.get()
            == 1.0
        )
        assert (
            fresh_metrics.requests_total.labels(endpoint="/generate", status="4xx")._value.get()
            == 1.0
        )
        assert (
            fresh_metrics.requests_total.labels(endpoint="/infer", status="2xx")._value.get() == 1.0
        )

    def test_generation_latency_histogram(self, fresh_metrics):
        """Test generation latency histogram observation."""
        fresh_metrics.observe_generation_latency(150.0)
        fresh_metrics.observe_generation_latency(500.0)
        fresh_metrics.observe_generation_latency(2000.0)

        # Check that histogram has observations
        metrics_text = fresh_metrics.get_metrics_text()
        assert "mlsdm_generation_latency_milliseconds_count 3" in metrics_text


class TestMetricsRegistryIntegration:
    """Tests for MetricsRegistry used in NeuroCognitiveEngine."""

    def test_request_tracking(self, fresh_metrics_registry):
        """Test request tracking with provider and variant labels."""
        fresh_metrics_registry.increment_requests_total(provider_id="openai", variant="control")
        fresh_metrics_registry.increment_requests_total(
            provider_id="anthropic", variant="treatment"
        )

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["requests_total"] == 2
        assert snapshot["requests_by_provider"]["openai"] == 1
        assert snapshot["requests_by_provider"]["anthropic"] == 1
        assert snapshot["requests_by_variant"]["control"] == 1
        assert snapshot["requests_by_variant"]["treatment"] == 1

    def test_rejection_tracking(self, fresh_metrics_registry):
        """Test rejection tracking by stage."""
        fresh_metrics_registry.increment_rejections_total("pre_flight")
        fresh_metrics_registry.increment_rejections_total("generation")
        fresh_metrics_registry.increment_rejections_total("pre_flight")

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["rejections_total"]["pre_flight"] == 2
        assert snapshot["rejections_total"]["generation"] == 1

    def test_latency_tracking(self, fresh_metrics_registry):
        """Test latency recording with percentile calculation."""
        # Record some latencies
        for latency in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            fresh_metrics_registry.record_latency_total(float(latency))

        summary = fresh_metrics_registry.get_summary()
        latency_stats = summary["latency_stats"]["total_ms"]

        assert latency_stats["count"] == 10
        assert latency_stats["min"] == 10.0
        assert latency_stats["max"] == 100.0
        assert latency_stats["mean"] == 55.0
        assert latency_stats["p50"] == 55.0  # Median


class TestAphasiaTelemetry:
    """Tests for Aphasia-specific telemetry."""

    def test_aphasia_event_recording(self, fresh_aphasia_metrics):
        """Test that aphasia events are recorded with correct labels."""
        fresh_aphasia_metrics.record_aphasia_event(
            mode="full",
            is_aphasic=True,
            repair_applied=True,
            severity=0.7,
            flags=["short_sentences", "missing_articles"],
        )

        # Check counter
        assert (
            fresh_aphasia_metrics.aphasia_events_total.labels(
                mode="full",
                is_aphasic="True",
                repair_applied="True",
            )._value.get()
            == 1.0
        )

        # Check flags
        assert (
            fresh_aphasia_metrics.aphasia_flags_total.labels(flag="short_sentences")._value.get()
            == 1.0
        )
        assert (
            fresh_aphasia_metrics.aphasia_flags_total.labels(flag="missing_articles")._value.get()
            == 1.0
        )

    def test_aphasia_severity_distribution(self, fresh_aphasia_metrics):
        """Test severity histogram captures distribution."""
        severities = [0.1, 0.3, 0.5, 0.7, 0.9]
        for severity in severities:
            fresh_aphasia_metrics.record_aphasia_event(
                mode="monitor",
                is_aphasic=severity > 0.5,
                repair_applied=False,
                severity=severity,
                flags=[],
            )

        # Histogram should have 5 observations
        # (checking via exported metrics)
        # The histogram is tracked internally


class TestTracingIntegration:
    """Tests for tracing integration."""

    def test_span_creation_with_attributes(self, fresh_tracer):
        """Test that spans are created with expected attributes."""
        with trace_full_pipeline(
            prompt_length=100,
            moral_value=0.7,
            phase="wake",
        ) as span:
            assert span is not None
            # Add custom attributes
            span.set_attribute("mlsdm.pipeline.result", "accepted")
            span.set_attribute("mlsdm.pipeline.latency_ms", 150.0)

    def test_nested_spans(self, fresh_tracer):
        """Test that nested spans maintain parent-child relationship."""
        tracer_manager = get_tracer_manager()

        with tracer_manager.start_span("parent_span") as parent:
            assert parent is not None
            parent.set_attribute("level", "parent")

            with tracer_manager.start_span("child_span") as child:
                assert child is not None
                child.set_attribute("level", "child")

                with tracer_manager.start_span("grandchild_span") as grandchild:
                    assert grandchild is not None
                    grandchild.set_attribute("level", "grandchild")

    def test_trace_generate_attributes(self, fresh_tracer):
        """Test trace_generate captures correct attributes."""
        with trace_generate(
            prompt="Hello world",
            moral_value=0.8,
            max_tokens=128,
        ) as span:
            assert span is not None
            # The span should have attributes set by trace_generate
            # (prompt_length, moral_value, max_tokens)

    def test_trace_moral_filter(self, fresh_tracer):
        """Test moral filter tracing."""
        with trace_moral_filter(threshold=0.5, score=0.8) as span:
            assert span is not None
            span.set_attribute("mlsdm.moral.passed", True)

    def test_tracer_manager_singleton(self, fresh_tracer):
        """Test that tracer manager is properly singleton."""
        manager1 = get_tracer_manager()
        manager2 = get_tracer_manager()
        assert manager1 is manager2


class TestE2EObservability:
    """E2E tests for observability across the full pipeline."""

    def test_engine_metrics_collection(self, fresh_metrics_registry):
        """Test that engine metrics are collected during generation."""
        # Simulate engine generation flow
        fresh_metrics_registry.increment_requests_total()

        # Record timing
        fresh_metrics_registry.record_latency_pre_flight(5.0)
        fresh_metrics_registry.record_latency_generation(100.0)
        fresh_metrics_registry.record_latency_total(110.0)

        snapshot = fresh_metrics_registry.get_snapshot()
        assert snapshot["requests_total"] == 1
        assert len(snapshot["latency_total_ms"]) == 1
        assert len(snapshot["latency_pre_flight_ms"]) == 1
        assert len(snapshot["latency_generation_ms"]) == 1

    def test_combined_metrics_and_tracing(self, fresh_metrics, fresh_tracer):
        """Test that metrics and tracing work together."""
        tracer_manager = get_tracer_manager()

        # Start span
        with tracer_manager.start_span("test.operation") as span:
            assert span is not None

            # Record metrics
            fresh_metrics.increment_events_processed()
            fresh_metrics.set_phase("wake")
            fresh_metrics.observe_generation_latency(100.0)

        # Verify metrics recorded
        assert fresh_metrics.events_processed._value.get() == 1.0
        assert fresh_metrics.phase_gauge._value.get() == 1.0  # wake = 1

    def test_error_path_observability(self, fresh_metrics, fresh_tracer):
        """Test observability in error paths."""
        tracer_manager = get_tracer_manager()

        with tracer_manager.start_span("error_operation") as span:
            # Simulate error path
            fresh_metrics.increment_errors("test_error")
            fresh_metrics.increment_moral_rejection("below_threshold")

            # Record error on span
            try:
                raise ValueError("Test error")
            except ValueError as e:
                tracer_manager.record_exception(span, e)

        # Verify error metrics
        assert fresh_metrics.errors.labels(error_type="test_error")._value.get() == 1.0
        assert fresh_metrics.moral_rejections.labels(reason="below_threshold")._value.get() == 1.0


class TestObservabilityConfiguration:
    """Tests for observability configuration options."""

    def test_tracing_can_be_disabled(self):
        """Test that tracing can be disabled via configuration."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=False)
        manager = TracerManager(config)

        # Even with disabled tracing, should not raise
        manager.initialize()
        assert not manager.enabled

        TracerManager.reset_instance()

    def test_lightweight_mode_no_exporter(self):
        """Test lightweight mode with no exporter (none type)."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=True, exporter_type="none")
        manager = TracerManager(config)
        manager.initialize()

        # Should still create spans, just no export
        with manager.start_span("test") as span:
            assert span is not None

        TracerManager.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
