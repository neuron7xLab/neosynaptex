# MFN Test Health Report — 2025-11-30 (Updated 2025-12-01)

## Executive Summary

**Date:** 2025-12-01 (Updated)  
**CI Status:** ✅ All Passing  
**Tests:** 1031 passed, 3 skipped  
**Coverage:** 87% overall (+3% from previous)

This report documents the test health analysis for MyceliumFractalNet v4.1 based on today's CI runs.

---

## 1. CI Run Summary (2025-11-30)

### Run ID: 19803646754 (main branch)

| Job | Status | Duration | Details |
|-----|--------|----------|---------|
| lint | ✅ success | ~3 min | ruff + mypy passed |
| test (3.10) | ✅ success | ~3 min | 758 passed, 1 skipped |
| test (3.11) | ✅ success | ~2.5 min | 758 passed, 1 skipped |
| test (3.12) | ✅ success | ~3 min | 758 passed, 1 skipped |
| validate | ✅ success | ~2.5 min | CLI validation passed |
| benchmark | ✅ success | ~2.5 min | 8/8 benchmarks passed |
| scientific-validation | ✅ success | ~2 min | 11/11 validations passed |

**Total CI Duration:** ~4 minutes (end-to-end)

---

## 2. Failing & Flaky Tests

### 2.1 Failed Tests
| Test | File | Status | Notes |
|------|------|--------|-------|
| — | — | — | No failing tests |

### 2.2 Skipped Tests
| Test | File | Reason |
|------|------|--------|
| test_mfn_performance.py (all) | tests/perf/ | "Benchmark tests are for manual profiling only" |

### 2.3 Potential Flaky Tests
No flaky tests detected (consistent results across all Python versions).

---

## 3. Warnings & Near-Threshold Metrics

### 3.1 Test Warnings (1585 total)
Most warnings are from:
- **DeprecationWarnings** from hypothesis/pytest internals
- **RuntimeWarnings** from numerical operations (expected in scientific code)
- **UserWarnings** from torch (GPU availability checks)

No actionable warnings related to MFN code.

### 3.2 Near-Threshold Scientific Values
| Metric | Computed | Expected | Tolerance | Status |
|--------|----------|----------|-----------|--------|
| Fractal dimension | 1.762±0.008 | 1.585 | 0.5 | ⚠️ 0.177 error (within tolerance) |
| Cl- Nernst potential | -90.9 mV | -89.0 mV | 10 mV | ✅ OK |
| Ca2+ Nernst potential | 101.5 mV | 102.0 mV | 20 mV | ✅ OK |

---

## 4. Coverage & Gaps

### 4.1 Overall Coverage: 87% (+3% from 2025-11-30)

### 4.2 Low-Coverage Modules (<70%)
| Module | Coverage | Missing Lines | Priority |
|--------|----------|---------------|----------|
| `experiments/generate_dataset.py` | 62% | CLI/main, exception handlers | MEDIUM |

### 4.3 Well-Covered Modules (>90%)
| Module | Coverage |
|--------|----------|
| `__init__.py` | 100% |
| `analytics/__init__.py` | 100% |
| `analytics/fractal_features.py` | 100% |
| `core/__init__.py` | 100% |
| `core/nernst.py` | 100% |
| `core/turing.py` | 100% |
| `core/fractal.py` | 100% |
| `core/types.py` | 100% |
| `core/stability.py` | 100% |
| `core/stdp.py` | 100% |
| `config.py` | 77% (edge cases tested) |
| `types/*.py` | 95-100% |
| `model.py` | 91% |
| `integration/schemas.py` | 100% |
| `integration/adapters.py` | 100% |

---

## 5. Slowest Tests (Top 25)

| Test | Duration | Notes |
|------|----------|-------|
| `test_nernst_equation_properties` | 2.39s | Hypothesis property test |
| `test_validate_minimal_latency` | 1.23s | API latency test |
| `test_xor_problem_convergence` | 0.94s | Training convergence |
| `test_rapid_fire_requests` | 0.57s | Stress test |
| `test_lyapunov_negative_invariant` | 0.47s | Stability check |
| `test_ifs_always_finite_property` | 0.43s | Hypothesis test |
| `test_validate_cli_vs_api_consistency` | 0.43s | Integration test |
| `test_model_stability_1000_steps` | 0.39s | Stability smoke |

All tests complete within reasonable time (<3s).

---

## 6. Hidden Issues Analysis

### 6.1 xfail/skip Markers
| File | Marker | Reason |
|------|--------|--------|
| `tests/perf/test_mfn_performance.py` | `@pytest.mark.skip` | Manual profiling tests |
| `tests/integration/test_critical_pipelines.py` | `@pytest.mark.skipif` | Conditional (pandas/fastapi) |

### 6.2 Weak Assertions Found
- `tests/e2e/test_mfn_end_to_end.py:pass` — Silent skip when pandas unavailable

### 6.3 Broad Exception Handlers in Code
| File | Location | Risk |
|------|----------|------|
| `integration/metrics.py` | Line ~68 | `except Exception` — may mask errors |
| `integration/logging_config.py` | Line ~142 | `except Exception` — error suppression |
| `pipelines/scenarios.py` | Multiple | Broad exception handling |
| `experiments/generate_dataset.py` | Multiple | Dataset generation error handling |

### 6.4 TODO/FIXME in Tests
None found.

---

## 7. Benchmark Results (Today)

| Benchmark | Value | Target | Status |
|-----------|-------|--------|--------|
| Forward pass latency | 0.22 ms | <10 ms | ✅ |
| Forward pass (batch=128) | 0.29 ms | <50 ms | ✅ |
| Field simulation (64x64, 100 steps) | 19.08 ms | <100 ms | ✅ |
| Fractal dimension estimation | 0.22 ms | <50 ms | ✅ |
| Training step | 1.68 ms | <20 ms | ✅ |
| Peak memory usage | 0.24 MB | <500 MB | ✅ |
| Inference throughput | 264,031 samples/sec | >1,000 | ✅ |
| Model initialization | 0.50 ms | <100 ms | ✅ |

All benchmarks **significantly exceed targets** (performance headroom: 10-100x).

---

## 8. Scientific Validation Results (Today)

| Test | Expected | Computed | Status |
|------|----------|----------|--------|
| K+ Nernst (mammalian) | -89.0 mV | -89.0 mV | ✅ |
| Na+ Nernst (mammalian) | 66.0 mV | 66.6 mV | ✅ |
| Cl- Nernst (mammalian) | -89.0 mV | -90.9 mV | ✅ |
| Ca2+ Nernst (mammalian) | 102.0 mV | 101.5 mV | ✅ |
| K+ Nernst (squid, 18.5°C) | -75.0 mV | -75.3 mV | ✅ |
| Na+ Nernst (squid) | 55.0 mV | 54.7 mV | ✅ |
| Cl- Nernst (squid) | -60.0 mV | -59.7 mV | ✅ |
| RT/F constant | 26.730 mV | 26.712 mV | ✅ |
| Fractal dimension | 1.585 | 1.762±0.008 | ✅ (within tolerance) |
| Membrane potential range | [-95, 40] mV | [-95, 40] mV | ✅ |
| Turing pattern formation | >1e-6 V | 0.002219 V | ✅ |

**Result: 11/11 scientific validations passed**

---

## 9. Recommendations

### 9.1 High Priority
1. ~~**Add tests for `core/stability.py`** — 40% coverage (missing `compute_stability_metrics`)~~ ✅ DONE: Tests added in `tests/core/test_stability.py`
2. ~~**Add tests for `core/stdp.py`** — 37% coverage (missing `compute_weight_update` edge cases)~~ ✅ DONE: Tests added in `tests/core/test_stdp_edge_cases.py`
3. ~~**Create test data fixtures** — No synthetic data files exist in `tests/data/`~~ ✅ DONE: `tests/data/edge_cases.json`, `tests/data/sample_features.json`

### 9.2 Medium Priority
1. **Improve `config.py` coverage** — Many environment-specific code paths untested
2. **Add edge case tests for `experiments/generate_dataset.py`**
3. **Document near-threshold values** — Fractal dimension has 11% error vs expected

### 9.3 Low Priority
1. **Consider removing/refactoring broad exception handlers**
2. **Add integration tests for rate limiting under load**
3. **Convert manual performance tests to automated regression tests**

---

## 10. Action Items for This PR

- [x] Generate this test health report
- [x] Add tests for `core/stability.py` (`compute_stability_metrics`) — see `tests/core/test_stability.py`
- [x] Add tests for `core/stdp.py` edge cases — see `tests/core/test_stdp_edge_cases.py`
- [x] Create minimal test data fixtures in `tests/data/` — see `edge_cases.json`, `sample_features.json`
- [x] Add benchmark assertions with documented thresholds — see `tests/perf/test_mfn_performance.py` (baselines from MFN_PERFORMANCE_BASELINES.md, +20% tolerance)
- [x] Update `TECHNICAL_AUDIT.md` with today's findings
- [x] Update `MFN_PERFORMANCE_BASELINES.md` with today's metrics — see Section 8

---

*Report generated: 2025-11-30*  
*CI Run: 19803646754*  
*Branch: main*
