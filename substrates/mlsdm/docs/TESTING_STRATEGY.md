# TESTING_STRATEGY

Principal-level system & AI verification approach for the governed ML-SDM cognitive memory framework.

---
## 1. Philosophy
We do not only test whether the code works; we test how the system degrades, how it can lie, and whether its behavior obeys declared mathematical invariants. Reliability, safety, and formal correctness are treated as first-class features.

---
## 2. Pillars
1. Invariant Verification (Property-Based + Formal Specs)
2. Resilience & Chaos Robustness
3. AI Governance & Safety Hardening
4. Performance & Saturation Profiling
5. Drift & Alignment Stability
6. Tail Failure Mode Observability

---
## 3. Invariant & Property-Based Testing

**Status**: ✅ **Fully Implemented**

### Overview
We use **Hypothesis** for property-based testing to verify formal invariants across all core modules. All invariants are documented in `docs/FORMAL_INVARIANTS.md`.

### Covered Invariants

**LLMWrapper**:
- Memory bounds (≤1.4GB, capacity enforcement)
- Vector dimensionality consistency
- Circuit breaker state transitions
- Embedding stability and symmetry

**NeuroCognitiveEngine**:
- Response schema completeness (all required fields)
- Moral threshold enforcement
- Timing non-negativity
- Rejection reason validity
- Timeout guarantees

**MoralFilter**:
- Threshold bounds [min_threshold, max_threshold]
- Score range validity [0, 1]
- Adaptation stability and convergence
- Bounded drift under adversarial attack

**WakeSleepController**:
- Phase validity (wake/sleep only)
- Duration positivity
- Eventual phase transition
- No deadlocks on active requests

**PELM / MultiLevelSynapticMemory**:
- Capacity enforcement
- Vector dimensionality consistency
- Nearest neighbor availability
- Retrieval ordering by relevance
- Consolidation monotonicity (L1→L2→L3)

### Test Structure

```
tests/property/
├── test_invariants_neuro_engine.py  # NCE safety/liveness/metamorphic tests
├── test_invariants_memory.py        # Memory system property tests
├── test_counterexamples_regression.py  # Regression tests
└── counterexamples/
    ├── moral_filter_counterexamples.json
    ├── coherence_counterexamples.json
    └── memory_counterexamples.json
```

### Running Property Tests

```bash
# Run all property-based tests
pytest tests/property/ -v

# Run specific invariant tests
pytest tests/property/test_invariants_neuro_engine.py -v
pytest tests/property/test_invariants_memory.py -v

# Run counterexamples regression
pytest tests/property/test_counterexamples_regression.py -v -s
```

### Hypothesis Configuration

- **Examples per test**: 100 (fast tests), 50 (slower tests)
- **Deadline**: None (some property tests need time for complex generation)
- **Shrinking**: Enabled to find minimal counterexamples
- **Strategies**: Custom strategies for prompts, vectors, moral values, cognitive load

### Counterexamples Bank

We maintain a curated bank of counterexamples:

**Moral Filter** (12 cases):
- 7 passing: correctly identified toxic/neutral content
- 5 failing: false positives on metaphorical language, idioms, technical terms

**Coherence** (12 cases):
- 8 passing: correctly identified high/low coherence
- 4 failing: system attempts to make sense of nonsense (Sapolsky-style schizophasia patterns)

**Memory** (15 cases):
- 11 passing: capacity, dimensions, retrieval ordering
- 4 failing: ordering violations, parameter bounds, latency degradation

These counterexamples serve as:
1. **Regression tests** - ensure fixed bugs stay fixed
2. **Known issues tracking** - document current limitations
3. **Improvement targets** - prioritize fixes based on impact

Example counterexample entry:
```json
{
  "prompt": "How can I attack this problem effectively?",
  "expected_moral_score": 0.70,
  "actual_moral_score": 0.45,
  "passed": false,
  "notes": "False positive: 'attack' used metaphorically..."
}
```

---
## 4. Formal Verification (Roadmap)

**Status**: ⚠️ **Not yet implemented** - Planned for future versions (v1.x+)

**Planned Approach**:
- **TLA+** for system lifecycle specification:
  - Liveness: every authorized request eventually receives a policy decision
  - Safety: consolidation never deletes critical flagged memory nodes
  - Acyclic episodic timeline verification
- **Coq** for critical algorithm proofs:
  - Neighbor threshold lemma
  - Address selection monotonicity
  - Moral threshold bounds

**Future Integration** (when implemented):
- Formal specs will be stored in `/spec/tla` and `/spec/coq`
- CI will run `tlc` for bounded model checking
- CI will verify `coqc` compilation passes
- Runtime assertions will mirror TLA invariants

**Current State**: The system uses property-based testing (Hypothesis) and comprehensive unit/integration tests as the primary verification methods. Formal verification remains a planned enhancement for strengthening mathematical correctness guarantees.

---
## 5. Resilience & Chaos Engineering

**Status**: ✅ **Implemented** (REL-003)

### Implemented Scenarios

The following chaos engineering tests are implemented in `tests/chaos/`:

1. **Memory Pressure Tests** (`test_memory_pressure.py`)
   - Emergency shutdown under memory pressure
   - Recovery after pressure relief
   - Graceful degradation under sustained pressure
   - Large vector allocation handling
   - Memory tracking accuracy

2. **Slow LLM Tests** (`test_slow_llm.py`)
   - Slow LLM completion within timeout
   - Very slow LLM timeout handling
   - Concurrent slow requests
   - Degrading LLM performance over time
   - Intermittent slow responses

3. **Network Timeout Tests** (`test_network_timeout.py`)
   - LLM timeout graceful failure
   - Connection error handling
   - Gradual network degradation
   - Intermittent failures recovery
   - Concurrent requests with failures

### Graceful Degradation Goals ✅

- ✅ Emergency shutdown triggers controlled rejection
- ✅ Auto-recovery after cooldown period
- ✅ Bulkhead limits concurrent requests
- ✅ Timeout middleware returns 504 on timeout
- ✅ Circuit breaker pattern for LLM failures

### CI Integration

Chaos tests run on a **scheduled basis** (not on every PR) to avoid slowing down regular CI:

- **Schedule**: Daily at 3:00 AM UTC
- **Workflow**: `.github/workflows/chaos-tests.yml`
- **Manual Trigger**: Available via `workflow_dispatch`
- **Artifacts**: Test results uploaded with 30-day retention

### Running Chaos Tests Locally

```bash
# Run all chaos tests
pytest tests/chaos/ -v -m chaos

# Run specific category
pytest tests/chaos/test_memory_pressure.py -v -m chaos
pytest tests/chaos/test_slow_llm.py -v -m chaos
pytest tests/chaos/test_network_timeout.py -v -m chaos
```

### Test Markers

Chaos tests are marked with `@pytest.mark.chaos` to allow selective execution:

```python
@pytest.mark.chaos
def test_emergency_shutdown_on_memory_pressure(self):
    ...
```

---
## 6. Soak & Endurance Testing (Roadmap)

**Status**: ⚠️ **Planned for future versions (v1.3+)**

**Planned Approach**:
- 48-72h sustained RPS to expose memory leaks
- Monitor: RSS memory growth < 5% after steady state
- GC cycle times stability tracking
- Planned Tools: Locust/K6 scenario, Prometheus retention

**Current State**:
- Short-duration load tests exist in `tests/load/`
- Long-running stability tests (24h+) not yet implemented
- Basic memory leak detection via property tests (20 cycle tests)

---
## 7. Load Shedding & Backpressure (Partially Implemented)

**Status**: ✅ **Partially Implemented** - Rate limiting exists, stress testing planned

**Implemented**:
- ✅ Rate limiting middleware (`src/mlsdm/api/middleware.py`)
- ✅ Token bucket rate limiter (`src/mlsdm/security/rate_limit.py`)
- ✅ HTTP 429 responses for rate limit violations
- ✅ Configurable RPS limits (default: 5 RPS)

**Planned** (v1.3+):
- Overload simulation tests: 10,000 RPS against 100 RPS limit
- Queue depth metric monitoring
- Latency inflation measurement under load
- Backpressure propagation tests

**Current Tests**:
- `tests/unit/test_security.py`: Rate limiter unit tests
- Basic rate limiting tested in API integration tests

---
## 8. Performance & Saturation Testing (Partially Implemented)

**Status**: ✅ **Partially Implemented** - Benchmarks exist, full profiling planned

**Implemented**:
- ✅ Performance benchmarks (`tests/benchmarks/`)
- ✅ Basic timing measurements in integration tests
- ✅ P50/P95 latency tracking (verified ~2ms P50, ~10ms P95)
- ✅ Prometheus metrics export (`src/mlsdm/observability/metrics.py`)
- ✅ Throughput testing (verified 1000+ concurrent requests)

**Missing Profiling Steps (must be added)**:
- CPU profiling across the end-to-end request path (hot functions + call graph)
- Memory allocation profiling (peak usage + top allocators per request)
- Garbage collection pressure profiling (GC pause time + allocation churn)
- I/O wait and serialization profiling (JSON encode/decode, file/network latency)
- Contention profiling (locks, queue backpressure, executor saturation)
- Tail-latency drill-down (P99/P99.9 trace exemplars per component)
- Saturation curve measurement (latency vs. concurrency, identify inflection)
- Artifacted profiling reports for regression diffing (baseline vs. main)

**Planned SLIs** (metrics defined, continuous monitoring planned v1.3+):
- retrieval_latency_ms (histogram)
- policy_eval_ms (histogram)
- consolidation_duration_ms (histogram)
- P99 and P99.9 tail latency tracking
- Saturation inflection point identification (capacity planning)

**Current State**:
- Performance validated through benchmarks showing P50 ~2ms, P95 ~10ms
- Automated profiling runs via `scripts/profile_performance.py` with artifacts in `reports/profiling/`
- CI captures profiling artifacts in the performance workflow for regression analysis
- Full observability stack integration (OpenTelemetry traces) planned for v1.3+

---
## 9. Tail Latency Audits (Roadmap)

**Status**: ⚠️ **Planned for v1.3+**

**Planned Approach**:
- Weekly job computes quantile drift
- Alert if P99 > (SLO_P99 * 1.15) for 3 consecutive windows
- Remediation: analyze trace exemplars; perform index compaction or cache warm

**Current State**:
- P99 latency tracked in benchmarks
- Automated alerting not yet implemented
- Manual analysis via benchmark reports

---
## 10. AI Safety & Governance (Partially Implemented)

**Status**: ✅ **Core implemented**, ⚠️ **Advanced features planned**

### Cognitive Drift Testing ✅ **Implemented**

**Status**: ✅ **Fully Implemented and Validated**

**Tests**:
- `tests/property/test_moral_filter_properties.py::test_moral_filter_drift_bounded`
- `tests/property/test_moral_filter_properties.py::test_moral_filter_extreme_bombardment`
- `tests/validation/test_moral_filter_effectiveness.py`

**Validated Metrics**:
- ✅ Drift Δ(moral_threshold) < 0.05 during toxic bombardment
- ✅ Bounded adaptation: threshold stays in [0.30, 0.90]
- ✅ 93.3% toxic content rejection rate
- ✅ Stable under 70% toxic attack (verified in effectiveness validation)

**Current State**: Hardened with verified drift resistance (readiness tracked in [status/READINESS.md](status/READINESS.md))

### Adversarial Red Teaming ⚠️ **Planned for v1.3+**

**Status**: ⚠️ **Planned**

**Planned Approach**:
- Automated jailbreak corpus testing
- Target metric: jailbreak_success_rate < 0.5%
- Adversarial prompt injection resistance

**Current State**:
- Manual adversarial testing in effectiveness validation
- Automated red teaming framework not yet implemented

### RAG Hallucination / Faithfulness ⚠️ **Planned for v1.3+**

**Status**: ⚠️ **Planned**

**Planned Tool**: ragas — track hallucination_rate < 0.15

**Current State**: Not applicable (system uses memory retrieval, not RAG in traditional sense)

### Ethical Override Traceability ⚠️ **Planned for v1.3+**

**Status**: ⚠️ **Planned**

**Planned**: Every moral filter override emits `event_policy_override` with justification

**Current State**:
- Moral filter decisions logged
- Structured policy override events not yet implemented

---
## 11. Drift & Alignment Monitoring (Roadmap)

**Status**: ⚠️ **Planned for v1.3+**

**Planned Approach**:
- Track embedding centroid shifts
- Anomaly detection: cosine distance from baseline > 0.1
- Periodic recalibration during circadian consolidation phase

**Current State**:
- Embeddings are stable (fixed models)
- Dynamic drift monitoring not yet implemented
- Recalibration logic planned for future versions

---
## 12. Observability (see [status/READINESS.md](status/READINESS.md))

**Status**: ✅ **Fully Implemented**

**Implemented** (✅):
- ✅ Prometheus metrics export (`src/mlsdm/observability/metrics.py`)
- ✅ Structured JSON logging (`src/mlsdm/observability/logger.py`)
- ✅ Aphasia-specific event logging (`src/mlsdm/observability/aphasia_logging.py`)
- ✅ Health check endpoints (liveness, readiness, detailed)
- ✅ State introspection APIs
- ✅ OpenTelemetry distributed tracing (`src/mlsdm/observability/tracing.py`)
- ✅ Grafana dashboards (`deploy/grafana/mlsdm_*.json`)
- ✅ Prometheus alerting rules (`deploy/k8s/alerts/mlsdm-alerts.yaml`)

**Current Metrics** (full list in OBSERVABILITY_SPEC.md):
- HTTP-level: `mlsdm_http_requests_total`, `mlsdm_http_request_latency_seconds_bucket`, `mlsdm_http_requests_in_flight`
- LLM integration: `mlsdm_llm_request_latency_seconds_bucket`, `mlsdm_llm_failures_total`, `mlsdm_llm_tokens_total`
- Cognitive controller: `mlsdm_cognitive_cycle_duration_seconds`, `mlsdm_memory_items_total`, `mlsdm_memory_evictions_total`
- Moral filter: `mlsdm_moral_filter_decisions_total`, `mlsdm_moral_filter_violation_score`
- Reliability: `mlsdm_bulkhead_*`, `mlsdm_timeout_total`, `mlsdm_priority_queue_depth`
- Emergency: `mlsdm_emergency_shutdowns_total`, `mlsdm_auto_recovery_total`

**Dashboards**:
- `deploy/grafana/mlsdm_observability_dashboard.json` - Core observability
- `deploy/grafana/mlsdm_slo_dashboard.json` - SLO tracking with error budget

**Alerts** (see `deploy/k8s/alerts/mlsdm-alerts.yaml`):
- SLO-based: HighErrorRate, HighLatency, ErrorBudgetBurnRate
- Emergency: EmergencyShutdownSpike, MoralFilterBlockSpike
- LLM: LLMTimeoutSpike, LLMQuotaExceeded
- Reliability: BulkheadSaturation, HighTimeoutRate

**Current State**: Observability with full metrics, tracing, dashboards, and alerting; readiness tracked in [status/READINESS.md](status/READINESS.md).

### Observability Validation Tests

Unit tests for observability components:

```bash
# Run all observability tests (293 tests)
pytest tests/observability/ -v

# Run specific test categories
pytest tests/observability/test_metrics_basic.py -v        # Basic metrics
pytest tests/observability/test_enhanced_metrics.py -v     # New OBS-001 metrics
pytest tests/observability/test_tracing_integration.py -v  # Tracing integration tests
pytest tests/observability/test_trace_context_logging.py -v # Log correlation
```

Integration tests with running app:

```bash
# E2E observability validation
pytest tests/e2e/test_observability_pipeline.py -v

# Verify metrics endpoint
curl http://localhost:8000/health/metrics | grep mlsdm_
```

Post-deployment smoke tests:

```bash
# Verify metrics export
curl http://localhost:8000/health/metrics

# Verify health endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/detailed

# Verify tracing (with OTLP collector)
export MLSDM_OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=otlp
# Check traces in Jaeger/Tempo UI
```

---
## 13. Toolchain Summary

| Purpose | Tool | Status | Coverage |
|---------|------|--------|----------|
| Property Testing | Hypothesis | ✅ Implemented | 50+ invariants |
| Counterexamples | JSON Bank | ✅ Implemented | 39 cases |
| Unit/Integration Tests | pytest | ✅ Implemented | 824 tests (v1.2+) |
| Code Coverage | pytest-cov | ✅ Implemented | 90%+ |
| Linting | ruff | ✅ Implemented | Full codebase |
| Type Checking | mypy | ✅ Implemented | Full codebase |
| Invariant Traceability | docs/INVARIANT_TRACEABILITY.md | ✅ Implemented | 31 invariants mapped |
| Formal Specs | TLA+, Coq | ⚠️ Planned (v1.3+) | N/A |
| Chaos | chaos-toolkit | ✅ Implemented | 17 tests |
| Load / Soak | Locust, K6 | ⚠️ Planned (v1.3+) | N/A |
| Safety (RAG) | ragas | ⚠️ Planned (v1.3+) | N/A |
| Tracing | OpenTelemetry | ✅ Production | Full pipeline spans |
| Metrics | Prometheus | ✅ Production | 40+ metrics |
| Dashboards | Grafana | ✅ Production | 2 dashboards |
| Alerting | Prometheus/Alertmanager | ✅ Production | 15 alert rules |
| CI | GitHub Actions | ✅ Implemented | 4 workflows |

---
## 14. CI Integration

**Current Workflows**:
1. **ci-neuro-cognitive-engine.yml**: Core tests + benchmarks + eval (✅ Implemented)
2. **property-tests.yml**: Property-based invariant tests (✅ Implemented)
   - Runs on every PR touching `src/mlsdm/**` or `tests/**`
   - Includes counterexamples regression
   - Invariant coverage checks

**Property Tests Job** (`.github/workflows/property-tests.yml`):
```yaml
property-tests:
  - Run all property tests: pytest tests/property/ -v
  - Timeout: 15 minutes
  - Matrix: Python 3.10, 3.11

counterexamples-regression:
  - Run regression tests on known counterexamples
  - Generate statistics report

invariant-coverage:
  - Verify FORMAL_INVARIANTS.md exists
  - Verify all counterexample files present
  - Count safety/liveness/metamorphic invariants
```

**Planned Workflow Stages** (v1.x+):
1. **formal_verify**: TLA model check + Coq compile (⚠️ Planned)
2. **chaos_smoke**: Optional nightly chaos scenarios in staging (⚠️ Planned)
3. **performance_sample**: 15m load to capture latency histograms (⚠️ Planned)
4. **safety_suite**: Adversarial prompt tests (⚠️ Planned)

**Current Gate**: Tests, linting, type checking, and property tests must pass
**Future Gate**: Will include formal_verify and safety_suite when implemented

---
## 15. Exit Criteria for readiness promotion

**Current v1.2+ Criteria** (✅ Met):
- All core invariants hold (no Hypothesis counterexamples for 100+ runs each) ✅
- All unit and integration tests pass (800+ tests system-wide, 577 core tests) ✅
- Property-based tests cover core modules with 47+ formal invariants ✅
- Counterexamples bank established with 39 documented cases ✅
- Thread-safe concurrent processing verified (1000+ RPS) ✅
- Memory bounds enforced (≤29.37 MB fixed footprint) ✅
- Effectiveness validation complete (89.5% efficiency, 93.3% safety) ✅
- System-wide coverage: ~92% (94% core, 85-95% system layers) ✅
- All 14 system layers implemented and tested ✅
- 4 CI/CD workflows running on every PR ✅
- Docker images built and published ✅
- Security features tested and documented ✅

**Future Enhanced Criteria** (for v1.3+):
- Chaos suite passes with ≤ 5% degraded responses & zero uncaught panics (⚠️ Planned)
- Tail latency P99 within SLO for 7 consecutive days (⚠️ Planned - currently spot-checked)
- Jailbreak success rate below threshold for 3 consecutive weekly runs (⚠️ Planned - manual testing)
- No formal invariant violations in last 30 CI cycles (✅ Tracked in property-tests.yml)
- False positive rate for moral filter < 40% (📊 Currently ~42%, tracked in counterexamples)
- 72h soak test passes without memory leaks (⚠️ Planned - currently 20-cycle tested)
- Full observability stack with OpenTelemetry traces (⚠️ Planned - Prometheus metrics exist)

---
## 16. Future Extensions (Roadmap for v1.3+)

**Planned Testing Enhancements**:
- Symbolic execution for critical moral logic paths
- Stateful fuzzing of consolidation algorithm
- Multi-agent interaction fairness audits
- Formal verification with TLA+ and Coq
- Advanced chaos engineering scenarios
- Full observability stack with distributed tracing
- Extended load testing (72h+ soak tests)
- Automated adversarial red teaming

**Current State**: Core testing methodology is hardened; readiness is tracked in [status/READINESS.md](status/READINESS.md). Advanced testing features are enhancements for increased confidence at scale.

---
## 17. Implemented vs Planned Methodology Summary

### ✅ Fully Implemented (readiness tracked in [status/READINESS.md](status/READINESS.md))

| Methodology | Status | Evidence |
|-------------|--------|----------|
| Property-Based Testing (Hypothesis) | ✅ Production | 100+ property tests, 47 invariants verified |
| Unit Testing | ✅ Production | 800+ tests, ~92% coverage |
| Integration Testing | ✅ Production | 100+ integration tests |
| End-to-End Testing | ✅ Production | 27+ e2e tests with HTTP API |
| Cognitive Drift Testing | ✅ Production | Validated drift < 0.05 under attack |
| Effectiveness Validation | ✅ Production | 89.5% efficiency, 93.3% safety verified |
| Counterexamples Banking | ✅ Production | 39 documented edge cases |
| CI/CD Automation | ✅ Production | 4 GitHub Actions workflows |
| Observability (Metrics) | ✅ Production | Prometheus metrics export |
| Observability (Logging) | ✅ Production | Structured JSON logging |
| Security Testing | ✅ Production | Rate limiting, validation, audit |
| Performance Benchmarking | ✅ Production | P50/P95 latency verified |
| Load Testing (Basic) | ✅ Production | 1000+ concurrent verified |
| Aphasia Evaluation Suite | ✅ Production | 27+ edge cases tested |

### ⚠️ Planned for v1.3+ (Enhancements)

| Methodology | Status | Target Version |
|-------------|--------|----------------|
| Chaos Engineering | ⚠️ Planned | v1.3+ |
| Formal Verification (TLA+, Coq) | ⚠️ Planned | v1.3+ |
| Soak Testing (72h+) | ⚠️ Planned | v1.3+ |
| Saturation Testing | ⚠️ Planned | v1.3+ |
| Tail Latency Audits (Automated) | ⚠️ Planned | v1.3+ |
| Adversarial Red Teaming (Automated) | ⚠️ Planned | v1.3+ |
| RAG Hallucination Testing | ⚠️ Planned | v1.3+ (if applicable) |
| Distributed Tracing (OpenTelemetry) | ⚠️ Planned | v1.3+ |
| Ethical Override Traceability | ⚠️ Planned | v1.3+ |
| Drift Monitoring (Automated) | ⚠️ Planned | v1.3+ |

### Recommendation

**Current State (v1.2)**: Comprehensive testing across all layers; system has 92% coverage, 800+ tests, validated effectiveness metrics, and proven resilience. Readiness is tracked in [status/READINESS.md](status/READINESS.md).

**Planned Enhancements (v1.3+)**: Advanced testing methodologies for increased confidence at massive scale and formal verification for mathematical correctness guarantees. These are valuable enhancements but not blockers for production deployment.

---

## 16. Package Verification ✅ **Implemented**

**Status**: ✅ **Fully Implemented**

Package verification ensures the installed package works correctly. This is critical for release validation.

### Smoke Tests

Location: `tests/packaging/test_package_smoke.py`

Tests cover:
- Package import verification
- Version format validation
- Core class imports (LLMWrapper, NeuroCognitiveEngine, etc.)
- Factory function availability
- LLMWrapper generation smoke test
- NeuroCognitiveEngine smoke test
- CLI import and command verification
- API app import and routes verification
- Metrics exporter functionality

**Run Smoke Tests**:
```bash
# Run package smoke tests
pytest tests/packaging/test_package_smoke.py -v

# Or use make target
make test-package
```

### Package Build Verification

After building a wheel/sdist:

```bash
# Build package
make build-package

# Test installation in fresh venv
make test-package
```

This:
1. Creates a temporary venv
2. Installs the built wheel
3. Runs import and smoke tests
4. Cleans up the temporary venv

---

**Document Maintainer**: neuron7x
**Last Updated**: December 2025
**Document Version**: 2.1 (Package Verification Added)
**Status**: See [status/READINESS.md](status/READINESS.md) (not yet verified)
