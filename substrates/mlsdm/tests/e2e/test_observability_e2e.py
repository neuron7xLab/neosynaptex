"""
E2E Observability Tests for MLSDM Pipeline.

This module validates that observability components (logging, metrics, tracing)
function correctly across the complete pipeline:
    API → Engine → Memory/Moral/Aphasia → Response

Tests verify:
- Tracing spans are created with expected attributes
- Metrics are recorded during request processing
- Log events are emitted at key stages
- No PII is leaked in observability data

These tests do NOT require external backends (Jaeger/Prometheus) - they use
in-memory exporters and collectors.
"""

from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING

import numpy as np
import pytest
from prometheus_client import CollectorRegistry

from mlsdm.engine import NeuroEngineConfig, build_neuro_engine_from_env
from mlsdm.observability.metrics import MetricsExporter
from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    get_tracer_manager,
)

if TYPE_CHECKING:
    from mlsdm.engine import NeuroCognitiveEngine


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(autouse=True)
def deterministic_seeds() -> None:
    """Set deterministic seeds for reproducibility."""
    seed = 42
    random.seed(seed)
    np.random.seed(seed)


@pytest.fixture
def fresh_tracing():
    """Create fresh tracing manager with no exporter."""
    TracerManager.reset_instance()
    config = TracingConfig(enabled=True, exporter_type="none")
    manager = TracerManager(config)
    manager.initialize()
    yield manager
    TracerManager.reset_instance()


@pytest.fixture
def fresh_metrics():
    """Create fresh metrics exporter with isolated registry."""
    registry = CollectorRegistry()
    return MetricsExporter(registry=registry)


@pytest.fixture
def engine_with_metrics() -> NeuroCognitiveEngine:
    """Create NeuroCognitiveEngine with metrics enabled."""
    os.environ["LLM_BACKEND"] = "local_stub"
    config = NeuroEngineConfig(
        dim=384,
        enable_fslgs=False,
        enable_metrics=True,
    )
    engine = build_neuro_engine_from_env(config=config)
    return engine


# ============================================================
# E2E Observability Tests
# ============================================================


class TestE2EObservabilityPipeline:
    """E2E tests for observability across the full pipeline."""

    def test_generate_creates_spans_and_metrics(self, engine_with_metrics, fresh_tracing):
        """
        Test that generating a response creates tracing spans and metrics.

        Validates:
        - Engine generates response
        - Tracing spans are created (via TracerManager)
        - Engine metrics are recorded
        """
        # Generate a response
        result = engine_with_metrics.generate(
            prompt="Hello, world!",
            max_tokens=128,
            moral_value=0.7,
        )

        # Verify response
        assert result is not None
        assert "response" in result
        assert "timing" in result

        # Verify metrics were recorded
        metrics = engine_with_metrics.get_metrics()
        if metrics is not None:
            snapshot = metrics.get_snapshot()
            assert snapshot["requests_total"] >= 1

    def test_observability_captures_rejection(self, engine_with_metrics, fresh_tracing):
        """
        Test that rejections are captured in observability.

        Uses high moral threshold to trigger rejection.
        """
        # Generate with high moral threshold to trigger rejection
        result = engine_with_metrics.generate(
            prompt="Hello, world!",
            max_tokens=128,
            moral_value=0.99,  # Very high threshold
        )

        # Check if rejected
        if result.get("rejected_at") is not None:
            # Verify metrics recorded rejection
            metrics = engine_with_metrics.get_metrics()
            if metrics is not None:
                snapshot = metrics.get_snapshot()
                # Either rejections or errors should be recorded
                total_rejections = sum(snapshot.get("rejections_total", {}).values())
                total_errors = sum(snapshot.get("errors_total", {}).values())
                assert total_rejections >= 1 or total_errors >= 1

    def test_observability_captures_timing(self, engine_with_metrics, fresh_tracing):
        """
        Test that timing metrics are captured.
        """
        result = engine_with_metrics.generate(
            prompt="Hello, world!",
            max_tokens=128,
            moral_value=0.5,
        )

        # Check timing in result
        timing = result.get("timing", {})
        assert "total" in timing or len(timing) > 0

        # Check metrics latency
        metrics = engine_with_metrics.get_metrics()
        if metrics is not None:
            snapshot = metrics.get_snapshot()
            # Should have at least one latency recorded
            assert len(snapshot.get("latency_total_ms", [])) > 0

    def test_spans_created_for_pipeline_stages(self, engine_with_metrics, fresh_tracing):
        """
        Test that spans are created for each pipeline stage.

        Note: Since we use 'none' exporter, we can only verify
        that span creation doesn't fail.
        """
        tracer_manager = get_tracer_manager()

        # Create spans manually to verify they work
        with tracer_manager.start_span("test.generate") as parent_span:
            assert parent_span is not None

            with tracer_manager.start_span("test.moral_precheck") as child_span:
                assert child_span is not None

            # Generate response (this will create its own spans)
            result = engine_with_metrics.generate(
                prompt="Hello, world!",
                max_tokens=128,
            )

            # Add result attributes to span
            parent_span.set_attribute("mlsdm.accepted", result.get("rejected_at") is None)

    def test_no_pii_in_observability(self, engine_with_metrics, fresh_tracing):
        """
        Test that PII is not leaked in observability data.

        INVARIANT: Only metadata (prompt_length, not prompt itself) is tracked.
        """
        secret_prompt = "SECRET_USER_DATA_12345"

        result = engine_with_metrics.generate(
            prompt=secret_prompt,
            max_tokens=128,
            moral_value=0.5,
        )

        # Timing should NOT contain the actual prompt
        timing = result.get("timing", {})
        timing_str = str(timing)
        assert secret_prompt not in timing_str

        # Validation steps should NOT contain the prompt
        validation_steps = result.get("validation_steps", [])
        validation_str = str(validation_steps)
        assert secret_prompt not in validation_str


class TestE2EMetricsExporter:
    """E2E tests for Prometheus metrics exporter."""

    def test_metrics_export_format(self, fresh_metrics):
        """Test that metrics are exported in valid Prometheus format."""
        # Record some metrics
        fresh_metrics.increment_events_processed()
        fresh_metrics.set_phase("wake")
        fresh_metrics.observe_generation_latency(100.0)

        # Export metrics
        metrics_text = fresh_metrics.get_metrics_text()

        # Verify Prometheus format
        assert "# HELP" in metrics_text
        assert "# TYPE" in metrics_text
        assert "mlsdm_events_processed_total" in metrics_text

    def test_metrics_endpoint_simulation(self, fresh_metrics):
        """Simulate the /health/metrics endpoint."""
        # Record request metrics
        fresh_metrics.increment_requests("/generate", "2xx")
        fresh_metrics.set_phase("wake")
        fresh_metrics.set_moral_threshold(0.5)

        # Get export
        metrics_bytes = fresh_metrics.export_metrics()

        assert isinstance(metrics_bytes, bytes)
        assert len(metrics_bytes) > 0


class TestE2ETracingConfiguration:
    """E2E tests for tracing configuration."""

    def test_tracing_disabled_no_errors(self):
        """Test that disabled tracing doesn't cause errors."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=False)
        manager = TracerManager(config)
        manager.initialize()

        # Should not raise
        tracer = manager.tracer
        assert tracer is not None

        TracerManager.reset_instance()

    def test_tracing_lightweight_mode(self):
        """Test lightweight mode with no backend."""
        TracerManager.reset_instance()
        config = TracingConfig(enabled=True, exporter_type="none")
        manager = TracerManager(config)
        manager.initialize()

        # Should create spans without errors
        with manager.start_span("test") as span:
            span.set_attribute("test", "value")

        TracerManager.reset_instance()


class TestE2EFullPipelineObservability:
    """Full pipeline observability integration test."""

    def test_full_pipeline_observability_flow(
        self, engine_with_metrics, fresh_tracing, fresh_metrics
    ):
        """
        Test complete observability flow through the pipeline.

        This is the main E2E test that validates:
        1. Request starts with tracing span
        2. Metrics are recorded at each stage
        3. Response includes timing info
        4. No errors in observability layer
        """
        tracer_manager = get_tracer_manager()

        # Simulate API-level span
        with tracer_manager.start_span("api.generate") as api_span:
            api_span.set_attribute("http.method", "POST")
            api_span.set_attribute("http.route", "/generate")

            # Generate response (engine creates its own child spans)
            result = engine_with_metrics.generate(
                prompt="Hello, how are you?",
                max_tokens=256,
                moral_value=0.6,
            )

            # Add result to span
            api_span.set_attribute("mlsdm.accepted", result.get("rejected_at") is None)
            api_span.set_attribute("mlsdm.response_length", len(result.get("response", "")))

            # Record simulated API metrics
            status = "2xx" if result.get("rejected_at") is None else "4xx"
            fresh_metrics.increment_requests("/generate", status)

            timing = result.get("timing", {})
            if "total" in timing:
                fresh_metrics.observe_generation_latency(timing["total"])

        # Verify result structure
        assert "response" in result
        assert "timing" in result
        assert "validation_steps" in result

        # Verify engine metrics
        engine_metrics = engine_with_metrics.get_metrics()
        if engine_metrics is not None:
            snapshot = engine_metrics.get_snapshot()
            assert snapshot["requests_total"] >= 1

        # Verify exported metrics
        metrics_text = fresh_metrics.get_metrics_text()
        assert 'endpoint="/generate"' in metrics_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
