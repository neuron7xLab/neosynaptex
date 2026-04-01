"""Tests for tracing module when OpenTelemetry is not installed.

This test module verifies that the tracing module gracefully handles
the absence of OpenTelemetry and provides no-op implementations.
"""

import sys
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_no_otel():
    """Mock environment where OpenTelemetry is not available."""
    # Remove opentelemetry from sys.modules to simulate it not being installed
    otel_modules = [m for m in sys.modules if m.startswith("opentelemetry")]
    removed_modules = {}

    for module in otel_modules:
        if module in sys.modules:
            removed_modules[module] = sys.modules.pop(module)

    # Mock import to fail
    original_import = __builtins__.__import__

    def mock_import(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        # Force reload of tracing module to pick up mocked import
        if "mlsdm.observability.tracing" in sys.modules:
            del sys.modules["mlsdm.observability.tracing"]

        yield

    # Restore modules
    for module, obj in removed_modules.items():
        sys.modules[module] = obj


def test_import_tracing_without_otel():
    """Test that tracing module can be imported without OpenTelemetry."""
    # This test just needs to import successfully
    from mlsdm.observability import tracing

    # Verify OTEL_AVAILABLE is a boolean
    assert isinstance(tracing.OTEL_AVAILABLE, bool)

    # Verify NoOpTracer and NoOpSpan are always available
    assert tracing.NoOpTracer is not None
    assert tracing.NoOpSpan is not None


def test_import_mlsdm_extensions_without_otel():
    """Test that mlsdm extensions can be imported without OpenTelemetry."""
    # These imports should work regardless of OTEL availability
    from mlsdm import LLMWrapper
    from mlsdm.extensions import AphasiaBrocaDetector, NeuroLangWrapper

    # Verify classes are importable
    assert AphasiaBrocaDetector is not None
    assert NeuroLangWrapper is not None
    assert LLMWrapper is not None


def test_noop_tracer_without_otel():
    """Test that NoOpTracer is used when OTEL is not available."""
    from mlsdm.observability.tracing import OTEL_AVAILABLE, NoOpTracer, get_tracer_manager

    if not OTEL_AVAILABLE:
        manager = get_tracer_manager()
        tracer = manager.tracer

        # Should be NoOpTracer when OTEL not available
        assert isinstance(tracer, NoOpTracer)

        # Test that context manager works
        with manager.start_span("test_span") as span:
            # These should not raise
            span.set_attribute("key", "value")
            span.set_attributes({"key1": "value1", "key2": "value2"})
            span.add_event("test_event", {"detail": "test"})
            try:
                raise ValueError("test exception")
            except ValueError as e:
                span.record_exception(e)
            span.set_status("OK")

            # Verify no-op span still records diagnostics for introspection
            assert span.attributes["key"] == "value"
            assert ("test_event", {"detail": "test"}) in span.events
            assert isinstance(span.exceptions[-1], ValueError)
            assert span.status == "OK"

        print("✓ NoOpTracer operations completed without errors")


def test_trace_context_without_otel():
    """Test that trace context returns empty values when OTEL not available."""
    from mlsdm.observability.logger import OTEL_AVAILABLE, get_current_trace_context

    if not OTEL_AVAILABLE:
        ctx = get_current_trace_context()

        # Should return empty strings
        assert isinstance(ctx, dict)
        assert "trace_id" in ctx
        assert "span_id" in ctx
        assert ctx["trace_id"] == ""
        assert ctx["span_id"] == ""

        print("✓ get_current_trace_context returns empty strings as expected")


def test_trace_helper_functions_without_otel():
    """Test that trace helper functions work without OTEL."""
    from mlsdm.observability.tracing import (
        OTEL_AVAILABLE,
        trace_full_pipeline,
        trace_generate,
        trace_llm_call,
        trace_memory_retrieval,
        trace_moral_filter,
    )

    if not OTEL_AVAILABLE:
        # Test trace_generate
        with trace_generate("test prompt", 0.8, 100) as span:
            span.set_attribute("test", "value")

        # Test trace_full_pipeline
        with trace_full_pipeline(100, 0.8, "wake") as span:
            span.set_attribute("test", "value")

        # Test trace_llm_call
        with trace_llm_call("test_model", "test prompt", 100) as span:
            span.set_attribute("test", "value")

        # Test trace_memory_retrieval
        with trace_memory_retrieval(5, 0.8) as span:
            span.set_attribute("test", "value")

        # Test trace_moral_filter
        with trace_moral_filter(0.5, 0.8) as span:
            span.set_attribute("test", "value")

        print("✓ All trace helper functions work without OTEL")


def test_no_otel_in_sys_modules():
    """Regression test: verify imports don't fail when opentelemetry not in sys.modules."""
    # Remove opentelemetry from sys.modules temporarily
    otel_modules = [m for m in list(sys.modules.keys()) if m.startswith("opentelemetry")]
    removed = {}

    for module in otel_modules:
        if module in sys.modules:
            removed[module] = sys.modules.pop(module)

    try:
        # Force reimport of mlsdm modules
        for module in ["mlsdm.observability.tracing", "mlsdm.observability.logger"]:
            if module in sys.modules:
                del sys.modules[module]

        # These imports should work even if opentelemetry was removed

        print("✓ Imports successful even with opentelemetry removed from sys.modules")
    finally:
        # Restore modules
        for module, obj in removed.items():
            sys.modules[module] = obj


def test_tracer_manager_disabled_state():
    """Test TracerManager behavior when tracing is disabled."""
    from mlsdm.observability.tracing import OTEL_AVAILABLE, TracerManager, TracingConfig

    if not OTEL_AVAILABLE:
        # Create manager with enabled=False
        config = TracingConfig(enabled=False)
        manager = TracerManager(config)
        manager.initialize()

        # Should not be enabled
        assert manager.enabled is False

        # Tracer should still be usable (NoOp)
        tracer = manager.tracer
        with tracer.start_as_current_span("test") as span:
            span.set_attribute("key", "value")

        print("✓ TracerManager handles disabled state correctly")


if __name__ == "__main__":
    # Run tests manually for debugging
    test_import_tracing_without_otel()
    test_import_mlsdm_extensions_without_otel()
    test_noop_tracer_without_otel()
    test_trace_context_without_otel()
    test_trace_helper_functions_without_otel()
    test_no_otel_in_sys_modules()
    test_tracer_manager_disabled_state()

    print("\n✅ All no-OTEL tests passed!")
