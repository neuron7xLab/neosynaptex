"""Observability module for MLSDM Governed Cognitive Memory.

This module provides structured logging and monitoring capabilities
for the cognitive architecture system, including:
- Trace context correlation (trace_id/span_id in logs)
- OpenTelemetry distributed tracing
- Prometheus metrics
- Structured JSON logging
- Memory subsystem telemetry (PELM + Synaptic)
"""

from .aphasia_logging import (
    LOGGER_NAME as APHASIA_LOGGER_NAME,
)
from .aphasia_logging import (
    AphasiaLogEvent,
    log_aphasia_event,
)
from .aphasia_logging import (
    get_logger as get_aphasia_logger,
)
from .aphasia_metrics import (
    AphasiaMetricsExporter,
    get_aphasia_metrics_exporter,
    reset_aphasia_metrics_exporter,
)
from .logger import (
    EventType,
    JSONFormatter,
    ObservabilityLogger,
    RejectionReason,
    TraceContextFilter,
    get_current_trace_context,
    get_observability_logger,
    payload_scrubber,
    scrub_for_log,
)
from .memory_telemetry import (
    LOGGER_NAME as MEMORY_LOGGER_NAME,
)
from .memory_telemetry import (
    MemoryEventType,
    MemoryMetricsExporter,
    MemoryOperationTimer,
    get_memory_logger,
    get_memory_metrics_exporter,
    log_pelm_capacity_warning,
    log_pelm_corruption,
    log_pelm_retrieve,
    log_pelm_store,
    log_synaptic_update,
    record_pelm_corruption,
    record_pelm_retrieve,
    record_pelm_store,
    record_synaptic_update,
    reset_memory_metrics_exporter,
    trace_pelm_retrieve,
    trace_pelm_store,
    trace_synaptic_update,
)
from .metrics import (
    MetricsExporter,
    PhaseType,
    get_metrics_exporter,
    record_aphasia_event,
    record_request,
)
from .tracing import (
    TracerManager,
    TracingConfig,
    add_span_attributes,
    get_tracer,
    get_tracer_manager,
    initialize_tracing,
    shutdown_tracing,
    span,
    trace_aphasia_detection,
    trace_aphasia_repair,
    trace_emergency_shutdown,
    trace_full_pipeline,
    trace_generate,
    trace_llm_call,
    trace_memory_retrieval,
    trace_moral_filter,
    trace_phase_transition,
    trace_process_event,
    trace_request,
    trace_speech_governance,
    traced,
    traced_async,
)

__all__ = [
    # Aphasia-specific observability
    "APHASIA_LOGGER_NAME",
    "AphasiaLogEvent",
    "AphasiaMetricsExporter",
    # Memory-specific observability
    "MEMORY_LOGGER_NAME",
    "MemoryEventType",
    "MemoryMetricsExporter",
    "MemoryOperationTimer",
    "get_memory_logger",
    "get_memory_metrics_exporter",
    "log_pelm_capacity_warning",
    "log_pelm_corruption",
    "log_pelm_retrieve",
    "log_pelm_store",
    "log_synaptic_update",
    "record_pelm_corruption",
    "record_pelm_retrieve",
    "record_pelm_store",
    "record_synaptic_update",
    "reset_memory_metrics_exporter",
    "trace_pelm_retrieve",
    "trace_pelm_store",
    "trace_synaptic_update",
    # General observability
    "EventType",
    "JSONFormatter",
    "MetricsExporter",
    "ObservabilityLogger",
    "PhaseType",
    "RejectionReason",
    "TraceContextFilter",
    "get_aphasia_logger",
    "get_aphasia_metrics_exporter",
    "get_current_trace_context",
    "get_metrics_exporter",
    "get_observability_logger",
    "log_aphasia_event",
    "payload_scrubber",
    "reset_aphasia_metrics_exporter",
    "scrub_for_log",
    # Metrics helpers
    "record_request",
    "record_aphasia_event",
    # Tracing
    "TracerManager",
    "TracingConfig",
    "add_span_attributes",
    "get_tracer",
    "get_tracer_manager",
    "initialize_tracing",
    "shutdown_tracing",
    "span",
    "traced",
    "traced_async",
    "trace_generate",
    "trace_process_event",
    "trace_memory_retrieval",
    "trace_moral_filter",
    "trace_aphasia_detection",
    "trace_aphasia_repair",
    "trace_emergency_shutdown",
    "trace_phase_transition",
    "trace_full_pipeline",
    "trace_llm_call",
    "trace_request",
    "trace_speech_governance",
]
