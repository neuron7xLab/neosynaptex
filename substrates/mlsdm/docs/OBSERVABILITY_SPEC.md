# MLSDM Observability Specification

This document defines the **minimal observability schema** for the MLSDM core pipeline, ensuring incidents and system behavior are transparently observable without excessive overhead.

## Overview

The observability layer provides three pillars:
1. **Distributed Tracing** - OpenTelemetry spans for request path visibility
2. **Prometheus Metrics** - Counters, gauges, and histograms for monitoring
3. **Structured Logging** - JSON-formatted logs with correlation IDs

All observability is designed with **graceful fallback**: if OpenTelemetry or Prometheus is not available/configured, the system continues to function without errors.

---

## Tracing Schema

### Span Hierarchy

For each call to `LLMWrapper.generate()` or `NeuroCognitiveEngine.generate()`:

```
mlsdm.generate (root)
├── mlsdm.cognitive_controller.step
│   └── (event processing, memory update)
├── mlsdm.memory.query
│   └── (PELM + Synaptic retrieval)
├── mlsdm.moral_filter.evaluate
│   └── (moral threshold check)
└── mlsdm.aphasia.detect_repair (optional)
    └── (detection and repair if enabled)
```

### Engine-Level Spans

When using `NeuroCognitiveEngine.generate()`:

```
engine.generate (root)
├── engine.moral_precheck
├── engine.grammar_precheck
├── engine.llm_generation
│   ├── llm_wrapper.moral_filter
│   ├── llm_wrapper.memory_retrieval
│   ├── llm_wrapper.llm_call
│   └── llm_wrapper.memory_update
└── engine.post_moral_check
```

### Required Span Attributes

| Attribute | Type | Description | Required |
|-----------|------|-------------|----------|
| `mlsdm.phase` | string | Current cognitive phase (`wake` or `sleep`) | Yes |
| `mlsdm.stateless_mode` | bool | Whether running in degraded stateless mode | Yes |
| `mlsdm.moral_threshold` | float | Current moral threshold value | Yes |
| `mlsdm.accepted` | bool | Whether the request was accepted | Yes |
| `mlsdm.emergency_shutdown` | bool | Whether emergency shutdown was triggered | Yes |
| `mlsdm.aphasia_flagged` | bool | Whether aphasia was detected | When aphasia enabled |
| `mlsdm.prompt_length` | int | Length of input prompt (not content!) | Yes |
| `mlsdm.response_length` | int | Length of generated response | On success |
| `mlsdm.rejected_at` | string | Stage where rejection occurred | On rejection |
| `mlsdm.error_type` | string | Type of error that occurred | On error |

### Context Propagation

Trace context is automatically propagated:
- From API layer to engine
- From engine to LLM wrapper
- From LLM wrapper to memory systems

---

## Metrics Schema

### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_requests_total` | `status`, `emergency` | Total requests processed |
| `mlsdm_aphasia_events_total` | `mode` | Aphasia detection/repair events |
| `mlsdm_events_processed_total` | - | Total cognitive events processed |
| `mlsdm_events_rejected_total` | - | Total rejected events |
| `mlsdm_errors_total` | `error_type` | Errors by type |
| `mlsdm_moral_rejections_total` | `reason` | Moral rejections by reason |
| `mlsdm_emergency_shutdowns_total` | `reason` | Emergency shutdowns by reason |

### Histograms

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_request_latency_seconds` | `endpoint`, `phase` | End-to-end request latency |
| `mlsdm_processing_latency_milliseconds` | - | Event processing latency |
| `mlsdm_generation_latency_milliseconds` | `provider_id`, `variant` | LLM generation latency |
| `mlsdm_retrieval_latency_milliseconds` | - | Memory retrieval latency |

### Gauges

| Metric | Description |
|--------|-------------|
| `mlsdm_phase` | Current phase (wake=1, sleep=0) |
| `mlsdm_moral_threshold` | Current moral threshold |
| `mlsdm_memory_usage_bytes` | Total memory usage |
| `mlsdm_emergency_shutdown_active` | Shutdown active (1/0) |
| `mlsdm_stateless_mode` | Stateless mode active (1/0) |

---

## Helper Functions

### Recording Requests

```python
from mlsdm.observability import record_request

# Record successful request
record_request(status="ok", latency_sec=0.15)

# Record error with emergency shutdown
record_request(status="error", emergency=True, latency_sec=0.5)

# With custom endpoint and phase
record_request(status="ok", endpoint="/infer", phase="sleep", latency_sec=0.3)
```

### Recording Aphasia Events

```python
from mlsdm.observability import record_aphasia_event

# Record detection only
record_aphasia_event(mode="detect", severity=0.7)

# Record repair (call detect separately to avoid double-counting)
record_aphasia_event(mode="detect", severity=0.8)
record_aphasia_event(mode="repair", severity=0.8)
```

### Creating Spans

```python
from mlsdm.observability import span

# Simple span with auto-prefixed attributes
with span("mlsdm.generate", phase="wake", stateless_mode=False) as s:
    # Attributes become mlsdm.phase, mlsdm.stateless_mode
    s.set_attribute("mlsdm.accepted", True)
    # ... do work ...
```

---

## Graceful Fallback

All observability functions are designed to fail gracefully:

1. **Tracing Disabled** (`MLSDM_OTEL_ENABLED=false`)
   - `span()` and `TracerManager.start_span()` create no-op spans
   - Attribute calls succeed silently

2. **Metrics Failure**
   - `record_request()` and `record_aphasia_event()` catch all exceptions
   - No impact on main processing logic

3. **No External Services**
   - By default, no network exporters are configured
   - Console/none exporters for development
   - Zero external dependencies in hot path

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MLSDM_OTEL_ENABLED` | Enable/disable tracing | `false` |
| `MLSDM_OTEL_ENDPOINT` | OTLP endpoint URL | `http://localhost:4318` |
| `OTEL_SERVICE_NAME` | Service name | `mlsdm` |
| `OTEL_EXPORTER_TYPE` | Exporter type | `console` |
| `OTEL_TRACES_SAMPLER_ARG` | Sampling rate (0.0-1.0) | `1.0` |

### Exporter Types

- `none` - No export (spans still created internally)
- `console` - Print to stdout (development)
- `otlp` - OTLP protocol (production)
- `jaeger` - Jaeger backend

---

## Invariants

1. **No PII in observability** - Only metadata (lengths, scores, counts) is captured
2. **No blocking in hot path** - All metric/span operations are non-blocking
3. **Graceful degradation** - Observability failures never crash the system
4. **Low overhead** - Default configuration has minimal performance impact
5. **Thread-safe** - All observability operations are safe for concurrent use

---

## Implementation Checklist

This checklist tracks the implementation status of observability components as specified in PROD_GAPS.md.

### Metrics

| Metric | Required | Status | Location |
|--------|----------|--------|----------|
| `mlsdm_http_requests_total{method,endpoint,status}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_http_request_latency_seconds_bucket{endpoint}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_http_requests_in_flight` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_cognitive_cycle_duration_seconds` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_memory_items_total{level}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_memory_evictions_total{reason}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_emergency_shutdown_total{reason}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_auto_recovery_total{result}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_moral_filter_decisions_total{decision}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_moral_filter_violation_score` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_llm_request_latency_seconds_bucket{model}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_llm_failures_total{reason}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_llm_tokens_total{direction}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_bulkhead_active_requests` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_bulkhead_queue_depth` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_timeout_total{endpoint}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |
| `mlsdm_priority_queue_depth{priority}` | Yes | ✅ Implemented | `src/mlsdm/observability/metrics.py` |

### Structured Logs

| Field | Required | Status | Location |
|-------|----------|--------|----------|
| `timestamp` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `level` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `service` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `component` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `trace_id` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `span_id` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `correlation_id` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `request_id` | Yes | ✅ Implemented | `src/mlsdm/api/middleware.py` |
| `event` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |
| `message` | Yes | ✅ Implemented | `src/mlsdm/observability/logger.py` |

### Tracing

| Span | Required | Status | Location |
|------|----------|--------|----------|
| `api.generate` | Yes | ✅ Implemented | `src/mlsdm/api/app.py` |
| `api.infer` | Yes | ✅ Implemented | `src/mlsdm/api/app.py` |
| `engine.generate` | Yes | ✅ Implemented | `src/mlsdm/engine/neuro_cognitive_engine.py` |
| `llm_wrapper.*` | Yes | ✅ Implemented | `src/mlsdm/observability/tracing.py` |

### Dashboards

| Dashboard | Required | Status | Location |
|-----------|----------|--------|----------|
| Core Observability | Yes | ✅ Implemented | `deploy/grafana/mlsdm_observability_dashboard.json` |
| SLO Dashboard | Yes | ✅ Implemented | `deploy/grafana/mlsdm_slo_dashboard.json` |

### Alerts

| Alert | Required | Status | Location |
|-------|----------|--------|----------|
| HighErrorRate | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |
| HighLatency | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |
| EmergencyShutdownSpike | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |
| LLMTimeoutSpike | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |
| BulkheadSaturation | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |
| MoralFilterBlockSpike | Yes | ✅ Implemented | `deploy/k8s/alerts/mlsdm-alerts.yaml` |

### Tests

| Test Category | Required | Status | Location |
|---------------|----------|--------|----------|
| Metrics export | Yes | ✅ Implemented | `tests/observability/test_metrics_basic.py` |
| Tracing spans | Yes | ✅ Implemented | `tests/observability/test_tracing_integration.py` |
| Log structure | Yes | ✅ Implemented | `tests/observability/test_trace_context_logging.py` |
| Integration | Yes | ✅ Implemented | `tests/observability/test_metrics_and_tracing_integration.py` |

---

## See Also

- [OBSERVABILITY_GUIDE.md](./OBSERVABILITY_GUIDE.md) - Operational guide with SLO recommendations
- [docs/APHASIA_OBSERVABILITY.md](./docs/APHASIA_OBSERVABILITY.md) - Aphasia-specific telemetry
- [docs/observability/GRAFANA_DASHBOARDS.md](./docs/observability/GRAFANA_DASHBOARDS.md) - Dashboard setup
