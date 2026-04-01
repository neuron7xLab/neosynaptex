# Memory Subsystem Observability Guide

This document describes the observability features available for monitoring the MLSDM memory subsystems:
- **PELM** (Phase-Entangled Lattice Memory)
- **Multi-Level Synaptic Memory**

## Overview

The memory observability layer provides comprehensive monitoring for memory operations through three pillars:

1. **Structured Logging** - JSON-formatted logs with operation metadata
2. **Prometheus Metrics** - Counters, gauges, and histograms for monitoring
3. **OpenTelemetry Tracing** - Spans for distributed tracing (when enabled)

All observability features are designed to expose only **metadata** - no raw vector data is ever logged or exposed through metrics.

## Quick Start

### Import Memory Observability Functions

```python
from mlsdm.observability import (
    # Metrics exporter
    get_memory_metrics_exporter,

    # Convenience functions for recording
    record_pelm_store,
    record_pelm_retrieve,
    record_synaptic_update,
    record_pelm_corruption,

    # Timer helper
    MemoryOperationTimer,
)
```

### Using PELM with Observability

The PELM class automatically records observability data when performing operations:

```python
from mlsdm.memory import PELM

# Create PELM instance
memory = PELM(dimension=384, capacity=20000)

# Store with correlation ID for request tracking
index = memory.entangle(
    vector=[0.1, 0.2, ...],  # 384-dim vector
    phase=0.5,
    correlation_id="request-123"  # Optional
)

# Retrieve with correlation ID
results = memory.retrieve(
    query_vector=[0.1, 0.2, ...],
    current_phase=0.5,
    correlation_id="request-123"  # Optional
)
```

### Using Synaptic Memory with Observability

```python
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
import numpy as np

# Create synaptic memory
synaptic = MultiLevelSynapticMemory(dimension=384)

# Update with correlation ID
event = np.random.randn(384).astype(np.float32)
synaptic.update(event, correlation_id="request-123")
```

## Prometheus Metrics

### PELM Metrics

#### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_memory_pelm_store_total` | - | Total PELM entangle (store) operations |
| `mlsdm_memory_pelm_retrieve_total` | `result` | Total PELM retrieve operations (hit/miss/error) |
| `mlsdm_memory_pelm_corruption_total` | `recovered` | Corruption events detected (true/false for recovery) |

#### Gauges

| Metric | Description |
|--------|-------------|
| `mlsdm_memory_pelm_capacity_used` | Current number of items stored |
| `mlsdm_memory_pelm_capacity_total` | Maximum capacity |
| `mlsdm_memory_pelm_utilization_ratio` | Capacity utilization (0.0 to 1.0) |
| `mlsdm_memory_pelm_bytes` | Estimated memory usage in bytes |

#### Histograms

| Metric | Buckets (ms) | Description |
|--------|--------------|-------------|
| `mlsdm_memory_pelm_store_latency_milliseconds` | 0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250 | Store operation latency |
| `mlsdm_memory_pelm_retrieve_latency_milliseconds` | 0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500 | Retrieve operation latency |

### Synaptic Memory Metrics

#### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `mlsdm_memory_synaptic_update_total` | - | Total synaptic update operations |
| `mlsdm_memory_synaptic_consolidation_total` | `transfer` | Consolidation events (l1_to_l2, l2_to_l3) |

#### Gauges

| Metric | Description |
|--------|-------------|
| `mlsdm_memory_synaptic_l1_norm` | L1 (short-term) layer norm |
| `mlsdm_memory_synaptic_l2_norm` | L2 (mid-term) layer norm |
| `mlsdm_memory_synaptic_l3_norm` | L3 (long-term) layer norm |
| `mlsdm_memory_synaptic_bytes` | Estimated memory usage in bytes |

#### Histograms

| Metric | Buckets (ms) | Description |
|--------|--------------|-------------|
| `mlsdm_memory_synaptic_update_latency_milliseconds` | 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10 | Update operation latency |

## Structured Logging

### Logger Configuration

The memory subsystem uses a dedicated logger named `mlsdm.memory`:

```python
import logging

# Configure memory logger
logging.getLogger("mlsdm.memory").setLevel(logging.DEBUG)
```

### Log Events

Logs are structured JSON with consistent fields:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "DEBUG",
  "event_type": "memory_store",
  "correlation_id": "request-123",
  "metrics": {
    "event": "pelm_store",
    "component": "pelm",
    "index": 5,
    "phase": 0.5,
    "vector_norm": 1.234,
    "capacity_used": 100,
    "capacity_total": 20000,
    "utilization": 0.005,
    "latency_ms": 2.5
  }
}
```

### Event Types

| Event | Level | Description |
|-------|-------|-------------|
| `pelm_store` | DEBUG | PELM entangle operation completed |
| `pelm_retrieve` | DEBUG | PELM retrieve operation completed |
| `pelm_capacity_warning` | WARNING | Capacity utilization ≥ 90% |
| `pelm_corruption_detected` | ERROR | Memory corruption detected |
| `pelm_recovery_attempted` | ERROR | Corruption recovery attempted |
| `synaptic_update` | DEBUG | Synaptic memory update completed |
| `synaptic_consolidation` | DEBUG | Layer transfer occurred (L1→L2 or L2→L3) |

## OpenTelemetry Tracing

### Span Names

| Span Name | Description |
|-----------|-------------|
| `mlsdm.memory.pelm_store` | PELM store operation |
| `mlsdm.memory.pelm_retrieve` | PELM retrieve operation |
| `mlsdm.memory.synaptic_update` | Synaptic memory update |

### Span Attributes

All spans include:

| Attribute | Type | Description |
|-----------|------|-------------|
| `mlsdm.memory.operation` | string | Operation type (store/retrieve/update) |
| `mlsdm.memory.type` | string | Memory type (pelm/synaptic) |
| `mlsdm.correlation_id` | string | Request correlation ID (if provided) |

PELM-specific attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `mlsdm.memory.phase` | float | Phase value for store |
| `mlsdm.memory.query_phase` | float | Query phase for retrieve |
| `mlsdm.memory.phase_tolerance` | float | Phase tolerance for retrieve |
| `mlsdm.memory.top_k` | int | Maximum results for retrieve |
| `mlsdm.memory.dimension` | int | Vector dimension |

### Using Trace Context Managers

```python
from mlsdm.observability import trace_pelm_store, trace_pelm_retrieve, trace_synaptic_update

# Manual span creation
with trace_pelm_store(phase=0.5, dimension=384, correlation_id="req-123") as span:
    # Perform store operation
    span.set_attribute("mlsdm.memory.results_count", 1)
```

## Example PromQL Queries

### PELM Capacity Monitoring

```promql
# Current utilization
mlsdm_memory_pelm_utilization_ratio

# Capacity trend over time
rate(mlsdm_memory_pelm_capacity_used[5m])

# High utilization alert (> 90%)
mlsdm_memory_pelm_utilization_ratio > 0.9
```

### PELM Performance

```promql
# P95 store latency
histogram_quantile(0.95, rate(mlsdm_memory_pelm_store_latency_milliseconds_bucket[5m]))

# P95 retrieve latency
histogram_quantile(0.95, rate(mlsdm_memory_pelm_retrieve_latency_milliseconds_bucket[5m]))

# Hit rate
sum(rate(mlsdm_memory_pelm_retrieve_total{result="hit"}[5m])) /
sum(rate(mlsdm_memory_pelm_retrieve_total[5m]))
```

### Synaptic Memory Monitoring

```promql
# Update rate per second
rate(mlsdm_memory_synaptic_update_total[1m])

# Consolidation events per minute
rate(mlsdm_memory_synaptic_consolidation_total[1m])

# L1/L2/L3 norm ratios (memory health)
mlsdm_memory_synaptic_l2_norm / mlsdm_memory_synaptic_l1_norm
```

### Corruption Monitoring

```promql
# Total corruption events
mlsdm_memory_pelm_corruption_total

# Recovery success rate
sum(mlsdm_memory_pelm_corruption_total{recovered="true"}) /
sum(mlsdm_memory_pelm_corruption_total)
```

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: mlsdm-memory-alerts
    rules:
      - alert: PELMCapacityHigh
        expr: mlsdm_memory_pelm_utilization_ratio > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PELM capacity utilization above 90%"
          description: "Current utilization: {{ $value | humanizePercentage }}"

      - alert: PELMCapacityCritical
        expr: mlsdm_memory_pelm_utilization_ratio > 0.95
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "PELM capacity critically high (> 95%)"

      - alert: PELMCorruptionDetected
        expr: increase(mlsdm_memory_pelm_corruption_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "PELM memory corruption detected"

      - alert: PELMHighRetrieveLatency
        expr: |
          histogram_quantile(0.95,
            rate(mlsdm_memory_pelm_retrieve_latency_milliseconds_bucket[5m])
          ) > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PELM P95 retrieve latency exceeds 50ms"

      - alert: LowMemoryHitRate
        expr: |
          sum(rate(mlsdm_memory_pelm_retrieve_total{result="hit"}[5m])) /
          sum(rate(mlsdm_memory_pelm_retrieve_total[5m])) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Memory hit rate below 50%"
```

## Grafana Dashboard

A basic Grafana dashboard should include:

1. **PELM Capacity Panel** - Gauge showing utilization ratio
2. **PELM Operations Rate** - Time series of store/retrieve operations
3. **PELM Latency Distribution** - Histogram of store/retrieve latencies
4. **Synaptic Memory Norms** - Time series of L1/L2/L3 norms
5. **Consolidation Events** - Counter for L1→L2 and L2→L3 transfers
6. **Corruption Events** - Counter with recovery status

## Privacy and Security

The memory observability layer is designed with privacy in mind:

- **No Vector Data**: Raw embedding vectors are never logged or exposed
- **Metadata Only**: Only norms, indices, counts, and timing data are recorded
- **No User Data**: No user identifiers or content is captured

### What IS Captured

- Vector norms (L2 magnitude)
- Storage indices
- Phase values
- Operation counts
- Latency measurements
- Capacity utilization

### What IS NOT Captured

- Raw embedding vectors
- User prompts or responses
- Any PII or sensitive data

## Running Tests

```bash
# Run memory observability tests
pytest tests/observability/test_memory_observability.py -v

# Run with coverage
pytest tests/observability/test_memory_observability.py --cov=src/mlsdm/observability/memory_telemetry
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MLSDM_MEMORY_LOG_LEVEL` | Memory logger level | `INFO` |
| `MLSDM_OTEL_ENABLED` | Enable tracing spans | `false` |

### Programmatic Configuration

```python
import logging
from mlsdm.observability import get_memory_logger

# Set memory logging level
logger = get_memory_logger()
logger.setLevel(logging.DEBUG)
```

## See Also

- [OBSERVABILITY_GUIDE.md](../OBSERVABILITY_GUIDE.md) - Main observability guide
- [OBSERVABILITY_SPEC.md](../OBSERVABILITY_SPEC.md) - Observability specification
- [APHASIA_OBSERVABILITY.md](APHASIA_OBSERVABILITY.md) - Aphasia-specific observability
