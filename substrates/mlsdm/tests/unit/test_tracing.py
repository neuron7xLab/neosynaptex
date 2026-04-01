"""Tests for OpenTelemetry distributed tracing module.

Tests the tracing functionality including:
- TracerManager singleton behavior
- Span creation and management
- Decorators for function tracing
- MLSDM-specific tracing utilities
"""

from __future__ import annotations

import asyncio

import pytest

from mlsdm.observability.tracing import (
    TracerManager,
    TracingConfig,
    add_span_attributes,
    get_tracer,
    get_tracer_manager,
    initialize_tracing,
    shutdown_tracing,
    trace_generate,
    trace_moral_filter,
    trace_process_event,
    traced,
    traced_async,
)


class TestTracingConfig:
    """Tests for TracingConfig class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        # Use explicit empty env to ensure defaults
        config = TracingConfig(_env={})
        assert config.service_name == "mlsdm"
        assert config.enabled is True
        assert config.exporter_type == "console"
        assert config.sample_rate == 1.0

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = TracingConfig(
            service_name="test-service",
            enabled=False,
            exporter_type="otlp",
            sample_rate=0.5,
            _env={},
        )
        assert config.service_name == "test-service"
        assert config.enabled is False
        assert config.exporter_type == "otlp"
        assert config.sample_rate == 0.5

    def test_config_from_env(self) -> None:
        """Test configuration from environment variables."""
        # Use explicit env dict instead of monkeypatch
        test_env = {
            "OTEL_SERVICE_NAME": "env-service",
            "OTEL_SDK_DISABLED": "true",
            "OTEL_EXPORTER_TYPE": "jaeger",
            "OTEL_TRACES_SAMPLER_ARG": "0.25",
        }
        config = TracingConfig(_env=test_env)
        assert config.service_name == "env-service"
        assert config.enabled is False
        assert config.exporter_type == "jaeger"
        assert config.sample_rate == 0.25

    def test_config_isolation_regression(self) -> None:
        """Regression test: ensure config reads don't leak between instances.

        This test verifies that creating multiple TracingConfig instances
        with different settings doesn't cause state pollution.
        """
        # First config with explicit disabled
        config1 = TracingConfig(enabled=False, _env={})
        assert config1.enabled is False

        # Second config should get defaults (enabled=True)
        config2 = TracingConfig(_env={})
        assert config2.enabled is True

        # Third config with env override
        config3 = TracingConfig(_env={"OTEL_SDK_DISABLED": "true"})
        assert config3.enabled is False

        # Fourth config should still get defaults
        config4 = TracingConfig(_env={})
        assert config4.enabled is True


class TestTracerManager:
    """Tests for TracerManager class."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        TracerManager.reset_instance()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        TracerManager.reset_instance()

    def test_singleton_pattern(self) -> None:
        """Test that TracerManager follows singleton pattern."""
        manager1 = TracerManager.get_instance()
        manager2 = TracerManager.get_instance()
        assert manager1 is manager2

    def test_initialization(self) -> None:
        """Test tracer initialization."""
        config = TracingConfig(exporter_type="none")
        manager = TracerManager.get_instance(config)
        manager.initialize()
        # With exporter_type="none", initialization still succeeds but with no exporter
        # The tracer is still available
        assert manager.tracer is not None

    def test_initialization_with_console_exporter(self) -> None:
        """Test initialization with console exporter."""
        config = TracingConfig(exporter_type="console")
        manager = TracerManager.get_instance(config)
        manager.initialize()
        assert manager.tracer is not None

    def test_shutdown(self) -> None:
        """Test tracer shutdown."""
        config = TracingConfig(exporter_type="console")
        manager = TracerManager.get_instance(config)
        manager.initialize()
        manager.shutdown()
        assert manager._initialized is False

    def test_start_span_context_manager(self) -> None:
        """Test span creation via context manager."""
        manager = TracerManager.get_instance()
        manager.initialize()

        with manager.start_span("test_span") as span:
            assert span is not None
            span.set_attribute("test_key", "test_value")


class TestGlobalFunctions:
    """Tests for global accessor functions."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        TracerManager.reset_instance()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        shutdown_tracing()

    def test_get_tracer_manager(self) -> None:
        """Test getting tracer manager instance."""
        manager = get_tracer_manager()
        assert manager is not None
        assert isinstance(manager, TracerManager)

    def test_get_tracer(self) -> None:
        """Test getting tracer instance."""
        tracer = get_tracer()
        assert tracer is not None

    def test_initialize_tracing(self) -> None:
        """Test tracing initialization."""
        config = TracingConfig(exporter_type="console")
        initialize_tracing(config)
        manager = get_tracer_manager()
        assert manager.tracer is not None

    def test_shutdown_tracing(self) -> None:
        """Test tracing shutdown."""
        initialize_tracing()
        shutdown_tracing()
        # After shutdown, getting manager creates a new instance
        new_manager = get_tracer_manager()
        assert new_manager._initialized is False


class TestDecorators:
    """Tests for tracing decorators."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        TracerManager.reset_instance()
        initialize_tracing(TracingConfig(exporter_type="console"))

    def teardown_method(self) -> None:
        """Clean up after each test."""
        shutdown_tracing()

    def test_traced_decorator(self) -> None:
        """Test synchronous function tracing decorator."""

        @traced("test_function")
        def sample_function(x: int, y: int) -> int:
            return x + y

        result = sample_function(2, 3)
        assert result == 5

    def test_traced_decorator_with_args(self) -> None:
        """Test tracing decorator with argument recording."""

        @traced("test_with_args", record_args=True)
        def sample_function(x: int, y: int) -> int:
            return x + y

        result = sample_function(2, 3)
        assert result == 5

    def test_traced_decorator_with_exception(self) -> None:
        """Test tracing decorator with exception handling."""

        @traced("test_exception")
        def failing_function() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    @pytest.mark.asyncio
    async def test_traced_async_decorator(self) -> None:
        """Test async function tracing decorator."""

        @traced_async("async_function")
        async def async_sample(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        result = await async_sample(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_traced_async_with_exception(self) -> None:
        """Test async tracing decorator with exception."""

        @traced_async("async_exception")
        async def async_failing() -> None:
            await asyncio.sleep(0.01)
            raise RuntimeError("Async error")

        with pytest.raises(RuntimeError, match="Async error"):
            await async_failing()


class TestMLSDMTracingUtilities:
    """Tests for MLSDM-specific tracing utilities."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        TracerManager.reset_instance()
        initialize_tracing(TracingConfig(exporter_type="console"))

    def teardown_method(self) -> None:
        """Clean up after each test."""
        shutdown_tracing()

    def test_trace_generate(self) -> None:
        """Test trace_generate context manager."""
        with trace_generate("test prompt", 0.8, 256) as span:
            assert span is not None
            # Can set additional attributes
            span.set_attribute("custom_attr", "value")

    def test_trace_process_event(self) -> None:
        """Test trace_process_event context manager."""
        with trace_process_event("cognitive", 0.7) as span:
            assert span is not None

    def test_trace_moral_filter(self) -> None:
        """Test trace_moral_filter context manager."""
        with trace_moral_filter(0.5, score=0.8) as span:
            assert span is not None

    def test_add_span_attributes(self) -> None:
        """Test adding attributes to a span."""
        manager = get_tracer_manager()

        with manager.start_span("test") as span:
            add_span_attributes(
                span,
                string_attr="value",
                int_attr=42,
                float_attr=3.14,
                bool_attr=True,
                list_attr=[1, 2, 3],
                none_attr=None,  # Should be skipped
            )

    def test_add_span_attributes_with_complex_types(self) -> None:
        """Test attribute conversion for complex types."""
        manager = get_tracer_manager()

        with manager.start_span("test") as span:
            add_span_attributes(
                span,
                dict_attr={"key": "value"},
                set_attr={1, 2, 3},
            )


class TestTracingDisabled:
    """Tests for behavior when tracing is disabled."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        TracerManager.reset_instance()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        shutdown_tracing()

    def test_disabled_tracing(self) -> None:
        """Test that operations work when tracing is disabled."""
        config = TracingConfig(enabled=False)
        initialize_tracing(config)

        # Operations should still work without error
        tracer = get_tracer()
        assert tracer is not None

        @traced("disabled_trace")
        def sample_fn() -> str:
            return "success"

        result = sample_fn()
        assert result == "success"
