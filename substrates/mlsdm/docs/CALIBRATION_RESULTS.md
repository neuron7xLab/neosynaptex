# CALIBRATION RESULTS

This document contains the results of calibration experiments for MLSDM components.
Use these results to validate threshold settings and tune parameters for your deployment.

**Last Run**: 2025-11-25

---

## 1. Moral Filter Calibration

### 1.1 MoralFilter (v1) - Threshold Sweep

Tests the impact of moral threshold on toxic rejection and false positive rates.

| Threshold | Toxic Reject % | False Positive % | Notes |
|-----------|----------------|------------------|-------|
| 0.30 | 66.7% | 0.0% | Too permissive - misses toxic content |
| 0.40 | 83.3% | 0.0% | Better but still misses some toxic |
| **0.50** | **100.0%** | **14.3%** | **Balanced - recommended default** |
| 0.60 | 100.0% | 28.6% | Too strict - blocks valid content |
| 0.70 | 100.0% | 42.9% | Very strict - high false positives |

**Analysis**:
- Threshold = 0.50 provides 100% toxic rejection with acceptable false positive rate (14.3%)
- Values below 0.45 miss toxic content (safety risk)
- Values above 0.55 have excessive false positives (quality issue)

**Recommendation**: Use threshold=0.50 with min_threshold=0.30 as safety floor.

### 1.2 MoralFilterV2 - Threshold Sweep

MoralFilterV2 uses EMA-based adaptation with dead band.

| Threshold | Toxic Reject % | False Positive % | Notes |
|-----------|----------------|------------------|-------|
| 0.30 | 66.7% | 0.0% | Same baseline behavior |
| 0.40 | 83.3% | 0.0% | Same baseline behavior |
| **0.50** | **100.0%** | **14.3%** | **Recommended** |
| 0.60 | 100.0% | 28.6% | Too strict |
| 0.70 | 100.0% | 42.9% | Very strict |

**MoralFilterV2 Specific Parameters**:
- `dead_band = 0.05`: Prevents jitter in threshold adaptation
- `ema_alpha = 0.1`: Smooth adaptation to changing content patterns

---

## 2. Aphasia Detector Calibration

### 2.1 Severity Threshold Sweep

Tests the impact of severity threshold on detection rates.

| Severity | Detection % | False Positive % | Notes |
|----------|-------------|------------------|-------|
| 0.10 | 100.0% | 16.7% | Too sensitive |
| 0.20 | 100.0% | 0.0% | Good balance |
| **0.30** | **100.0%** | **0.0%** | **Recommended** |
| 0.40 | 100.0% | 0.0% | Still effective |
| 0.50 | 100.0% | 0.0% | May miss edge cases |

**Analysis**:
- Severity threshold = 0.30 provides 100% detection with 0% false positives
- Values below 0.20 may flag normal short text as aphasic
- The detector is robust across the 0.20-0.50 range

### 2.2 Min Sentence Length Sweep

Tests the impact of minimum sentence length requirement.

| Min Length | Detection % | False Positive % | Notes |
|------------|-------------|------------------|-------|
| 4.0 | 100.0% | 0.0% | Permissive |
| 5.0 | 100.0% | 0.0% | Moderate |
| **6.0** | **100.0%** | **0.0%** | **Recommended** |
| 7.0 | 100.0% | 0.0% | Stricter |
| 8.0 | 100.0% | 0.0% | Very strict |

**Recommended Aphasia Parameters**:
- `min_sentence_len = 6.0`
- `min_function_word_ratio = 0.15`
- `max_fragment_ratio = 0.5`
- `severity_threshold = 0.30`

---

## 3. PELM (Phase-Entangled Lattice Memory) Calibration

### 3.1 Phase Tolerance Sweep

Tests the impact of phase tolerance on retrieval precision/recall.

| Tolerance | Recall % | Precision % | Latency (ms) | Notes |
|-----------|----------|-------------|--------------|-------|
| 0.05 | 100.0% | 100.0% | 0.051 | Very precise |
| 0.10 | 100.0% | 100.0% | 0.051 | Precise |
| **0.15** | **100.0%** | **100.0%** | **0.050** | **Recommended** |
| 0.20 | 100.0% | 100.0% | 0.050 | Moderate |
| 0.30 | 100.0% | 100.0% | 0.050 | Wide tolerance |

**Analysis**:
- All tested tolerances achieve 100% precision/recall on test data
- Phase tolerance = 0.15 provides good balance for production use
- Latency is consistently low (~0.05ms) across all settings

### 3.2 Top-K Sweep (tolerance=0.15)

Tests the impact of top_k on retrieval quality.

| Top-K | Recall % | Precision % | Latency (ms) | Notes |
|-------|----------|-------------|--------------|-------|
| 1 | 100.0% | 100.0% | 0.044 | Minimal |
| 3 | 100.0% | 100.0% | 0.047 | Light |
| **5** | **100.0%** | **100.0%** | **0.050** | **Recommended** |
| 10 | 100.0% | 100.0% | 0.052 | Rich context |
| 20 | 100.0% | 100.0% | 0.058 | Full context |

**Recommended PELM Parameters**:
- `phase_tolerance = 0.15`
- `top_k = 5`
- `capacity = 20,000` (production default)

---

## 4. Synaptic Memory Calibration

### 4.1 Default Parameters (100 events)

With default decay rates after processing 100 events:

| Level | Norm | Description |
|-------|------|-------------|
| L1 (Short-term) | 2.7918 | Active memory |
| L2 (Medium-term) | 4.1208 | Consolidating |
| L3 (Long-term) | 1.6984 | Stable |

### 4.2 Decay Rate Comparison

Impact of decay rate configurations on memory distribution:

| λ_L1 | λ_L2 | λ_L3 | L1 Norm | L2 Norm | L3 Norm | Notes |
|------|------|------|---------|---------|---------|-------|
| 0.30 | 0.05 | 0.005 | 2.8073 | 6.4748 | 35.9447 | Slow decay - long retention |
| **0.50** | **0.10** | **0.010** | **2.7918** | **4.1208** | **1.6984** | **Balanced - recommended** |
| 0.70 | 0.15 | 0.015 | 2.3754 | 0.4744 | 0.0000 | Fast decay - short retention |

**Analysis**:
- Default configuration (λ=0.5/0.1/0.01) provides balanced memory distribution
- Slower decay leads to long-term accumulation (may cause drift)
- Faster decay prevents consolidation (memory loss risk)

**Recommended Synaptic Memory Parameters**:
- `lambda_l1 = 0.50` (short-term decay)
- `lambda_l2 = 0.10` (medium-term decay)
- `lambda_l3 = 0.01` (long-term decay)
- `theta_l1 = 1.2` (L1→L2 threshold)
- `theta_l2 = 2.5` (L2→L3 threshold)
- `gating12 = 0.45` (L1→L2 transfer)
- `gating23 = 0.30` (L2→L3 transfer)

---

## 5. Reliability Parameters

### 5.1 Circuit Breaker Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `failure_threshold` | 5 | Allow transient failures |
| `recovery_timeout` | 60.0s | Standard recovery window |
| `success_threshold` | 2 | Confirm recovery |

### 5.2 LLM Wrapper Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `llm_timeout` | 30.0s | Standard LLM latency |
| `retry_attempts` | 3 | Handle transient errors |
| `max_wake_tokens` | 2048 | Full response length |
| `max_sleep_tokens` | 150 | Forced short during sleep |

---

## 6. Rate Limiting Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `requests_per_window` | 100 | Standard API limit |
| `window_seconds` | 60 | Per-minute rate |
| `cleanup_interval` | 300s | Memory management |

---

## 7. Calibration Summary

### Safety-Critical Thresholds

| Parameter | Value | Impact |
|-----------|-------|--------|
| `moral_filter.threshold` | 0.50 | 100% toxic rejection |
| `moral_filter.min_threshold` | 0.30 | Safety floor |
| `aphasia.severity_threshold` | 0.30 | 100% detection |

### Quality Thresholds

| Parameter | Value | Impact |
|-----------|-------|--------|
| `aphasia.min_sentence_len` | 6.0 | Complete sentences |
| `pelm.phase_tolerance` | 0.15 | Precise retrieval |
| `pelm.top_k` | 5 | Sufficient context |

### Performance Thresholds

| Parameter | Value | Impact |
|-----------|-------|--------|
| `cognitive_controller.max_processing_time_ms` | 1000.0 | Latency SLO |
| `reliability.llm_timeout` | 30.0 | Request timeout |
| `pelm.capacity` | 20,000 | Memory budget |

---

## 8. Reproducing These Results

To regenerate these calibration results:

```bash
cd /path/to/mlsdm
python scripts/run_calibration_benchmarks.py
```

For more detailed analysis:

```bash
# Run aphasia evaluation
python scripts/run_aphasia_eval.py

# Run security tests
python scripts/test_security_features.py
```

---

## 9. Tuning for Your Deployment

### High-Security Deployment

For maximum safety (higher false positives acceptable):
```yaml
moral_filter:
  threshold: 0.60
  min_threshold: 0.40

aphasia:
  severity_threshold: 0.20
```

### High-Throughput Deployment

For maximum performance (slightly relaxed safety):
```yaml
moral_filter:
  threshold: 0.45

pelm:
  phase_tolerance: 0.20
  top_k: 3

cognitive_controller:
  max_processing_time_ms: 500.0
```

### Memory-Constrained Deployment

For limited memory environments:
```yaml
pelm:
  capacity: 5000

cognitive_rhythm:
  max_wake_tokens: 512
  max_sleep_tokens: 50
```

---

## Change History

| Date | Change | Impact |
|------|--------|--------|
| 2025-11-25 | Initial calibration | Baseline established |
