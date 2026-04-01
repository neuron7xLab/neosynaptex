# MLSDM Grafana Dashboards

This document describes the Grafana dashboards available for monitoring the MLSDM Governed Cognitive Memory system.

## Overview

MLSDM exposes Prometheus-compatible metrics at `/health/metrics` that can be scraped by Prometheus and visualized in Grafana. The dashboards are designed to provide comprehensive observability into:

1. **System Health** - Overall health and resource usage
2. **Request Flow** - Request rates, latencies, and acceptance/rejection
3. **Cognitive State** - Wake/sleep phases, moral filtering, memory state
4. **Aphasia Telemetry** - Detection rates, severity distribution, repair actions
5. **Emergency Shutdown** - Critical system events

## Available Metrics

### Counters

| Metric | Description | Labels |
|--------|-------------|--------|
| `mlsdm_events_processed_total` | Total events processed | - |
| `mlsdm_events_rejected_total` | Total events rejected by moral filter | - |
| `mlsdm_errors_total` | Total errors encountered | `error_type` |
| `mlsdm_emergency_shutdowns_total` | Emergency shutdown events | `reason` |
| `mlsdm_phase_events_total` | Events per cognitive phase | `phase` |
| `mlsdm_moral_rejections_total` | Moral filter rejections | `reason` |
| `mlsdm_requests_total` | Requests by endpoint | `endpoint`, `status` |
| `mlsdm_aphasia_events_total` | Aphasia detection events | `mode`, `is_aphasic`, `repair_applied` |
| `mlsdm_aphasia_flags_total` | Individual aphasia flags | `flag` |

### Gauges

| Metric | Description | Values |
|--------|-------------|--------|
| `mlsdm_memory_usage_bytes` | Current memory usage | bytes |
| `mlsdm_moral_threshold` | Current moral filter threshold | 0.0-1.0 |
| `mlsdm_phase` | Current cognitive phase | 0=sleep, 1=wake |
| `mlsdm_memory_l1_norm` | L1 memory layer norm | float |
| `mlsdm_memory_l2_norm` | L2 memory layer norm | float |
| `mlsdm_memory_l3_norm` | L3 memory layer norm | float |
| `mlsdm_emergency_shutdown_active` | Emergency shutdown state | 0=normal, 1=active |
| `mlsdm_stateless_mode` | Stateless mode state | 0=stateful, 1=stateless |

### Histograms

| Metric | Description | Buckets (ms) |
|--------|-------------|--------------|
| `mlsdm_processing_latency_milliseconds` | Event processing latency | 1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000 |
| `mlsdm_retrieval_latency_milliseconds` | Memory retrieval latency | 0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500 |
| `mlsdm_generation_latency_milliseconds` | End-to-end generation latency | 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000 |
| `mlsdm_aphasia_severity` | Aphasia severity distribution | 0.0-1.0 in 0.1 increments |

## Dashboard Panels

### 1. System Overview Dashboard

**Purpose**: High-level system health at a glance

**Panels**:

1. **Request Rate** (Graph)
   ```promql
   rate(mlsdm_requests_total[5m])
   ```

2. **Error Rate** (Graph)
   ```promql
   rate(mlsdm_errors_total[5m])
   ```

3. **Current Phase** (Stat)
   ```promql
   mlsdm_phase
   ```

4. **Emergency Shutdown Active** (Stat, Red when 1)
   ```promql
   mlsdm_emergency_shutdown_active
   ```

5. **Memory Usage** (Graph)
   ```promql
   mlsdm_memory_usage_bytes
   ```

### 2. Request Flow Dashboard

**Purpose**: Detailed request processing metrics

**Panels**:

1. **Requests by Endpoint** (Stacked Graph)
   ```promql
   sum(rate(mlsdm_requests_total[5m])) by (endpoint)
   ```

2. **Request Status Distribution** (Pie Chart)
   ```promql
   sum(increase(mlsdm_requests_total[1h])) by (status)
   ```

3. **P50/P95/P99 Latency** (Graph)
   ```promql
   histogram_quantile(0.50, rate(mlsdm_generation_latency_milliseconds_bucket[5m]))
   histogram_quantile(0.95, rate(mlsdm_generation_latency_milliseconds_bucket[5m]))
   histogram_quantile(0.99, rate(mlsdm_generation_latency_milliseconds_bucket[5m]))
   ```

4. **Acceptance Rate** (Graph)
   ```promql
   rate(mlsdm_events_processed_total[5m]) / (rate(mlsdm_events_processed_total[5m]) + rate(mlsdm_events_rejected_total[5m]))
   ```

### 3. Cognitive State Dashboard

**Purpose**: Monitor cognitive rhythm and moral filtering

**Panels**:

1. **Wake/Sleep Phase Timeline** (State Timeline)
   ```promql
   mlsdm_phase
   ```

2. **Events by Phase** (Stacked Graph)
   ```promql
   sum(rate(mlsdm_phase_events_total[5m])) by (phase)
   ```

3. **Moral Threshold** (Graph)
   ```promql
   mlsdm_moral_threshold
   ```

4. **Moral Rejections by Reason** (Graph)
   ```promql
   sum(rate(mlsdm_moral_rejections_total[5m])) by (reason)
   ```

5. **Memory Layer Norms** (Graph)
   ```promql
   mlsdm_memory_l1_norm
   mlsdm_memory_l2_norm
   mlsdm_memory_l3_norm
   ```

### 4. Aphasia Telemetry Dashboard

**Purpose**: Monitor aphasia detection and repair

**Panels**:

1. **Aphasia Detection Rate** (Graph)
   ```promql
   rate(mlsdm_aphasia_events_total{is_aphasic="True"}[5m])
   ```

2. **Severity Distribution** (Heatmap)
   ```promql
   rate(mlsdm_aphasia_severity_bucket[5m])
   ```

3. **Repair Success Rate** (Graph)
   ```promql
   sum(rate(mlsdm_aphasia_events_total{repair_applied="True"}[5m])) / sum(rate(mlsdm_aphasia_events_total{is_aphasic="True"}[5m]))
   ```

4. **Most Common Flags** (Bar Chart)
   ```promql
   topk(10, sum(increase(mlsdm_aphasia_flags_total[1h])) by (flag))
   ```

### 5. Emergency & Errors Dashboard

**Purpose**: Critical system events and error tracking

**Panels**:

1. **Emergency Shutdown Count** (Stat)
   ```promql
   sum(increase(mlsdm_emergency_shutdowns_total[24h]))
   ```

2. **Emergency Shutdowns by Reason** (Bar Chart)
   ```promql
   sum(increase(mlsdm_emergency_shutdowns_total[24h])) by (reason)
   ```

3. **Error Rate by Type** (Stacked Graph)
   ```promql
   sum(rate(mlsdm_errors_total[5m])) by (error_type)
   ```

4. **System Status** (Traffic Light)
   - Green: `mlsdm_emergency_shutdown_active == 0`
   - Red: `mlsdm_emergency_shutdown_active == 1`

## Alert Rules

### Critical Alerts

```yaml
groups:
  - name: mlsdm_critical
    rules:
      - alert: EmergencyShutdownActive
        expr: mlsdm_emergency_shutdown_active == 1
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "MLSDM Emergency Shutdown Active"
          description: "System is in emergency shutdown state"

      - alert: HighErrorRate
        expr: rate(mlsdm_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in MLSDM"
          description: "Error rate is {{ $value }}/s"
```

### Warning Alerts

```yaml
groups:
  - name: mlsdm_warnings
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(mlsdm_generation_latency_milliseconds_bucket[5m])) > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High P99 latency in MLSDM"
          description: "P99 latency is {{ $value }}ms"

      - alert: HighRejectionRate
        expr: rate(mlsdm_events_rejected_total[5m]) / rate(mlsdm_events_processed_total[5m]) > 0.3
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High rejection rate in MLSDM"
          description: "Rejection rate is {{ $value }}"
```

## Setup Instructions

### 1. Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'mlsdm'
    static_configs:
      - targets: ['mlsdm-service:8000']
    metrics_path: '/health/metrics'
    scrape_interval: 15s
```

### 2. Import Dashboards

1. Navigate to Grafana → Dashboards → Import
2. Upload the JSON files from `docs/observability/dashboards/`
3. Select your Prometheus data source
4. Save the dashboard

### 3. Configure Alerts

1. Navigate to Grafana → Alerting → Alert Rules
2. Import the alert rules from `docs/observability/alerts/`
3. Configure notification channels (Slack, PagerDuty, etc.)

## Trace Correlation

MLSDM uses OpenTelemetry for distributed tracing. The following spans are created:

| Span Name | Kind | Description |
|-----------|------|-------------|
| `api.generate` | SERVER | Root span for /generate endpoint |
| `api.infer` | SERVER | Root span for /infer endpoint |
| `engine.generate` | INTERNAL | Engine-level generation |
| `engine.moral_precheck` | INTERNAL | Pre-flight moral check |
| `engine.grammar_precheck` | INTERNAL | Pre-flight grammar check (if FSLGS enabled) |
| `engine.llm_generation` | INTERNAL | LLM generation |
| `engine.post_moral_check` | INTERNAL | Post-generation moral check |

### Trace Attributes

All spans include:
- `mlsdm.prompt_length` - Length of input prompt (NOT the prompt itself)
- `mlsdm.moral_value` - Moral threshold used
- `mlsdm.phase` - Current cognitive phase
- `mlsdm.accepted` - Whether request was accepted
- `mlsdm.request_id` - Request correlation ID

## Production Recommendations

1. **Sampling**: For high-traffic production, configure trace sampling:
   ```bash
   export OTEL_TRACES_SAMPLER=traceidratio
   export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
   ```

2. **Cardinality**: Be cautious with high-cardinality labels. Avoid using user IDs or request IDs as metric labels.

3. **Retention**: Configure appropriate retention for metrics (7-30 days) and traces (24-48 hours).

4. **Alerting Thresholds**: Adjust alert thresholds based on your baseline traffic patterns.

## Related Documentation

- [APHASIA_OBSERVABILITY.md](../APHASIA_OBSERVABILITY.md) - Detailed aphasia telemetry specification
- [IMPLEMENTATION_SUMMARY.md](../../IMPLEMENTATION_SUMMARY.md) - System implementation overview
- [SLO_SPEC.md](../../SLO_SPEC.md) - Service Level Objectives
