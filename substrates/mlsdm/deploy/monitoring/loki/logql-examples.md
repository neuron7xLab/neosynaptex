# LogQL Query Examples for MLSDM
# ================================
# This document provides example LogQL queries for common MLSDM log analysis.

## Basic Queries

### View all MLSDM logs
```logql
{job="mlsdm"}
```

### Filter by log level
```logql
{job="mlsdm"} | json | level="ERROR"
```

```logql
{job="mlsdm"} | json | level=~"ERROR|WARN"
```

### View specific event types
```logql
{job="mlsdm"} | json | event_type="request_completed"
```

```logql
{job="mlsdm"} | json | event_type="emergency_shutdown"
```

---

## Error Analysis

### All errors with error codes
```logql
{job="mlsdm"} | json | level="ERROR" | line_format "{{.error_code}} - {{.message}}"
```

### Specific error code category (E3xx = Moral filter)
```logql
{job="mlsdm"} | json | error_code=~"E3.."
```

### Count errors by error code (last hour)
```logql
sum by (error_code) (count_over_time({job="mlsdm"} | json | level="ERROR" [1h]))
```

### LLM timeout errors (E601)
```logql
{job="mlsdm"} | json | error_code="E601"
```

---

## Request Lifecycle

### Trace a specific request
```logql
{job="mlsdm"} | json | request_id="req-12345"
```

### View rejected requests
```logql
{job="mlsdm"} | json | event_type="request_rejected"
```

### Requests with high latency (>500ms)
```logql
{job="mlsdm"} | json | latency_ms > 500
```

### Moral filter rejections
```logql
{job="mlsdm"} | json | event_type="moral_rejected" | line_format "score={{.moral_value}} threshold={{.threshold}}"
```

---

## Emergency Shutdown Analysis

### All emergency shutdown events
```logql
{job="mlsdm"} | json | event_type=~"emergency_shutdown.*"
```

### Emergency shutdowns with context
```logql
{job="mlsdm"}
  | json
  | event_type="emergency_shutdown"
  | line_format "reason={{.reason}} phase={{.phase}} memory_mb={{.memory_mb}}"
```

### Count emergency shutdowns (last 24h)
```logql
count_over_time({job="mlsdm"} | json | event_type="emergency_shutdown" [24h])
```

---

## Cognitive State

### Phase transitions
```logql
{job="mlsdm"} | json | event_type=~".*_phase_entered"
```

### Wake phase only
```logql
{job="mlsdm"} | json | phase="wake"
```

### Sleep phase rejections
```logql
{job="mlsdm"} | json | error_code="E501"
```

---

## Aphasia Analysis

### Aphasia detection events
```logql
{job="mlsdm"} | json | event_type="aphasia_detected"
```

### Aphasia repairs
```logql
{job="mlsdm"} | json | event_type="aphasia_repaired"
```

### High severity aphasia (>0.7)
```logql
{job="mlsdm"} | json | event_type=~"aphasia.*" | severity > 0.7
```

---

## Performance Metrics (from logs)

### Average latency (last hour)
```logql
avg_over_time({job="mlsdm"} | json | unwrap latency_ms [1h])
```

### 95th percentile latency
```logql
quantile_over_time(0.95, {job="mlsdm"} | json | unwrap latency_ms [1h])
```

### Request rate (per minute)
```logql
rate({job="mlsdm"} | json | event_type="request_completed" [1m])
```

---

## Trace Correlation

### Find logs for a specific trace
```logql
{job="mlsdm"} | json | trace_id="0af7651916cd43dd8448eb211c80319c"
```

### Logs with missing trace context (potential issues)
```logql
{job="mlsdm"} | json | trace_id=""
```

---

## Dashboards

### SLO Compliance Panel Query
```logql
# Error rate (should be < 0.1%)
sum(rate({job="mlsdm"} | json | level="ERROR" [5m]))
/
sum(rate({job="mlsdm"} | json [5m]))
* 100
```

### Error Budget Burn Rate
```logql
# Burn rate calculation (1 = using budget at expected rate)
(
  sum(rate({job="mlsdm"} | json | level="ERROR" [1h]))
  /
  sum(rate({job="mlsdm"} | json [1h]))
) / 0.001
```

---

## Alerting Rules

### Alert on high error rate
```yaml
groups:
- name: mlsdm-log-alerts
  rules:
  - alert: HighErrorRateFromLogs
    expr: |
      sum(count_over_time({job="mlsdm"} | json | level="ERROR" [5m]))
      /
      sum(count_over_time({job="mlsdm"} | json [5m])) > 0.01
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in MLSDM logs"
```

---

## Tips

1. **Use labels efficiently**: Loki indexes labels, so use them for high-cardinality filtering
2. **JSON parsing**: Always use `| json` before filtering on JSON fields
3. **Time ranges**: Use appropriate time ranges to avoid scanning too much data
4. **Rate vs Count**: Use `rate()` for dashboards, `count_over_time()` for totals
5. **Unwrap**: Use `| unwrap field_name` to extract numeric values for aggregations
