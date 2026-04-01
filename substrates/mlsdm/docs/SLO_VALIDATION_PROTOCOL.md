# SLO Validation Protocol

**Version:** 1.1.0
**Last Updated:** March 2026
**Status:** ACTIVE

## Purpose

This document defines the protocol for validating Service Level Objectives (SLOs) in the MLSDM system. All SLO tests must follow this protocol to ensure consistency, determinism, and meaningful signal.

## SLO Sources of Truth

All SLO targets are defined in **`policy/observability-slo.yaml`** and loaded through the canonical policy loader (`mlsdm.policy.loader`). Tests MUST read from the loader output to ensure consistency between documentation and enforcement. `policy_contract_version` is strictly enforced (currently `1.1`), and unknown fields fail closed.

## Policy Architecture (Single Source of Truth)

**SoT:** `policy/observability-slo.yaml` → **Loader:** `mlsdm.policy.loader` (schema + canonicalization + canonical hash) → **Enforcement:** runtime SLOs, tests, and CI gates.

### Unit Normalization (Deterministic)

SLO numeric fields accept explicit units and are normalized by the loader:
- **Latency fields** (`*_ms`): allow `ms` or `s` (converted to milliseconds)
- **Percent fields** (`*_percent`): allow `%`, `percent`, or `ratio` (ratio → percent)
- **Ratio fields** (explicit validators): allow `%`, `percent`, or `ratio` (percent → ratio)

This ensures deterministic interpretation across OS/Python versions.

## SLO Invariants & Test Matrix

| Invariant | Test Location | Target | Policy Source | Enforcement |
|-----------|---------------|--------|---------------|-------------|
| **Generate P95 < 120ms** | `tests/perf/test_slo_api_endpoints.py::TestGenerateEndpointSLO` | p95 < 120ms (prod)<br>p95 < 150ms (CI) | `policy/observability-slo.yaml`<br>`thresholds.slos.api_endpoints[name=generate]` | Blocking |
| **Infer P95 < 120ms** | `tests/perf/test_slo_api_endpoints.py::TestInferEndpointSLO` | p95 < 120ms (prod)<br>p95 < 150ms (CI) | `policy/observability-slo.yaml`<br>`thresholds.slos.api_endpoints[name=infer]` | Blocking |
| **API Readiness P95 < 120ms** | `tests/perf/test_slo_api_endpoints.py::test_readiness_latency` | p95 < 120ms (prod)<br>p95 < 150ms (CI) | `policy/observability-slo.yaml`<br>`thresholds.slos.api_endpoints[name=health-readiness]` | Blocking |
| **API Liveness P95 < 50ms** | `tests/perf/test_slo_api_endpoints.py::test_liveness_latency` | p95 < 50ms (prod)<br>p95 < 75ms (CI) | `policy/observability-slo.yaml`<br>`thresholds.slos.api_endpoints[name=health-liveness]` | Blocking |
| **Event Processing P95 < 500ms** | N/A (monitoring only) | p95 < 500ms (prod)<br>p95 < 600ms (CI) | `policy/observability-slo.yaml`<br>`thresholds.slos.api_endpoints[name=event-processing]` | Advisory |
| **Memory Stays Stable** | `tests/unit/test_cognitive_controller.py::TestCognitiveControllerMemoryLeak::test_memory_stays_stable_over_time` | later_growth ≤ initial_growth × 2.0 | `policy/observability-slo.yaml`<br>`thresholds.slos.system_resources[name=memory-usage]` | Blocking |
| **Memory Max < 1400 MB** | `tests/unit/test_cognitive_controller.py` | max_usage_mb ≤ 1400.0 | `policy/observability-slo.yaml`<br>`thresholds.slos.system_resources[name=memory-usage]` | Blocking |
| **Moral Filter Stability** | `tests/property/test_moral_filter_properties.py` | threshold ∈ [0.30, 0.90]<br>drift ≤ 0.15 | `policy/observability-slo.yaml`<br>`thresholds.slos.cognitive_engine[name=moral-filter-stability]` | Blocking |
| **Memory Corruption Rate = 0** | `tests/property/test_pelm_phase_behavior.py` | corruption_rate = 0.0% | `policy/observability-slo.yaml`<br>`thresholds.slos.cognitive_engine[name=memory-operations]` | Blocking |

## Test Design Principles

### 1. Determinism

**All SLO tests MUST be deterministic and reproducible.**

- **Use fixed seeds**: `np.random.seed(42)` for any randomness
- **Avoid external dependencies**: No network calls, no real LLM APIs
- **Control timing**: Use predictable operations, not wall-clock time
- **Warm-up phase**: Run warm-up iterations before measurement

Example:
```python
def test_memory_stays_stable_over_time():
    """Verify memory usage doesn't grow unbounded."""
    np.random.seed(42)  # Deterministic
    controller = CognitiveController()

    # Warm-up: 3 iterations
    for _ in range(3):
        controller.process_event(test_event)

    # Measure initial growth
    initial_mem = controller.get_memory_usage()
    for _ in range(100):
        controller.process_event(test_event)
    mid_mem = controller.get_memory_usage()
    initial_growth = mid_mem - initial_mem

    # Measure later growth
    for _ in range(100):
        controller.process_event(test_event)
    final_mem = controller.get_memory_usage()
    later_growth = final_mem - mid_mem

    # Allow noise tolerance
    assert later_growth <= initial_growth * 2 + NOISE_TOLERANCE_MB
```

### 2. Noise Tolerance

**Account for allocator noise and system variance.**

- **Memory tests**: Allow `noise_tolerance_mb = 5.0` MB variance
- **Latency tests**: Use percentiles (p95, p99) not averages
- **Sample size**: Collect ≥ 5 samples for statistical significance

### 3. Single Source of Truth

**Read SLO thresholds from policy files, not hardcoded values.**

```python
from mlsdm.policy.loader import load_policy_bundle

def test_readiness_latency():
    policy = load_policy_bundle()
    readiness = next(
        endpoint
        for endpoint in policy.observability_slo.thresholds.slos.api_endpoints
        if endpoint.name == "health-readiness"
    )
    target = readiness.ci_thresholds.p95_latency_ms

    # Run test
    latencies = measure_readiness_latency(n=100)
    p95 = np.percentile(latencies, 95)

    assert p95 < target, f"P95 latency {p95:.1f}ms exceeds target {target}ms"
```

### 4. Fail Fast

**Don't retry flaky tests. Fix the root cause.**

- **No `@pytest.mark.flaky`**
- **No retries on failure**
- **No conditional skips based on environment**

If a test is flaky, it indicates:
1. Test design issue (not deterministic)
2. Code issue (race condition, memory leak)
3. SLO target issue (too aggressive)

Fix the root cause, don't mask it.

## SLO Tiers

### Tier 1: Blocking (CI Gate)

Must pass on every PR. Failure blocks merge.

- API health endpoint latency
- Memory leak detection
- Core system invariants

### Tier 2: Advisory (Warning)

Tracked but don't block merge. Generate alerts.

- Event processing latency
- CPU usage
- Throughput targets

### Tier 3: Monitoring Only

Tracked in production, not enforced in CI.

- Error budgets
- Availability
- Business metrics

## Running SLO Tests

### Local Development

```bash
# Run fast SLO tests (< 2 minutes)
pytest tests/perf/ -v -m "benchmark and not slow"
pytest tests/resilience/ -v -m "not slow"

# Run memory leak tests
pytest tests/unit/test_cognitive_controller.py::TestCognitiveControllerMemoryLeak -v

# Run all SLO tests
pytest tests/perf/ tests/resilience/ -v
```

### Local Policy Validation

```bash
python -m mlsdm.policy.check
```

This ensures the YAML contract, export mapping, and enforcement gates stay aligned with SLO test expectations.

### CI/CD

**On every PR:**
- Fast SLO tests (< 2 min total)
- Memory leak tests
- Core invariants

**Nightly:**
- Full SLO test suite
- Extended load tests
- Chaos engineering tests

## Interpreting Results

### Green: SLO Met ✅

```
P95 latency: 95ms (target: 120ms) ✓
Memory growth: 1.2x (target: ≤ 2x) ✓
```

**Action:** None required. System is healthy.

### Yellow: Approaching SLO Limit ⚠️

```
P95 latency: 115ms (target: 120ms) ⚠
Memory growth: 1.8x (target: ≤ 2x) ⚠
```

**Action:** Investigate before it becomes red. Optimize if possible.

### Red: SLO Violated ❌

```
P95 latency: 135ms (target: 120ms) ✗
Memory growth: 2.5x (target: ≤ 2x) ✗
```

**Action:**
1. Investigate root cause
2. Profile and optimize
3. Consider adjusting SLO target if it's too aggressive
4. Document findings in PR

## Updating SLOs

### Process

1. **Propose change** in `policy/observability-slo.yaml`
2. **Justify change** with data and analysis
3. **Update tests** to use new target
4. **Run full suite** to verify
5. **Document** in PR description

### Valid Reasons to Change SLO

- **Tighten:** System improvements allow stricter target
- **Loosen:** SLO too aggressive, causing false positives
- **New SLO:** Adding monitoring for new feature

### Invalid Reasons

- ❌ "Test is flaky" - Fix the test
- ❌ "Sometimes fails" - Investigate root cause
- ❌ "Takes too long" - Optimize test, not SLO

## Debugging SLO Failures

### Memory Leak

```bash
# Run with memory profiling
pytest tests/unit/test_cognitive_controller.py::TestCognitiveControllerMemoryLeak -v --profile-mem

# Check for unbounded caches
grep -r "cache" src/mlsdm/core/
grep -r "lru_cache" src/mlsdm/
```

**Common causes:**
- Unbounded caches
- Event listeners not removed
- Circular references
- Logging handlers accumulating

### High Latency

```bash
# Profile code
pytest tests/perf/test_slo_api_endpoints.py --profile

# Check for blocking operations
grep -r "sleep\|time.sleep" src/mlsdm/
```

**Common causes:**
- Synchronous I/O
- Expensive computations in hot path
- Inefficient data structures
- Lock contention

### Flaky Test

```bash
# Run test 100 times
for i in {1..100}; do
    pytest tests/perf/test_slo_api_endpoints.py::test_readiness_latency || echo "Failed on run $i"
done
```

**Common causes:**
- Non-deterministic random seeds
- Timing-dependent assertions
- External dependencies
- System state not reset between runs

## Metrics & Dashboards

### Grafana Dashboards

- **SLO Overview**: Real-time SLO compliance
- **Error Budget**: Burn rate and remaining budget
- **Latency Heatmap**: P50, P95, P99 over time

### Prometheus Queries

```promql
# P95 readiness latency
histogram_quantile(0.95,
  rate(process_event_latency_seconds_bucket{endpoint="/health/readiness"}[5m])
)

# Memory growth rate
rate(memory_usage_bytes[1h])

# Error rate
rate(rejected_events_count[5m]) / rate(total_events_processed[5m])
```

## Compliance & Audit

### Monthly SLO Review

- Review all SLO targets
- Analyze trends and violations
- Adjust targets if needed
- Document decisions

### Quarterly SLO Audit

- Validate SLO test coverage
- Check for missing SLOs
- Update this protocol if needed
- Present findings to team

## References

- **Policy:** `policy/observability-slo.yaml`
- **Spec:** `SLO_SPEC.md`
- **Tests:** `tests/perf/`, `tests/resilience/`
- **Runbook:** `RUNBOOK.md`
- **Observability:** `OBSERVABILITY_GUIDE.md`

---

**Changelog:**

- **2025-12-07:** v1.0.0 - Initial version defining SLO validation protocol
