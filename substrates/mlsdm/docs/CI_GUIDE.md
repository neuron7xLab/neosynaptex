# CI/CD Configuration Guide

**Understanding and working with MLSDM's CI/CD pipeline**

## Overview

MLSDM uses GitHub Actions for continuous integration and deployment. The CI pipeline is designed to ensure code quality, security, and reliability before changes are merged or released.

## 🔒 Reproducible Dependencies

**IMPORTANT:** The project uses `uv.lock` for reproducible dependency installation across all environments:

- **Lock File:** `uv.lock` pins all dependencies to specific versions
- **Update Lock:** Run `uv lock` after changing `pyproject.toml` dependencies
- **Install from Lock:** Use `uv sync` for reproducible installs matching CI
- **GitHub Actions:** All workflows use pinned versions (@v4, @v5, etc.)

**To reproduce CI environment locally:**
```bash
pip install uv
uv sync
# Now you have the exact same dependencies as CI
```

### Dependency Drift Prevention

The `requirements.txt` file is **GENERATED** from `pyproject.toml` and should not be edited manually. A CI check enforces this:

```bash
# Check for drift (fails if out of sync)
python scripts/ci/export_requirements.py --check

# Regenerate requirements.txt from pyproject.toml
python scripts/ci/export_requirements.py
```

The `dependency-drift-check` job in `ci-smoke.yml` runs this check on every PR/push to ensure no drift between `pyproject.toml` and `requirements.txt`.

## ⚠️ Security Gates

**CRITICAL:** MLSDM implements strict security gating. Security checks are **BLOCKING** and will prevent merges/releases if they fail.

See **[docs/CI_SECURITY_GATING.md](docs/CI_SECURITY_GATING.md)** for complete security gate policy, including:
- Which security checks block CI
- How to run security checks locally
- What to do when a security gate fails
- Justification for informational checks

**Quick security check before pushing:**
```bash
bandit -r src/mlsdm --severity-level high --confidence-level high
pip-audit --requirement requirements.txt --strict
```

## CI Workflows

### Core CI Workflows (Run on Every PR/Push)

#### 1. **CI - Neuro Cognitive Engine** (`ci-neuro-cognitive-engine.yml`)
**Purpose:** Primary CI pipeline for code quality and testing
**Triggers:** Push to main/feature branches, PRs
**Duration:** ~15-20 minutes

**Jobs:**
- `lint`: Code linting (ruff) and type checking (mypy)
- `security`: Dependency vulnerability scanning (pip-audit) - **BLOCKING GATE**
- `test`: Unit and integration tests (Python 3.10, 3.11)
- `coverage`: Code coverage gate with **75% threshold** (current coverage: ~88%)
- `e2e-tests`: End-to-end integration tests
- `effectiveness-validation`: Validate cognitive system metrics
- `benchmarks`: Performance benchmarks with SLO validation
- `neuro-engine-eval`: Sapolsky cognitive safety evaluation (informational, non-blocking)
- `all-ci-passed`: Gate job requiring all critical checks (excludes neuro-engine-eval)

**Reproduce coverage locally:**
```bash
# Run tests with coverage (matches CI gate)
pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing \
  --cov-fail-under=75 --ignore=tests/load -m "not slow and not benchmark" -v

# Or use the coverage script
./coverage_gate.sh

# Or use Make
make cov
```

**When to modify:**
- Adding new test suites
- Changing Python version support
- Modifying test infrastructure

#### 2. **CI Smoke Tests** (`ci-smoke.yml`)
**Purpose:** Quick sanity checks for rapid feedback
**Triggers:** Push to main/feature branches, PRs
**Duration:** ~5 minutes

**Jobs:**
- Quick import tests
- Basic API health checks
- Configuration validation

**When to modify:**
- Adding critical smoke tests
- Changing core dependencies

#### 3. **Property-Based Tests** (`property-tests.yml`)
**Purpose:** Hypothesis-based property testing
**Triggers:** Push to main/feature branches, PRs
**Duration:** ~10 minutes

**Jobs:**
- Fuzz testing with Hypothesis
- Invariant validation
- Edge case detection

**When to modify:**
- Adding new property-based tests
- Changing test strategies

#### 4. **SAST Security Scan** (`sast-scan.yml`)
**Purpose:** Static Application Security Testing
**Triggers:** Push to main, PRs
**Duration:** ~5-10 minutes

**Jobs:**
- Bandit security scanning (BLOCKING GATE)
- Semgrep SAST with security rulesets (BLOCKING GATE)
- Dependency audits
- Secret detection

**Security Gate Policy:** This workflow implements critical security gates. See [docs/CI_SECURITY_GATING.md](docs/CI_SECURITY_GATING.md) for details.

**When to modify:**
- Adding new security checks
- Updating security policies

### Specialized CI Workflows

#### 5. **Aphasia / NeuroLang CI** (`aphasia-ci.yml`)
**Purpose:** Test optional Aphasia/NeuroLang extension
**Triggers:** Push to main/feature branches, PRs (manual dispatch)
**Duration:** ~10 minutes

**Jobs:**
- Aphasia detection tests
- Speech governance validation
- PyTorch-dependent tests

**When to modify:**
- Changes to NeuroLang extension
- Adding speech governance features

#### 6. **Performance & Resilience Validation** (`perf-resilience.yml`)
**Purpose:** Load testing and stress testing
**Triggers:** Scheduled (daily at 2 AM UTC), manual dispatch
**Duration:** ~30-60 minutes

**Jobs:**
- Load testing with Locust
- Stress testing
- Performance regression detection

**When to modify:**
- Changing performance requirements
- Adding new performance tests

#### 7. **Chaos Engineering Tests** (`chaos-tests.yml`)
**Purpose:** Test system resilience under adverse conditions
**Triggers:** Scheduled (daily at 3 AM UTC), manual dispatch
**Duration:** ~30-60 minutes

**Jobs:**
- Memory pressure tests
- Network disruption tests
- LLM failure simulation

**When to modify:**
- Adding new chaos scenarios
- Changing resilience requirements

### Release Workflows

#### 8. **Production Gate** (`prod-gate.yml`)
**Purpose:** Pre-production validation and approval
**Triggers:** Manual workflow dispatch
**Duration:** ~30 minutes + manual approval time

**Jobs:**
- Full test suite execution
- Security audit
- Performance validation
- Manual approval step
- Deployment simulation

## Failure Intelligence Summaries

- CI Smoke runs publish a **Failure Intelligence** section in the GitHub Actions job summary.
- The artifact `failure-intelligence` contains `failure_summary.md`, `failure_summary.json`, and `changed_files.txt` for reproducible debugging.
- Reproduce failures locally using the suggested commands in the summary (commonly `make test-fast`, `make lint`, `make type`).

### Artifact Contract

The Failure Intelligence job expects specific artifacts from upstream jobs. These are defined as environment variables in `ci-smoke.yml`:

| Artifact Name | Expected Path | Source Job |
|---------------|---------------|------------|
| `smoke-junit` | `artifacts/junit-smoke.xml` | smoke |
| `coverage-report` | `artifacts/coverage.xml` | coverage-gate |
| `ablation-report` | `artifacts/` | ablation-smoke |

**When artifacts are missing:**

The script handles missing artifacts gracefully:
- Sets `status: "degraded"` in the JSON output
- Records structured errors in `input_errors` array with format:
  ```json
  {"code": "input_missing", "artifact": "junit", "expected_path": "artifacts/junit-smoke.xml"}
  ```
- Includes an "Input Integrity" section in the markdown summary listing all missing inputs
- Job still succeeds (never-fail behavior) to avoid blocking the workflow
- Missing artifacts are surfaced clearly in both markdown and JSON outputs

**When to modify:**
- Changing production requirements
- Adding deployment validations

#### 9. **Release** (`release.yml`)
**Purpose:** Build and publish releases
**Triggers:** Git tags (v*)
**Duration:** ~15 minutes

**Jobs:**
- Build Python package
- Create GitHub release
- Publish to PyPI (if configured)
- Build Docker images
- Generate release notes

**When to modify:**
- Changing release process
- Adding build artifacts

## Workflow Dependencies

```
Main CI Flow:
ci-neuro-cognitive-engine (REQUIRED)
  ├── lint (with pip caching)
  ├── security (pip-audit on requirements.txt only)
  ├── test (matrix: Python 3.10, 3.11 with pip caching)
  ├── coverage (75% threshold, current evidence: ~80.04%, with pip caching)
  ├── e2e-tests (with pip caching)
  ├── effectiveness-validation (with pip caching)
  ├── benchmarks (SLO validation, accurate timestamps)
  └── neuro-engine-eval (continue-on-error: true)

Supporting Checks:
├── ci-smoke (FAST FEEDBACK)
├── property-tests (HYPOTHESIS)
├── sast-scan (SECURITY)
└── aphasia-ci (OPTIONAL EXTENSION)

Scheduled/Manual:
├── perf-resilience (NIGHTLY)
├── chaos-tests (NIGHTLY)
└── prod-gate (MANUAL - BEFORE RELEASE)

Release:
└── release (TAG TRIGGERED)
```

## Environment Variables

### Common Variables

```bash
# Disable rate limiting for CI
export DISABLE_RATE_LIMIT=1

# Use stub LLM backend for testing
export LLM_BACKEND=local_stub

# OpenTelemetry configuration (optional)
export OTEL_SDK_DISABLED=true  # Disable OTEL in CI for speed
export OTEL_EXPORTER_TYPE=none

# Test configuration
export PYTEST_TIMEOUT=300  # 5 minute timeout per test
```

### Secrets Required

Configure these in GitHub repository secrets:

- `PYPI_API_TOKEN`: PyPI publishing token (optional)
- `DOCKER_USERNAME`: Docker Hub username (optional)
- `DOCKER_PASSWORD`: Docker Hub password (optional)

## Running CI Locally

### Run Core Tests

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run linting
ruff check src tests

# Run type checking
mypy src/mlsdm

# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Run all tests (like CI)
pytest tests/ --ignore=tests/load -v
```

### Run Security Scans

```bash
# Install security tools
pip install pip-audit bandit

# Run dependency audit (only requirements.txt to avoid system package false positives)
pip-audit --requirement requirements.txt --progress-spinner=off

# Run security scan
bandit -r src/
```

### Run Coverage Tests

```bash
# Run tests with coverage (75% threshold, current evidence: ~80.04%)
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing \
  --cov-fail-under=75 --ignore=tests/load -v
```

### Run E2E and Effectiveness Tests

```bash
# E2E tests
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/e2e -v -m "not slow" --tb=short

# Effectiveness validation with SLO
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  python scripts/run_effectiveness_suite.py --validate-slo

# Benchmark tests with SLO
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest benchmarks/test_neuro_engine_performance.py -v -s --tb=short

# Sapolsky evaluation suite
DISABLE_RATE_LIMIT=1 LLM_BACKEND=local_stub \
  pytest tests/eval/test_sapolsky_suite.py -v
```

### Run Property Tests

```bash
# Run hypothesis tests
pytest tests/property -v --hypothesis-show-statistics
```

## Recent CI Improvements (December 2025)

### Q4 2025 Hardening

The CI pipeline was hardened with the following improvements:

1. **Pip Dependency Caching**
   - Added `cache: 'pip'` to all Python setup steps
   - Dramatically reduces dependency installation time (from ~2-3 minutes to ~10-20 seconds on cache hit)
   - Cache key based on `requirements.txt` and `pyproject.toml` hashes

2. **Security Scan Refinement**
   - Changed from `pip-audit --strict` to `pip-audit --requirement requirements.txt`
   - Eliminates false positives from system packages (configobj, twisted, etc.)
   - Focuses audit on project dependencies only

3. **Timestamp Accuracy in Benchmarks**
   - Fixed hardcoded shell timestamp in benchmark metrics
   - Now uses Python `datetime.now(timezone.utc)` for accurate timestamps
   - Ensures proper time tracking in benchmark reports

4. **Coverage Gate Addition**
  - Added dedicated `coverage` job with 75% threshold (current evidence: ~80.04%)
   - Generates and uploads coverage reports as CI artifacts
   - Included in `all-ci-passed` gate for quality enforcement
   - Threshold may be increased as coverage continues to improve

5. **Python 3.10/3.11 Compatibility**
   - Verified compatibility using `typing_extensions.Self` instead of native `Self`
   - Confirmed all dependencies support Python 3.10+
   - Matrix testing ensures both versions work correctly

### Quality Metrics

Current CI pipeline ensures:
- **Lint**: Zero ruff/mypy violations
- **Security**: Zero known vulnerabilities in project dependencies
- **Coverage**: ≥75% threshold (actual evidence: ~80.04%) - see [docs/METRICS_SOURCE.md](docs/METRICS_SOURCE.md)
- **E2E**: 68 end-to-end tests passing
- **Effectiveness**: SLO validation passing
- **Benchmarks**: P95 latency within SLO (< 500ms)
- **Sapolsky**: 14 cognitive safety tests passing

## CI Optimization Tips

### Speed Up CI

1. **Use minimal dependencies in workflows**
   - Only install OTEL for workflows that need tracing
   - Skip visualization dependencies (matplotlib, jupyter) in CI

2. **Parallel test execution**
   - Use `pytest-xdist` for parallel tests
   ```bash
   pytest tests/ -n auto
   ```

3. **Cached dependencies** (✅ IMPLEMENTED)
   - GitHub Actions caches pip packages automatically
   - Ensure `actions/setup-python@v5` with `cache: 'pip'` is used
   - All CI jobs now use pip caching (Q4 2025 improvement)

4. **Skip long tests in smoke checks**
   ```bash
   pytest tests/ -m "not slow"
   ```

### Reduce Workflow Count

**Option: Consolidate into single workflow with jobs**

Instead of 9 separate workflow files, you could consolidate into fewer workflows:

```yaml
# mega-ci.yml (example consolidation)
name: CI Pipeline
on: [push, pull_request]

jobs:
  quick-checks:
    runs-on: ubuntu-latest
    steps:
      - lint
      - smoke-tests

  full-tests:
    needs: quick-checks
    strategy:
      matrix:
        python-version: ['3.10', '3.11']
    runs-on: ubuntu-latest
    steps:
      - unit-tests
      - integration-tests
      - e2e-tests

  specialized-tests:
    needs: full-tests
    runs-on: ubuntu-latest
    steps:
      - property-tests
      - security-scan
      - aphasia-tests (if: optional)
```

**Trade-offs:**
- ✅ Fewer workflow files to maintain
- ✅ Clearer dependency graph
- ❌ Less granular control
- ❌ Longer feedback time (sequential jobs)

## Troubleshooting CI Failures

### Common Issues

#### 1. Import Error: No module named 'opentelemetry'

**Fix:** OpenTelemetry is now optional. Either:
- Install it: `pip install ".[observability]"`
- Or set `OTEL_SDK_DISABLED=true` (it will work without it)

#### 2. Rate Limit Errors in Tests

**Fix:** Set environment variable:
```bash
export DISABLE_RATE_LIMIT=1
```

#### 3. Timeout in Long-Running Tests

**Fix:** Skip slow tests in smoke checks:
```bash
pytest -m "not slow"
```

Or increase timeout:
```yaml
timeout-minutes: 30  # in workflow YAML
```

#### 4. Dependency Conflicts

**Fix:** Use clean virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 5. Security Scan False Positives

**Fix:** Create exemption in `pyproject.toml`:
```toml
[tool.bandit]
exclude_dirs = ["tests", "examples"]
skips = ["B404", "B603"]  # specific checks to skip
```

## Best Practices

### When Adding New Tests

1. **Add to appropriate workflow**
   - Unit tests → `ci-neuro-cognitive-engine.yml`
   - Security tests → `sast-scan.yml`
   - Performance tests → `perf-resilience.yml`

2. **Mark slow tests**
   ```python
   import pytest

   @pytest.mark.slow
   def test_long_running():
       ...
   ```

3. **Test locally first**
   ```bash
   pytest tests/new_test.py -v
   ```

### When Modifying Workflows

1. **Test with act (local GitHub Actions)**
   ```bash
   # Install act: https://github.com/nektos/act
   act -j lint  # Run specific job
   ```

2. **Use workflow dispatch for testing**
   ```yaml
   on:
     workflow_dispatch:  # Allow manual triggering
   ```

3. **Validate YAML syntax**
   ```bash
   # Use yamllint
   yamllint .github/workflows/*.yml
   ```

## Monitoring CI Health

### Key Metrics

- **Average CI Duration**: Should be < 20 minutes
- **Flaky Test Rate**: Should be < 1%
- **Security Scan Pass Rate**: Should be 100%
- **Cache Hit Rate**: Should be > 80%

### CI Dashboard

Monitor at: `https://github.com/neuron7xLab/mlsdm/actions`

Look for:
- ✅ Green checkmarks on all jobs
- ⚠️ Warning signs for flaky tests
- ❌ Red X's for failures

## CI Performance & Resilience Gate

**New Tool:** Automated PR risk assessment and merge verdict system.

The CI Performance & Resilience Gate (`scripts/ci_perf_resilience_gate.py`) analyzes PRs to ensure critical performance and resilience tests run before merge.

**Features:**
- Automatic risk classification (GREEN/YELLOW/RED)
- CI status verification
- Clear merge verdicts with required actions
- SLO/CI improvement suggestions

**Usage:**
```bash
# Analyze a PR
python scripts/ci_perf_resilience_gate.py --pr-url https://github.com/neuron7xLab/mlsdm/pull/231

# With authentication (higher rate limits)
export GITHUB_TOKEN=your_token
python scripts/ci_perf_resilience_gate.py --pr-number 231 --repo neuron7xLab/mlsdm
```

**When to Use:**
- Before merging any PR that touches core code
- For release PRs (requires full validation)
- When unsure if perf/resilience tests are needed

**Documentation:** [docs/CI_PERF_RESILIENCE_GATE.md](docs/CI_PERF_RESILIENCE_GATE.md)

## Support

- **CI Issues**: [GitHub Issues](https://github.com/neuron7xLab/mlsdm/issues)
- **Workflow Examples**: [GitHub Actions Docs](https://docs.github.com/en/actions)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Last Updated:** December 2025
**Maintainer:** neuron7x
