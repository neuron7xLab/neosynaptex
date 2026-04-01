# CALIBRATION PROTOCOL

This document describes the procedure for calibrating MLSDM thresholds and sensitivity parameters.

## Overview

Calibration ensures that MLSDM's safety, quality, and performance thresholds are properly tuned for your deployment environment. This protocol provides a reproducible procedure for:

1. Measuring current system behavior
2. Identifying optimal threshold values
3. Validating changes do not break existing behavior
4. Documenting calibration results

## Prerequisites

Before starting calibration:

```bash
# Install MLSDM with development dependencies
pip install -e ".[dev]"

# Verify installation
python -c "from config.calibration import get_calibration_summary; print('OK')"
```

## Step 1: Run Baseline Benchmarks

Run the calibration benchmark suite to establish baseline metrics:

```bash
cd /path/to/mlsdm
python scripts/run_calibration_benchmarks.py
```

This produces metrics for:
- **Moral Filter**: Toxic rejection rate, false positive rate
- **Aphasia Detector**: Detection rate, false positive rate
- **PELM Memory**: Recall, precision, latency
- **Synaptic Memory**: State distribution

Save the output for comparison after changes.

## Step 2: Review Current Calibration

Examine the current calibration settings:

```python
from config.calibration import get_calibration_summary

summary = get_calibration_summary()
for section, params in summary.items():
    print(f"\n{section}:")
    for key, value in params.items():
        print(f"  {key}: {value}")
```

## Step 3: Identify Parameters to Tune

### Safety Parameters (Tune with Caution)

| Parameter | Current | Safe Range | Impact |
|-----------|---------|------------|--------|
| `moral_filter.threshold` | 0.50 | 0.40-0.60 | Toxic rejection rate |
| `moral_filter.min_threshold` | 0.30 | 0.25-0.35 | Minimum safety floor |
| `aphasia.severity_threshold` | 0.30 | 0.20-0.40 | Repair trigger level |

### Quality Parameters

| Parameter | Current | Typical Range | Impact |
|-----------|---------|---------------|--------|
| `aphasia.min_sentence_len` | 6.0 | 4.0-8.0 | Detection sensitivity |
| `pelm.phase_tolerance` | 0.15 | 0.10-0.25 | Retrieval precision |
| `pelm.top_k` | 5 | 3-10 | Context richness |

### Performance Parameters

| Parameter | Current | Typical Range | Impact |
|-----------|---------|---------------|--------|
| `reliability.llm_timeout` | 30.0 | 10.0-60.0 | Request timeout |
| `reliability.llm_retry_attempts` | 3 | 2-5 | Retry count |
| `cognitive_rhythm.max_wake_tokens` | 2048 | 512-4096 | Response length |

## Step 4: Run Targeted Experiments

### 4.1 Moral Filter Threshold Sweep

```python
from scripts.run_calibration_benchmarks import run_moral_filter_benchmark

# Test different thresholds
for threshold in [0.4, 0.45, 0.5, 0.55, 0.6]:
    metrics = run_moral_filter_benchmark(threshold)
    print(f"Threshold {threshold}: "
          f"Toxic reject {metrics.toxic_rejection_rate:.1%}, "
          f"False positive {metrics.false_positive_rate:.1%}")
```

**Target**: 100% toxic rejection with <20% false positives

### 4.2 Aphasia Detector Sensitivity

```python
from scripts.run_calibration_benchmarks import run_aphasia_benchmark

# Test severity thresholds
for severity in [0.1, 0.2, 0.3, 0.4, 0.5]:
    metrics = run_aphasia_benchmark(severity_threshold=severity)
    print(f"Severity {severity}: "
          f"Detection {metrics.telegraphic_detection_rate:.1%}, "
          f"False positive {metrics.false_positive_rate:.1%}")
```

**Target**: 100% detection with 0% false positives

### 4.3 PELM Retrieval Quality

```python
from scripts.run_calibration_benchmarks import run_pelm_benchmark

# Test phase tolerance
for tolerance in [0.05, 0.10, 0.15, 0.20, 0.25]:
    metrics = run_pelm_benchmark(phase_tolerance=tolerance)
    print(f"Tolerance {tolerance}: "
          f"Recall {metrics.recall_at_k:.1%}, "
          f"Precision {metrics.precision_at_k:.1%}, "
          f"Latency {metrics.avg_retrieval_time_ms:.3f}ms")
```

**Target**: High recall with acceptable latency (<1ms)

## Step 5: Update Calibration Values

After identifying optimal values, update `config/calibration.py`:

```python
# In config/calibration.py

@dataclass(frozen=True)
class MoralFilterCalibration:
    threshold: float = 0.50  # Your new value
    # ... other parameters
```

Or override via config file:

```yaml
# config/production.yaml
moral_filter:
  threshold: 0.50  # Your new value

aphasia:
  severity_threshold: 0.30  # Your new value
```

## Step 6: Validate Changes

Run the full test suite to ensure changes don't break existing behavior:

```bash
# Run unit tests
pytest tests/ --ignore=tests/load -v

# Run calibration benchmarks again
python scripts/run_calibration_benchmarks.py
```

Compare before/after metrics to validate:
- Safety metrics are not degraded
- Quality metrics are improved or maintained
- Performance is acceptable

## Step 7: Document Results

Update `docs/CALIBRATION_RESULTS.md` with:

1. Date of calibration
2. Parameters changed
3. Before/after metrics
4. Rationale for changes

## Common Calibration Scenarios

### Scenario 1: Reduce False Positives

If too much legitimate content is being rejected:

```yaml
moral_filter:
  threshold: 0.45  # Lower from 0.50
```

**Trade-off**: May allow some borderline toxic content.

### Scenario 2: More Aggressive Aphasia Repair

If telegraphic responses are slipping through:

```yaml
aphasia:
  severity_threshold: 0.20  # Lower from 0.30
  min_sentence_len: 7.0     # Increase from 6.0
```

**Trade-off**: More LLM calls for repair.

### Scenario 3: Faster Response Times

If latency is too high:

```yaml
cognitive_rhythm:
  max_wake_tokens: 1024  # Reduce from 2048

reliability:
  llm_timeout: 15.0  # Reduce from 30.0
```

**Trade-off**: Shorter responses.

### Scenario 4: Memory-Constrained Deployment

If memory usage is too high:

```yaml
pelm:
  capacity: 5000  # Reduce from 20000
  top_k: 3        # Reduce from 5
```

**Trade-off**: Less context, shorter memory.

## Rollback Procedure

If calibration changes cause issues:

1. Revert to previous calibration values
2. Or use environment variables to override:
   ```bash
   export MLSDM_MORAL_FILTER__THRESHOLD=0.50
   export MLSDM_APHASIA__SEVERITY_THRESHOLD=0.30
   ```
3. Restart the application

## Monitoring Post-Calibration

After deploying new calibration:

1. Monitor rejection rates in production logs
2. Track aphasia detection/repair counts
3. Watch for latency regressions
4. Check memory usage

Use observability metrics:
```python
from mlsdm.observability.metrics import get_prometheus_metrics

metrics = get_prometheus_metrics()
# Review moral_filter_threshold_gauge, aphasia_detections_total, etc.
```

## See Also

- [CALIBRATION_MAP.md](docs/CALIBRATION_MAP.md) - Complete parameter inventory
- [CALIBRATION_RESULTS.md](docs/CALIBRATION_RESULTS.md) - Benchmark results
- [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) - Configuration overview

---

**Questions?** Open an issue on [GitHub](https://github.com/neuron7xLab/mlsdm/issues).
