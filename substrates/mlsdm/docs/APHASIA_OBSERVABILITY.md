# Aphasia Observability Guide

This document describes the observability features available for monitoring Aphasia-Broca
detection and repair in the MLSDM system.

## Overview

The Aphasia-Broca subsystem detects telegraphic speech patterns in LLM outputs that are
characteristic of Broca's aphasia (agrammatism, missing function words, short fragmented
sentences) [@asha_aphasia; @fedorenko2023_agrammatic]. When detected, the system can
optionally repair these outputs.

**Non-Clinical Boundary:** Aphasia/Broca terminology in MLSDM denotes LLM-output
phenotypes inspired by literature. It is not a clinical aphasia model and must not be
used for diagnosis or medical decisions.

All observability features are designed to expose only **metadata** - no user prompts,
LLM responses, or other content is ever logged or exposed through metrics.

## Structured Logging

### Logger Configuration

The aphasia subsystem uses a dedicated logger named `mlsdm.aphasia`. Configure it in your
application's logging setup:

```python
import logging

# Configure aphasia logger
logging.getLogger("mlsdm.aphasia").setLevel(logging.INFO)
logging.getLogger("mlsdm.aphasia").addHandler(logging.StreamHandler())
```

### Log Format

Each aphasia detection event emits a single structured log record with the following fields:

```
[APHASIA] decision=<decision> is_aphasic=<bool> severity=<float> flags=<csv>
          detect_enabled=<bool> repair_enabled=<bool> severity_threshold=<float>
```

| Field | Description |
|-------|-------------|
| `decision` | The action taken: `skip`, `detected_no_repair`, or `repaired` |
| `is_aphasic` | Whether aphasia was detected (`True`/`False`) |
| `severity` | Aphasia severity score (0.0 to 1.0) |
| `flags` | Comma-separated list of detected issues (e.g., `short_sentences,low_function_words`) |
| `detect_enabled` | Whether detection was enabled |
| `repair_enabled` | Whether repair was enabled |
| `severity_threshold` | Configured threshold for triggering repair |

### Example Log Output

```
INFO:mlsdm.aphasia:[APHASIA] decision=repaired is_aphasic=True severity=0.750 flags=short_sentences,low_function_words detect_enabled=True repair_enabled=True severity_threshold=0.300
```

## Prometheus Metrics

### Available Metrics

The aphasia subsystem exports three Prometheus metrics:

#### `mlsdm_aphasia_events_total`

**Type:** Counter

Counts all aphasia detection/repair events.

| Label | Values | Description |
|-------|--------|-------------|
| `mode` | `full`, `monitor`, `disabled` | Detection mode |
| `is_aphasic` | `True`, `False` | Whether aphasia was detected |
| `repair_applied` | `True`, `False` | Whether repair was applied |

**Example queries:**

```promql
# Total aphasia events per minute
rate(mlsdm_aphasia_events_total[1m])

# Aphasic responses that were repaired
mlsdm_aphasia_events_total{is_aphasic="True", repair_applied="True"}

# Detection rate (aphasic / total)
sum(rate(mlsdm_aphasia_events_total{is_aphasic="True"}[5m])) /
sum(rate(mlsdm_aphasia_events_total[5m]))
```

#### `mlsdm_aphasia_severity`

**Type:** Histogram

Distribution of aphasia severity scores (0.0 to 1.0).

**Buckets:** 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0

**Example queries:**

```promql
# Average severity over time
rate(mlsdm_aphasia_severity_sum[5m]) / rate(mlsdm_aphasia_severity_count[5m])

# 95th percentile severity
histogram_quantile(0.95, rate(mlsdm_aphasia_severity_bucket[5m]))

# Count of high-severity events (> 0.7)
mlsdm_aphasia_severity_bucket{le="1.0"} - mlsdm_aphasia_severity_bucket{le="0.7"}
```

#### `mlsdm_aphasia_flags_total`

**Type:** Counter

Counts individual aphasia flags detected.

| Label | Values | Description |
|-------|--------|-------------|
| `flag` | `short_sentences`, `low_function_words`, `high_fragment_ratio`, etc. | Flag type |

**Example queries:**

```promql
# Most common aphasia indicators
topk(5, sum by (flag) (rate(mlsdm_aphasia_flags_total[1h])))

# Rate of low function word detection
rate(mlsdm_aphasia_flags_total{flag="low_function_words"}[5m])
```

### Integration with Prometheus

The metrics are automatically registered when the aphasia telemetry layer is used.
To expose them via your application's `/metrics` endpoint, ensure your metrics endpoint
includes the aphasia metrics registry:

```python
from mlsdm.observability import get_aphasia_metrics_exporter

# Get the singleton metrics exporter
metrics = get_aphasia_metrics_exporter()

# The metrics are automatically available in the default Prometheus registry
# If using a custom registry, pass it when first calling get_aphasia_metrics_exporter()
```

## Grafana Dashboard

### Basic Dashboard Configuration

Here's a JSON schema for a basic Grafana dashboard to monitor aphasia metrics:

```json
{
  "dashboard": {
    "title": "MLSDM Aphasia Monitoring",
    "panels": [
      {
        "title": "Aphasia Events Rate",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(mlsdm_aphasia_events_total[5m])) by (is_aphasic)",
            "legendFormat": "is_aphasic={{is_aphasic}}"
          }
        ]
      },
      {
        "title": "Severity Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum(rate(mlsdm_aphasia_severity_bucket[5m])) by (le)",
            "format": "heatmap"
          }
        ]
      },
      {
        "title": "Average Severity (5m)",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(mlsdm_aphasia_severity_sum[5m]) / rate(mlsdm_aphasia_severity_count[5m])"
          }
        ]
      },
      {
        "title": "Repair Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(rate(mlsdm_aphasia_events_total{repair_applied=\"True\"}[5m])) / sum(rate(mlsdm_aphasia_events_total{is_aphasic=\"True\"}[5m]))"
          }
        ]
      },
      {
        "title": "Top Aphasia Flags",
        "type": "table",
        "targets": [
          {
            "expr": "topk(10, sum by (flag) (rate(mlsdm_aphasia_flags_total[1h])))",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

### Key Panels to Include

1. **Events Rate by Detection Status** - Shows the rate of aphasic vs non-aphasic responses
2. **Severity Heatmap** - Visualizes the distribution of severity scores over time
3. **Average Severity** - Quick glance at current severity levels
4. **Repair Success Rate** - Percentage of aphasic responses that were repaired
5. **Top Flags** - Most commonly detected aphasia indicators

## Privacy and Security

The aphasia observability layer is designed with privacy in mind:

- **No Content Logging**: Prompts and responses are never included in logs or metrics
- **Metadata Only**: Only aggregate statistics and predefined flags are recorded
- **PII Protection**: No user identifiers or sensitive data is exposed

### Validation Tests

The system includes security tests that verify:

1. No prompt text appears in logs
2. No response text appears in logs
3. Only predefined metadata fields are logged
4. Secrets in prompts/responses are never leaked

See `tests/security/test_aphasia_logging_privacy.py` for the complete test suite.

## Configuration

### Enabling/Disabling Features

```python
from mlsdm.extensions import NeuroLangWrapper

wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embedder,
    aphasia_detect_enabled=True,   # Enable detection
    aphasia_repair_enabled=True,   # Enable repair
    aphasia_severity_threshold=0.3, # Severity threshold for repair
)
```

### Modes

| Mode | Detection | Repair | Metrics | Logging |
|------|-----------|--------|---------|---------|
| Full (`detect=True, repair=True`) | ✓ | ✓ | ✓ | ✓ |
| Monitor (`detect=True, repair=False`) | ✓ | ✗ | ✓ | ✓ |
| Disabled (`detect=False`) | ✗ | ✗ | ✗ | ✗ |

## Alerting Recommendations

Consider setting up alerts for:

1. **High Aphasia Rate**: `rate(mlsdm_aphasia_events_total{is_aphasic="True"}[5m]) > 0.1`
2. **High Severity Spike**: `histogram_quantile(0.95, rate(mlsdm_aphasia_severity_bucket[5m])) > 0.8`
3. **Repair Failures**: When repairs are enabled but not applying (monitor logs)

## Troubleshooting

### No Metrics Appearing

1. Verify `aphasia_detect_enabled=True` in your wrapper configuration
2. Check that the Prometheus endpoint includes the aphasia metrics registry
3. Ensure the wrapper's `generate()` method is being called

### Missing Log Records

1. Configure the `mlsdm.aphasia` logger at INFO level or below
2. Add a handler to the logger
3. Verify detection is enabled in your configuration
