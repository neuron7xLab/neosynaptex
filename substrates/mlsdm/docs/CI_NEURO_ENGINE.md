# CI - Neuro Cognitive Engine: Technical Specification

**Version**: 2.0
**Last Updated**: December 11, 2025
**Status**: See [status/READINESS.md](status/READINESS.md) (not yet verified)

## Overview

The Neuro Cognitive Engine CI pipeline is the primary quality gate for MLSDM. It ensures code quality, security, performance, and cognitive safety through comprehensive automated checks.

## Pipeline Architecture

### Workflow File
`.github/workflows/ci-neuro-cognitive-engine.yml`

### Trigger Conditions
- **Push**: To `main` and `feature/*` branches
- **Pull Request**: To `main` and `feature/*` branches
- **Estimated Duration**:
  - With cache hits (typical): 8-12 minutes
  - Cold cache (first run or cache miss): 15-20 minutes

## CI Jobs

### 1. Lint and Type Check
**Purpose**: Static code quality verification
**Duration**: ~2 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + dev extras)
4. Run `ruff check src tests`
5. Run `mypy src/mlsdm`

**Success Criteria**:
- Zero ruff violations
- Zero mypy type errors
- Exit code 0

**Local Reproduction**:
```bash
ruff check src tests
mypy src/mlsdm
```

---

### 2. Security Vulnerability Scan
**Purpose**: Dependency security audit
**Duration**: ~2 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install pip-audit and requirements.txt
4. Run `pip-audit --requirement requirements.txt --progress-spinner=off`

**Success Criteria**:
- Zero known vulnerabilities in project dependencies
- Exit code 0

**Important Notes**:
- Audits **only** requirements.txt to avoid false positives from system packages
- System packages (configobj, twisted) are intentionally excluded
- Changed from `--strict` to `--requirement requirements.txt` in Q4 2025

**Local Reproduction**:
```bash
pip install pip-audit
pip-audit --requirement requirements.txt --progress-spinner=off
```

---

### 3. Test Matrix (Python 3.10 & 3.11)
**Purpose**: Cross-version compatibility testing
**Duration**: ~8 minutes per version
**Python Versions**: 3.10, 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python (matrix version) with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `pytest -q --ignore=tests/load`

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1` - Disable rate limiting for testing
- `LLM_BACKEND=local_stub` - Use stub LLM backend

**Success Criteria**:
- All tests pass on both Python versions
- No compatibility issues
- Exit code 0

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest -q --ignore=tests/load
```

---

### 4. Coverage Gate ⚡ NEW
**Purpose**: Enforce code coverage standards
**Duration**: ~10 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing --cov-fail-under=75 --ignore=tests/load -v`
5. Upload coverage.xml as artifact

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1`
- `LLM_BACKEND=local_stub`

**Success Criteria**:
- Coverage ≥ 75% on src/mlsdm (current evidence: ~80.04%)
- Exit code 0

**Note**: Threshold set at 75% to match the committed evidence gate. The gate rises only after sustained headroom is demonstrated.

**Artifacts**:
- `coverage.xml` (90 day retention)

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing \
  --cov-fail-under=75 --ignore=tests/load -v
```

---

### 5. End-to-End Tests
**Purpose**: Integration testing across full system
**Duration**: ~3 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `pytest tests/e2e -v -m "not slow" --tb=short`

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1`
- `LLM_BACKEND=local_stub`

**Success Criteria**:
- All 68 E2E tests pass
- Exit code 0

**Test Categories**:
- Happy path scenarios
- Toxic rejection flows
- Aphasia detection/repair
- Memory phase rhythms
- Metrics endpoints
- Observability pipeline

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/e2e -v -m "not slow" --tb=short
```

---

### 6. Effectiveness Validation
**Purpose**: Validate cognitive system effectiveness metrics
**Duration**: ~4 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `python scripts/run_effectiveness_suite.py --validate-slo`
5. Upload effectiveness reports as artifacts

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1`
- `LLM_BACKEND=local_stub`

**Success Criteria**:
- SLO validation passes
- Effectiveness metrics within acceptable ranges
- Exit code 0

**Artifacts**:
- `reports/effectiveness_snapshot.json` (90 day retention)
- `reports/EFFECTIVENESS_SNAPSHOT.md` (90 day retention)

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  python scripts/run_effectiveness_suite.py --validate-slo
```

---

### 7. Performance Benchmarks (SLO Gate)
**Purpose**: Enforce performance SLO requirements
**Duration**: ~3 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `pytest benchmarks/test_neuro_engine_performance.py -v -s --tb=short`
5. Extract P95 latency metrics with accurate timestamp ⚡ FIXED
6. Validate against SLO thresholds
7. Generate benchmark summary
8. Upload benchmark results as artifacts

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1`
- `LLM_BACKEND=local_stub`

**SLO Thresholds** (from SLO_SPEC.md):
- Pre-flight P95 latency: < 20ms
- End-to-end P95 latency: < 500ms
- Availability: ≥ 99.9% (tracked in production)

**Success Criteria**:
- All benchmark tests pass
- P95 latencies within SLO
- "SLO met" message present in output
- Exit code 0

**Performance Regression Check** (PR only):
- ❌ Regression: P95 > 500ms (fails build)
- ⚠️ Warning: P95 > 400ms (80% of SLO)
- ✅ OK: P95 < 400ms

**Timestamp Fix** ⚡ Q4 2025:
- Changed from shell `$(date -u +%Y-%m-%dT%H:%M:%SZ)` (treated as literal string, not executed)
- To Python `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`
- Shell command in Python string was never executed; now using proper Python datetime
- Ensures accurate benchmark timestamps

**Artifacts**:
- `benchmark-results.xml` (JUnit format, 90 day retention)
- `benchmark-output.txt` (raw output, 90 day retention)
- `benchmark-metrics.json` (structured metrics, 90 day retention)

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest benchmarks/test_neuro_engine_performance.py -v -s --tb=short
```

---

### 8. Cognitive Safety Evaluation
**Purpose**: Validate neuro-cognitive safety properties
**Duration**: ~2 minutes
**Python Version**: 3.11
**Caching**: ✅ Enabled
**Continue on Error**: ✅ Yes (non-blocking)

**Steps**:
1. Checkout code
2. Set up Python with pip cache
3. Install dependencies (requirements.txt + test extras)
4. Run `pytest tests/eval/test_sapolsky_suite.py -v`
5. Run `python examples/run_sapolsky_eval.py --output sapolsky_eval_results.json --verbose` (continue-on-error)
6. Upload evaluation results as artifacts

**Environment Variables**:
- `DISABLE_RATE_LIMIT=1`
- `LLM_BACKEND=local_stub`

**Success Criteria**:
- All 14 Sapolsky suite tests pass
- Full evaluation may fail without blocking CI
- Continue-on-error allows pipeline to proceed

**Test Categories**:
- Coherence stress testing
- Topic drift detection
- Moral filter validation
- Grammar and UG testing
- Baseline comparison

**Artifacts**:
- `sapolsky_eval_results.json` (90 day retention)

**Why Continue-on-Error?**:
The full Sapolsky evaluation (`run_sapolsky_eval.py`) may require specific configurations or baselines that aren't available in CI. The core test suite (`test_sapolsky_suite.py`) must pass, but the full evaluation is informational.

**Local Reproduction**:
```bash
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/eval/test_sapolsky_suite.py -v

DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  python examples/run_sapolsky_eval.py --output sapolsky_eval_results.json --verbose
```

---

### 9. All CI Checks Passed (Gate)
**Purpose**: Aggregate gate requiring all critical jobs
**Duration**: < 1 minute
**Depends On**: lint, security, test, coverage, e2e-tests, effectiveness-validation, benchmarks

**Important Notes**:
- **Does NOT** depend on `neuro-engine-eval` (which has continue-on-error)
- This is the final gate that must pass for PR merge
- If this job is green, all critical quality gates have passed

**Success Criteria**:
- All dependent jobs completed successfully
- Exit code 0

## Performance Optimizations

### Pip Caching ⚡ Q4 2025
All jobs now use pip caching via `actions/setup-python@v5`:

```yaml
- name: Set up Python 3.11
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
    cache-dependency-path: |
      requirements.txt
      pyproject.toml
```

**Impact**:
- Dependency installation: 2-3 minutes → 10-20 seconds (cache hit)
- Total pipeline: 15-20 minutes → 8-12 minutes (cache hit)
- Cache hit rate: Expected >80%

### Cache Invalidation
Cache is automatically invalidated when:
- `requirements.txt` changes
- `pyproject.toml` changes
- Python version changes
- GitHub Actions runner image updates

## Environment Variables

### Required for All Test Jobs
```bash
DISABLE_RATE_LIMIT=1    # Disable rate limiting in tests
LLM_BACKEND=local_stub  # Use stub LLM (no real API calls)
```

### Optional (for debugging)
```bash
PYTEST_VERBOSE=1        # Extra verbose output
OTEL_SDK_DISABLED=true  # Disable OpenTelemetry (faster)
```

## Artifact Retention

All artifacts are retained for **90 days**:
- `coverage-report` (coverage.xml)
- `effectiveness-snapshot` (JSON + MD)
- `benchmark-results-py3.11` (XML, txt, JSON)
- `sapolsky-eval-results` (JSON)

Access artifacts from workflow run page in GitHub Actions.

## Quality Metrics Enforced

| Metric | Target | Job |
|--------|--------|-----|
| Ruff violations | 0 | lint |
| Mypy errors | 0 | lint |
| Security vulnerabilities | 0 | security |
| Code coverage | ≥75% (current evidence: ~80.04%) | coverage |
| E2E tests | 68/68 pass | e2e-tests |
| Pre-flight P95 latency | <20ms | benchmarks |
| End-to-end P95 latency | <500ms | benchmarks |
| Sapolsky tests | 14/14 pass | neuro-engine-eval |

## Troubleshooting

### Common Issues

#### Coverage Job Fails
```bash
# Run locally to debug
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest --cov=src/mlsdm --cov-report=term-missing \
  --cov-fail-under=75 --ignore=tests/load -v
```

#### Security Scan False Positives
If system packages are flagged:
- Ensure using `--requirement requirements.txt` (not `--strict`)
- System packages should not be audited

#### Benchmark Regression
If P95 > 500ms:
- Check for performance-impacting changes
- Review benchmark output logs in artifacts
- Compare with baseline metrics

#### Cache Miss Issues
If installation is slow:
- Check if `requirements.txt` or `pyproject.toml` changed
- Verify `cache: 'pip'` is present in setup-python step
- Check GitHub Actions cache status

## Local CI Simulation

Run full CI pipeline locally:

```bash
#!/bin/bash
# Full local CI simulation

set -e  # Exit on error

echo "=== 1. Lint & Type Check ==="
ruff check src tests
mypy src/mlsdm

echo "=== 2. Security Scan ==="
pip install pip-audit
pip-audit --requirement requirements.txt --progress-spinner=off

echo "=== 3. Tests (Python 3.11 only) ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest -q --ignore=tests/load

echo "=== 4. Coverage ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest --cov=src/mlsdm --cov-report=term-missing \
  --cov-fail-under=65 --ignore=tests/load -v

echo "=== 5. E2E Tests ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/e2e -v -m "not slow" --tb=short

echo "=== 6. Effectiveness Validation ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  python scripts/run_effectiveness_suite.py --validate-slo

echo "=== 7. Benchmarks ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest benchmarks/test_neuro_engine_performance.py -v -s --tb=short

echo "=== 8. Cognitive Safety Eval ==="
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/eval/test_sapolsky_suite.py -v

echo ""
echo "✅ All CI checks passed locally!"
```

Save as `scripts/run_local_ci.sh` and execute:
```bash
chmod +x scripts/run_local_ci.sh
./scripts/run_local_ci.sh
```

## Version History

### v2.0 (December 2025) - Q4 Hardening
- ✅ Added pip caching to all jobs
- ✅ Fixed security scan to use `--requirement requirements.txt`
- ✅ Fixed timestamp generation in benchmark metrics
- ✅ Added coverage gate job (75% threshold, aligned with `coverage_gate.sh` and CI)
- ✅ Verified Python 3.10/3.11 compatibility
- ✅ Updated all-ci-passed gate logic
- ✅ Comprehensive documentation updates

### v1.0 (November 2025) - Initial Implementation
- Initial workflow structure
- Basic jobs: lint, security, test, e2e, effectiveness, benchmarks
- Sapolsky evaluation integration

## References

- [CI_GUIDE.md](../CI_GUIDE.md) - General CI/CD guide
- [SLO_SPEC.md](../SLO_SPEC.md) - Performance SLO specifications
- [TESTING_GUIDE.md](../TESTING_GUIDE.md) - Testing best practices
- [SECURITY_POLICY.md](../SECURITY_POLICY.md) - Security policies

---

**Maintainer**: neuron7x
**Contact**: [GitHub Issues](https://github.com/neuron7xLab/mlsdm/issues)
**License**: MIT
