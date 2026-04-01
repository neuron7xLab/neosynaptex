# MLSDM Observability Guide

This guide explains how to set up and use observability features in MLSDM for monitoring, troubleshooting, and maintaining SLO compliance.

## Overview

MLSDM provides comprehensive observability through three pillars:

1. **Structured Logging** - JSON-formatted logs with correlation IDs and mandatory fields
2. **Prometheus Metrics** - Counters, gauges, and histograms for monitoring
3. **OpenTelemetry Tracing** - Distributed tracing for request path visibility

## Quick Start

### Enable Prometheus Metrics

Metrics are exposed at `/health/metrics` endpoint by default:

```bash
# Start the API server
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000

# Scrape metrics
curl http://localhost:8000/health/metrics
```

### Enable OpenTelemetry Tracing

Set environment variables to enable tracing:

```bash
# Enable tracing with console exporter (for debugging)
export MLSDM_OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=console

# Or use OTLP exporter for production
export MLSDM_OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=otlp
export MLSDM_OTEL_ENDPOINT=http://jaeger:4318
```

### Import Grafana Dashboard

1. Open Grafana and navigate to Dashboards → Import
2. Upload `deploy/grafana/mlsdm_observability_dashboard.json`
3. Select your Prometheus data source
4. Click Import

## Health Endpoints for DevOps

MLSDM provides health endpoints for Kubernetes liveness and readiness probes, as well as detailed system diagnostics.

### Endpoint Summary

| Endpoint | Purpose | Response Code |
|----------|---------|---------------|
| `GET /health` | Simple health check | 200 always |
| `GET /health/live` | **Liveness probe** - process alive | 200 always |
| `GET /health/ready` | **Readiness probe** - can accept traffic | 200 or 503 |
| `GET /health/readiness` | Legacy alias for `/health/ready` | 200 or 503 |
| `GET /health/detailed` | Full system diagnostics | 200 or 503 |
| `GET /health/metrics` | Prometheus metrics | 200 |

### Liveness Probe: `/health/live`

Use this endpoint for Kubernetes liveness probes. It returns 200 if the process is alive - no dependency checks are performed.

```bash
curl http://localhost:8000/health/live
```

Response:
```json
{
  "status": "alive",
  "timestamp": 1234567890.123
}
```

### Readiness Probe: `/health/ready`

Use this endpoint for Kubernetes readiness probes. It performs comprehensive health checks on critical components.

**Components Checked:**
- **cognitive_controller**: Not in `emergency_shutdown` state
- **memory_bounds**: Global memory usage within configured limit (default: 1.4 GB)
- **moral_filter**: Initialized without critical errors
- **system_memory**: System RAM usage < 95%
- **system_cpu**: System CPU usage < 98%

```bash
curl http://localhost:8000/health/ready
```

Response (ready):
```json
{
  "ready": true,
  "status": "ready",
  "timestamp": 1234567890.123,
  "components": {
    "cognitive_controller": {"healthy": true, "details": null},
    "memory_bounds": {"healthy": true, "details": "usage: 45.2%"},
    "moral_filter": {"healthy": true, "details": "threshold=0.50"},
    "system_memory": {"healthy": true, "details": "usage: 68.5%"},
    "system_cpu": {"healthy": true, "details": "usage: 35.2%"}
  },
  "details": null,
  "checks": {
    "cognitive_controller": true,
    "memory_bounds": true,
    "moral_filter": true,
    "memory_available": true,
    "cpu_available": true
  }
}
```

Response (not ready - emergency shutdown):
```json
{
  "ready": false,
  "status": "not_ready",
  "timestamp": 1234567890.123,
  "components": {
    "cognitive_controller": {"healthy": false, "details": "emergency_shutdown_active"},
    ...
  },
  "details": {
    "unhealthy_components": ["cognitive_controller"]
  },
  "checks": {...}
}
```

### Kubernetes Configuration Example

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: mlsdm-api
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 3
```

## Minimal Observability Schema for Core Pipeline

This section defines the **minimal** observability requirements for the core MLSDM pipeline (`generate()` → engine → controller → memory). This schema ensures incidents and system behavior are observable without excessive overhead.

### Tracing Schema

For each call to `LLMWrapper.generate()` or `NeuroCognitiveEngine.generate()`:

**Root Span:**
- `mlsdm.generate` - Root span for the entire request

**Child Spans (nested under root):**
- `mlsdm.cognitive_controller.step` - Processing each event/step
- `mlsdm.memory.query` - PELM + Synaptic memory retrieval
- `mlsdm.moral_filter.evaluate` - Moral filter evaluation
- `mlsdm.aphasia.detect_repair` - Aphasia detection and repair (when enabled)

**Required Span Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `mlsdm.phase` | string | Current cognitive phase (`wake` or `sleep`) |
| `mlsdm.stateless_mode` | bool | Whether running in degraded stateless mode |
| `mlsdm.moral_threshold` | float | Current moral threshold value |
| `mlsdm.accepted` | bool | Whether the request was accepted |
| `mlsdm.emergency_shutdown` | bool | Whether emergency shutdown was triggered |
| `mlsdm.aphasia_flagged` | bool | Whether aphasia was detected |

### Metrics Schema

**Counters:**

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_requests_total` | `status=ok\|error`, `emergency=true\|false` | Total requests processed |
| `mlsdm_aphasia_events_total` | `mode=detect\|repair` | Aphasia detection/repair events |

**Histograms:**

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_request_latency_seconds` | `endpoint`, `phase` | Request latency distribution |

### Helper Functions

Simple helper functions are provided for consistent metric recording:

```python
from mlsdm.observability import record_request, record_aphasia_event, span

# Record a successful request
record_request(status="ok", latency_sec=0.15)

# Record an error with emergency shutdown
record_request(status="error", emergency=True, latency_sec=0.5)

# Record aphasia detection
record_aphasia_event(mode="detect", severity=0.7)

# Create a span with attributes
with span("mlsdm.generate", phase="wake", stateless_mode=False):
    # ... do work ...
    pass
```

### Graceful Fallback

All observability functions are designed to fail gracefully:

- If tracing is disabled (`MLSDM_OTEL_ENABLED=false`), span operations become no-ops
- If metrics fail for any reason, `record_request()` and `record_aphasia_event()` silently continue
- No network calls or blocking operations in the hot path

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MLSDM_OTEL_ENABLED` | Enable/disable tracing | `false` |
| `MLSDM_OTEL_ENDPOINT` | OTLP endpoint URL | `http://localhost:4318` |
| `OTEL_SERVICE_NAME` | Service name for traces | `mlsdm` |
| `OTEL_EXPORTER_TYPE` | Exporter type: `console`, `otlp`, `jaeger`, `none` | `console` |
| `OTEL_TRACES_SAMPLER_ARG` | Sampling rate (0.0-1.0) | `1.0` |

### Prometheus Scrape Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mlsdm'
    scrape_interval: 15s
    static_configs:
      - targets: ['mlsdm-api:8000']
    metrics_path: '/health/metrics'
```

## Key Metrics

### Request Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_requests_total` | Counter | Total requests | `endpoint`, `status` |
| `mlsdm_requests_inflight` | Gauge | **NEW** Concurrent requests in progress | - |
| `mlsdm_request_latency_seconds` | Histogram | Request latency | `endpoint`, `phase` |
| `mlsdm_generate_latency_seconds` | Histogram | **NEW** End-to-end generate() latency (seconds) | - |
| `mlsdm_events_processed_total` | Counter | Events processed | - |
| `mlsdm_events_rejected_total` | Counter | Events rejected | - |
| `mlsdm_generation_latency_milliseconds` | Histogram | End-to-end generation latency | - |
| `mlsdm_llm_call_latency_milliseconds` | Histogram | Inner LLM API call latency | - |
| `mlsdm_processing_latency_milliseconds` | Histogram | Event processing latency | - |
| `mlsdm_retrieval_latency_milliseconds` | Histogram | Memory retrieval latency | - |

### Moral Governance Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_moral_rejections_total` | Counter | Moral rejections | `reason` |
| `mlsdm_moral_threshold` | Gauge | Current threshold | - |

### Aphasia Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_aphasia_detected_total` | Counter | Aphasia detections | `severity_bucket` |
| `mlsdm_aphasia_repaired_total` | Counter | Successful repairs | - |
| `mlsdm_aphasia_events_total` | Counter | All aphasia events | `mode`, `is_aphasic`, `repair_applied` |

### Security Mode Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_secure_mode_requests_total` | Counter | Requests in secure mode | - |

### Emergency Shutdown Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_cognitive_emergency_total` | Counter | **NEW** Total cognitive emergency events | - |
| `mlsdm_emergency_shutdowns_total` | Counter | Shutdown events | `reason` |
| `mlsdm_emergency_shutdown_active` | Gauge | Shutdown active (1/0) | - |

### Cognitive State Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `mlsdm_phase` | Gauge | Current phase (wake=1, sleep=0) | - |
| `mlsdm_memory_usage_bytes` | Gauge | Memory usage in bytes | - |
| `mlsdm_memory_l1_norm` | Gauge | L1 memory layer norm | - |
| `mlsdm_memory_l2_norm` | Gauge | L2 memory layer norm | - |
| `mlsdm_memory_l3_norm` | Gauge | L3 memory layer norm | - |
| `mlsdm_stateless_mode` | Gauge | Stateless/degraded mode (1/0) | - |
| `mlsdm_phase_events_total` | Counter | Events per phase | `phase` |

## SLO Recommendations

Based on MLSDM architecture and production patterns, we recommend the following SLOs:

### Availability SLO: 99.5%

```promql
# Availability calculation
(1 - sum(rate(mlsdm_requests_total{status=~"5.."}[5m]))
   / sum(rate(mlsdm_requests_total[5m]))) * 100
```

### Latency SLO: P95 < 500ms

```promql
# P95 latency
histogram_quantile(0.95,
  sum(rate(mlsdm_request_latency_seconds_bucket[5m])) by (le)
)
```

### Error Budget: 0.5% of requests

```promql
# Error budget burn rate (per hour)
sum(increase(mlsdm_errors_total[1h]))
/ (30 * 24 * 0.005 * sum(increase(mlsdm_requests_total[1h])))
```

### Moral Rejection Rate: < 5%

```promql
# Moral rejection rate
sum(rate(mlsdm_moral_rejections_total[5m]))
/ sum(rate(mlsdm_requests_total[5m])) * 100
```

### Emergency Shutdown Frequency: < 1 per day

```promql
# Shutdowns per day
sum(increase(mlsdm_emergency_shutdowns_total[24h]))
```

## Tracing Structure

Each request generates a span tree with the following structure:

```
api.generate (SERVER)
├── engine.generate (INTERNAL)
│   ├── engine.moral_precheck (INTERNAL)
│   ├── engine.grammar_precheck (INTERNAL)
│   ├── engine.llm_generation (INTERNAL)
│   │   ├── llm_wrapper.moral_filter (INTERNAL)    ← Inner moral validation
│   │   ├── llm_wrapper.memory_retrieval (INTERNAL) ← Context retrieval from PELM
│   │   ├── llm_wrapper.llm_call (INTERNAL)        ← Raw LLM API call
│   │   └── llm_wrapper.memory_update (INTERNAL)   ← Memory entanglement
│   └── engine.post_moral_check (INTERNAL)
```

For `/infer` endpoint with aphasia mode enabled:

```
api.infer (SERVER)
├── engine.generate (INTERNAL)
│   ├── engine.moral_precheck (INTERNAL)
│   ├── engine.llm_generation (INTERNAL)
│   │   ├── llm_wrapper.moral_filter (INTERNAL)
│   │   ├── llm_wrapper.memory_retrieval (INTERNAL)
│   │   ├── llm_wrapper.llm_call (INTERNAL)
│   │   │   └── mlsdm.speech_governance (INTERNAL)
│   │   │       ├── mlsdm.aphasia_detection (INTERNAL)
│   │   │       └── mlsdm.aphasia_repair (INTERNAL)
│   │   └── llm_wrapper.memory_update (INTERNAL)
│   └── engine.post_moral_check (INTERNAL)
```

### Key Span Attributes

| Attribute | Description |
|-----------|-------------|
| `mlsdm.request_id` | Unique request identifier |
| `mlsdm.phase` | Cognitive phase (wake/sleep) |
| `mlsdm.moral_value` | Moral threshold used |
| `mlsdm.moral_threshold` | Current moral threshold |
| `mlsdm.moral.accepted` | Whether moral check passed |
| `mlsdm.accepted` | Whether request was accepted |
| `mlsdm.rejected_at` | Stage where rejection occurred |
| `mlsdm.prompt_length` | Length of prompt (not content!) |
| `mlsdm.response_length` | Length of response |
| `mlsdm.latency_ms` | Processing latency |
| `mlsdm.context_items_retrieved` | Number of memory items retrieved |
| `mlsdm.stateless_mode` | Whether running in degraded stateless mode |
| `mlsdm.secure_mode` | Whether secure mode is enabled |
| `mlsdm.aphasia_mode` | Whether aphasia detection is enabled |
| `mlsdm.rag_enabled` | Whether RAG retrieval is enabled |

## Logging Structure

All logs are JSON-formatted with mandatory fields:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "event_type": "request_completed",
  "correlation_id": "abc-123",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331",
  "metrics": {
    "request_id": "abc-123",
    "phase": "wake",
    "step_counter": 42,
    "accepted": true,
    "reason": "normal",
    "moral_score_before": 0.75,
    "moral_score_after": 0.80,
    "latency_ms": 150.5
  }
}
```

### Trace Context Correlation

When OpenTelemetry tracing is enabled, all logs automatically include `trace_id` and `span_id` fields from the current span context. This enables correlation between logs and distributed traces in your observability backend (e.g., Jaeger, Grafana Tempo).

**How it works:**
- The `TraceContextFilter` is automatically added to `ObservabilityLogger`
- Each log record is enriched with the current `trace_id` (32 hex chars) and `span_id` (16 hex chars)
- If no span is active, these fields are omitted from the log output

**Example: Correlating logs with traces:**

```python
from mlsdm.observability import span, get_observability_logger

logger = get_observability_logger()

with span("mlsdm.generate", phase="wake"):
    # This log will include trace_id and span_id
    logger.info(EventType.REQUEST_STARTED, "Processing request")
```

**Querying correlated logs in Grafana Loki:**

```logql
{job="mlsdm"} | json | trace_id="0af7651916cd43dd8448eb211c80319c"
```

**Disabling trace context injection:**

```python
logger = ObservabilityLogger(
    enable_trace_context=False  # Disable trace context injection
)
```

### Privacy Invariant

**CRITICAL**: Raw user input and LLM responses are NEVER logged. Only metadata (lengths, scores, counts) is captured. The `payload_scrubber` function masks any text content before logging.

## Emergency Shutdown Logs

When an emergency shutdown is triggered, a structured log entry is created with full context for incident response.

### Log Format

Emergency shutdown events are logged at ERROR level with `event_type` set to one of:
- `emergency_shutdown` - General emergency
- `emergency_shutdown_memory` - Memory limit exceeded
- `emergency_shutdown_timeout` - Processing timeout

### Log Fields

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "ERROR",
  "event_type": "emergency_shutdown",
  "correlation_id": "abc-123",
  "message": "EMERGENCY SHUTDOWN triggered: memory_limit",
  "metrics": {
    "event": "emergency_shutdown",
    "reason": "memory_limit",
    "phase": "wake",
    "memory_used": 1500000000,
    "is_stateless": false,
    "aphasia_flags": ["repetition"],
    "step_counter": 1542,
    "moral_threshold": 0.75
  }
}
```

### Reason Codes

| Reason | Description | Common Cause |
|--------|-------------|--------------|
| `memory_limit` | Global memory bound exceeded (1.4 GB) | High traffic, memory leak |
| `memory_exceeded` | Process memory threshold exceeded | Same as above |
| `processing_timeout` | Event processing took too long | Slow LLM, resource contention |
| `config_error` | Configuration validation failed | Invalid config, missing keys |
| `safety_violation` | Safety constraint violated | Moral filter failure |

### How to Respond

1. **Immediate**: Check `/health/ready` - will return 503 during emergency
2. **Diagnose**: Look for `reason` field in logs to identify root cause
3. **Memory Issues**:
   - Check `mlsdm_memory_usage_bytes` metric
   - Check `memory_used` field in log
   - Consider restarting pod or scaling down
4. **Timeout Issues**:
   - Check `mlsdm_generate_latency_seconds` histogram
   - Check LLM backend health
   - Consider increasing timeout or scaling LLM
5. **Recovery**: System has auto-recovery (after cooldown period), or manually restart

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: mlsdm-alerts
    rules:
      - alert: HighMoralRejectionRate
        expr: |
          sum(rate(mlsdm_moral_rejections_total[5m]))
          / sum(rate(mlsdm_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High moral rejection rate (> 10%)"

      - alert: EmergencyShutdownTriggered
        expr: mlsdm_emergency_shutdown_active == 1
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "MLSDM emergency shutdown is active"

      - alert: HighP95Latency
        expr: |
          histogram_quantile(0.95,
            sum(rate(mlsdm_request_latency_seconds_bucket[5m])) by (le)
          ) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency exceeds 500ms"

      - alert: HighAphasiaCriticalRate
        expr: |
          sum(rate(mlsdm_aphasia_detected_total{severity_bucket="critical"}[5m]))
          / sum(rate(mlsdm_aphasia_detected_total[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate of critical aphasia detections (> 20%)"
```

## Troubleshooting

### No Metrics on /health/metrics

1. Check the API is running: `curl http://localhost:8000/health`
2. Verify Prometheus client is installed: `pip show prometheus-client`
3. Check for import errors in logs

### Tracing Not Working

1. Verify MLSDM_OTEL_ENABLED is set to "true" (case-sensitive)
2. Check exporter type is valid: `console`, `otlp`, `jaeger`, or `none`
3. For OTLP, verify endpoint is reachable
4. Check for OpenTelemetry SDK initialization errors in logs

### High Latency

1. Check `mlsdm_request_latency_seconds` histogram for distribution
2. Look at individual span durations in traces
3. Common bottlenecks:
   - `mlsdm.llm_call`: LLM API latency
   - `mlsdm.memory_retrieval`: Memory search latency
   - `mlsdm.aphasia_repair`: Repair processing time

### High Moral Rejection Rate

1. Check `mlsdm_moral_threshold` gauge value
2. Review rejection reasons in `mlsdm_moral_rejections_total` labels
3. Check if threshold is adapting correctly
4. Review logs for `moral_precheck` and `post_moral_check` events

## Integration Examples

### Jaeger Setup

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  mlsdm-api:
    image: mlsdm-api:latest
    environment:
      - MLSDM_OTEL_ENABLED=true
      - OTEL_EXPORTER_TYPE=otlp
      - MLSDM_OTEL_ENDPOINT=http://jaeger:4318
```

### Prometheus + Grafana Stack

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./deploy/grafana:/etc/grafana/provisioning/dashboards
```

## Performance Testing & SLO Validation

### Automated Performance Tests

The repository includes comprehensive performance and resilience tests located in:
- `tests/perf/` - SLO validation tests for API endpoints
- `tests/resilience/` - Failure mode and chaos tests

### Running Performance Tests

**Quick Validation** (< 2 minutes):
```bash
# Test API endpoint SLOs under light load
pytest tests/perf/test_slo_api_endpoints.py -v -m "not slow"

# Test resilience (rate limiting, circuit breakers, timeouts)
pytest tests/resilience/ -v -m "not slow"
```

**Comprehensive Validation** (~15 minutes):
```bash
# Full performance test suite including moderate load
pytest tests/perf/ -v

# Full resilience test suite including slow tests
pytest tests/resilience/ -v
```

### SLO Constants

Performance targets are defined in `src/mlsdm/config/perf_slo.py`:

```python
from mlsdm.config.perf_slo import (
    DEFAULT_LATENCY_SLO,
    DEFAULT_ERROR_RATE_SLO,
    get_load_profile,
)

# Example: Check if latency meets SLO
assert latency_p95 < DEFAULT_LATENCY_SLO.api_p95_ms

# Example: Get standard load profile
profile = get_load_profile("light")  # 50 requests, 5 concurrent
```

### Load Test Utilities

Use `tests/perf/utils.py` for custom load tests:

```python
from tests.perf.utils import run_load_test, LoadTestResults

def my_operation():
    # Your operation to test
    response = client.post("/generate", json={"prompt": "test"})
    assert response.status_code == 200

# Run load test
results = run_load_test(
    operation=my_operation,
    n_requests=100,
    concurrency=10,
)

# Check results
print(f"P95 latency: {results.p95_latency_ms:.2f}ms")
print(f"Error rate: {results.error_rate_percent:.2f}%")
assert results.p95_latency_ms < 150.0  # Custom SLO
```

### CI Integration

Performance and resilience tests run automatically in CI:
- **On main branch**: Fast subset (< 5 min)
- **On labeled PRs**: Add `perf` or `resilience` label to trigger
- **Nightly**: Full comprehensive suite at 2 AM UTC
- **Manual**: GitHub Actions workflow dispatch

See `.github/workflows/perf-resilience.yml` for configuration.

### Interpreting Test Results

**Successful Test Run**:
```
tests/perf/test_slo_api_endpoints.py::TestGenerateEndpointSLO::test_generate_latency_light_load PASSED
```
- All assertions passed
- Latency and error rate within SLO targets

**Failed Test**:
```
AssertionError: P95 latency 185.23ms exceeds SLO (150ms)
```
- Performance regression detected
- Investigate recent changes
- Profile slow operations

### Performance Metrics to Monitor

When running performance tests, monitor these key metrics:

1. **Latency Distribution**:
   - P50 (median)
   - P95 (SLO target)
   - P99 (tail latency)

2. **Error Rates**:
   - 5xx errors (system failures)
   - Timeouts
   - Rate limit rejections

3. **Throughput**:
   - Requests per second (RPS)
   - Concurrent request capacity
   - Queue depth

4. **Resource Utilization**:
   - Memory usage
   - CPU utilization
   - Network I/O

## Best Practices

1. **Always use correlation IDs** - Pass `request_id` through the entire pipeline
2. **Never log PII** - Use `payload_scrubber` for any user content
3. **Set appropriate sampling** - Use 10% sampling in high-traffic production
4. **Monitor error budgets** - Set up alerts before budget exhaustion
5. **Review traces periodically** - Look for slow spans and optimization opportunities

---

## Structured Error Logging with Error Codes (OBS-004)

MLSDM uses a structured error code system for consistent error identification and automated alerting.

### Error Code Format

Error codes follow the pattern: `E{category}{number}`

| Category | Range | Description |
|----------|-------|-------------|
| **E1xx** | Input | Input validation errors |
| **E2xx** | Auth | Authentication/Authorization errors |
| **E3xx** | Moral | Moral filter errors |
| **E4xx** | Memory | Memory/PELM errors |
| **E5xx** | Rhythm | Cognitive rhythm errors |
| **E6xx** | LLM | LLM/Generation errors |
| **E7xx** | System | System/Infrastructure errors |
| **E8xx** | Config | Configuration errors |
| **E9xx** | API | API/Request errors |

### Common Error Codes

| Code | Name | Description | Recoverable |
|------|------|-------------|-------------|
| `E100` | VALIDATION_ERROR | Input validation failed | Yes |
| `E101` | INVALID_VECTOR | Invalid event vector dimension | Yes |
| `E102` | INVALID_MORAL_VALUE | Moral value out of range | Yes |
| `E201` | INVALID_TOKEN | Invalid authentication token | No |
| `E203` | INSUFFICIENT_PERMISSIONS | Insufficient permissions | No |
| `E301` | MORAL_THRESHOLD_EXCEEDED | Moral threshold not met | Yes |
| `E302` | TOXIC_CONTENT_DETECTED | Toxic content in input | Yes |
| `E401` | MEMORY_CAPACITY_EXCEEDED | Memory capacity limit | No |
| `E501` | SLEEP_PHASE_REJECTION | Rejected during sleep | Yes |
| `E601` | LLM_TIMEOUT | LLM request timed out | Yes |
| `E602` | LLM_RATE_LIMITED | LLM rate limit exceeded | Yes |
| `E701` | EMERGENCY_SHUTDOWN | System in emergency shutdown | No |
| `E901` | RATE_LIMIT_EXCEEDED | API rate limit exceeded | Yes |
| `E902` | REQUEST_TIMEOUT | Request timed out | Yes |

### Using Error Code Logging

```python
from mlsdm.observability.logger import get_observability_logger

logger = get_observability_logger()

# Log with specific error code
logger.log_error_with_code(
    error_code="E301",
    message="Moral threshold exceeded",
    details={"score": 0.3, "threshold": 0.5},
    recoverable=True,
    request_id="req-12345"
)

# Convenience methods
logger.log_validation_error(field="prompt", reason="empty string")
logger.log_auth_error(error_code="E201", reason="expired token")
logger.log_moral_filter_error(error_code="E301", score=0.3, threshold=0.5)
logger.log_llm_error(error_code="E601", provider="openai", reason="timeout")
```

### Log Output Format

```json
{
  "timestamp": "2025-12-06T07:30:00.123Z",
  "level": "ERROR",
  "event_type": "system_error",
  "message": "[E301] Moral threshold exceeded",
  "correlation_id": "abc-123",
  "metrics": {
    "error_code": "E301",
    "recoverable": true,
    "detail_score": 0.3,
    "detail_threshold": 0.5,
    "request_id": "req-12345"
  },
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331"
}
```

### Alerting on Error Codes

Configure Prometheus alerts based on error codes:

```yaml
groups:
- name: mlsdm-error-codes
  rules:
  - alert: HighMoralRejections
    expr: |
      sum(rate(mlsdm_errors_total{error_code=~"E3.."}[5m])) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High rate of moral filter rejections (E3xx)"

  - alert: AuthenticationErrors
    expr: |
      sum(rate(mlsdm_errors_total{error_code=~"E2.."}[5m])) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Authentication errors detected (E2xx)"

  - alert: LLMTimeouts
    expr: |
      sum(rate(mlsdm_errors_total{error_code="E601"}[5m])) > 0.01
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "LLM timeout errors (E601)"
```

### Full Error Code Reference

See [`src/mlsdm/utils/errors.py`](src/mlsdm/utils/errors.py) for the complete error code enum and default messages.
