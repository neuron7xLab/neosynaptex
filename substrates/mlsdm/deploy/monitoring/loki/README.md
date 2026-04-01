# ====================================================
# Loki Log Aggregation Configuration for MLSDM
# ====================================================
# This directory contains configuration for log aggregation using
# Grafana Loki with Promtail.
#
# Loki is recommended for MLSDM because:
# - Native integration with Grafana dashboards
# - Efficient storage (indexes labels, not full log content)
# - Compatible with JSON structured logs
# - Easy correlation with Prometheus metrics
#
# ====================================================

## Quick Start

### 1. Start Loki Stack

```bash
# Using Docker Compose
cd deploy/monitoring/loki
docker compose up -d

# Check health
curl http://localhost:3100/ready
```

### 2. Configure Promtail

Edit `promtail-config.yaml` to point to your MLSDM logs:

```yaml
# For file-based logs
scrape_configs:
  - job_name: mlsdm
    static_configs:
      - targets:
          - localhost
        labels:
          job: mlsdm
          __path__: /var/log/mlsdm/*.log
```

### 3. View Logs in Grafana

1. Add Loki data source: http://loki:3100
2. Navigate to Explore
3. Query logs: `{job="mlsdm"}`

## Files

- `loki-config.yaml` - Loki server configuration
- `promtail-config.yaml` - Log collector configuration
- `docker-compose.yaml` - Complete stack deployment
- `logql-examples.md` - Example LogQL queries

## Log Format

MLSDM produces JSON structured logs compatible with Loki:

```json
{
  "timestamp": "2025-12-06T07:30:00.123Z",
  "level": "INFO",
  "event_type": "request_completed",
  "correlation_id": "abc-123",
  "message": "Request completed",
  "metrics": {
    "latency_ms": 45.2,
    "accepted": true
  },
  "trace_id": "0af7651916cd43dd",
  "span_id": "b7ad6b7169203331"
}
```

## See Also

- [OBSERVABILITY_GUIDE.md](../../../OBSERVABILITY_GUIDE.md) - Full observability documentation
- [SLO_SPEC.md](../../../SLO_SPEC.md) - SLO definitions
- [RUNBOOK.md](../../../RUNBOOK.md) - Operational procedures
