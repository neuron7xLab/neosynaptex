# GitHub Actions Test Protocol

**Version:** 1.0  
**Date:** 2026-01-27  
**Repository:** neuron7x/bnsyn-phase-controlled-emergent-dynamics

---

## Purpose

This document describes the **GitHub Actions testing strategy** for BN-Syn, including workflow design, fork-safety policies, and artifact management.

---

## Workflow Architecture

### 1. Blocking Workflows (PR Gates)

**Trigger:** `pull_request`, `push` to main  
**Purpose:** Prevent broken code from merging  
**Timeout:** 10-15 minutes per job  
**Failure Policy:** Block merge

#### ci-pr.yml

Primary PR validation workflow with 10 blocking jobs:

- `ssot` - SSOT validation + **claims coverage gate**
- `dependency-consistency` - Dependency resolution + audit
- `quality` - Linting + type checking (reusable)
- `build` - Package build + import check
- `docs-build` - Sphinx documentation build
- `tests-smoke` - Smoke test suite (reusable, 85% coverage)
- `tests-core-only` - Core tests without optional deps
- `benchmarks.yml` (tier=standard, profile=ci) - Fast smoke benchmarks
- `gitleaks` - Secret scanning
- `pip-audit` - Dependency vulnerability scan

**Key Features:**
- GitHub Step Summaries for all jobs
- Artifact uploads on failure
- Concurrency control (cancel in-progress)

---

### 2. Non-Blocking Workflows (Scheduled)

**Trigger:** `schedule` cron + `workflow_dispatch`  
**Purpose:** Comprehensive validation without blocking PRs  
**Timeout:** 30 minutes per job  
**Failure Policy:** Informational, manual review

#### ci-validation.yml (mode: `elite`)

Daily validation of scientific claims and invariants:

**Jobs:**
- `validation` - 10 validation tests (`-m validation`)
- `property-tests` - 8 Hypothesis property tests (`-m property`)
- `summary` - Aggregate results

**Schedule:** Daily at 2 AM UTC  
**Artifacts:** `validation.log`, `property.log`, JUnit XML

**Never Triggered On:** `pull_request` or `push` (isolated from PR gates)

#### benchmarks.yml (tier=elite, profile=elite)

Weekly performance regression detection:

**Jobs:**
- `benchmarks` - Run all benchmarks + compare to golden baseline

**Schedule:** Weekly Sunday at 3 AM UTC  
**Artifacts:** `baseline.json`, `benchmark_report.json`

**Policy:** Non-blocking, manual review of regressions

---

## Fork-Safety Policy

All workflows are **fork-safe** by design:

1. **No Secrets Required**
   - All validation/testing uses public data
   - No GitHub tokens needed for core functionality
   - Secrets only used for optional integrations (Codecov)

2. **Artifact Access**
   - Artifacts accessible to PR authors
   - Retention: 30-90 days depending on type

3. **Step Summaries**
   - All critical info written to `$GITHUB_STEP_SUMMARY`
   - Visible directly in PR checks UI

---

## Artifact Policy

### Retention Schedule

| Artifact Type | Retention | Workflow | Purpose |
|---------------|-----------|----------|---------|
| Claims Coverage | 30 days | ci-pr.yml | Evidence traceability |
| Validation Logs | 30 days | ci-validation.yml (elite mode) | Scientific validation |
| Property Logs | 30 days | ci-validation.yml (elite mode) | Invariant verification |
| Benchmark Results | 90 days | benchmarks.yml (elite schedule) | Performance tracking |
| Dependency Audit | 30 days | ci-pr.yml | Security compliance |

### Artifact Naming

Format: `{artifact-type}-{sha|timestamp}`

Examples:
- `claims-coverage-report` (per-PR)
- `validation-logs-abc123` (per-commit)
- `benchmark-results-2026-01-27` (per-run)

---

## Test Markers

### Pytest Markers

```python
@pytest.mark.smoke          # Fast critical-path tests (BLOCKING)
@pytest.mark.validation     # Slow scientific validation (NON-BLOCKING)
@pytest.mark.property       # Hypothesis property tests (NON-BLOCKING)
@pytest.mark.performance    # Performance regression tests
@pytest.mark.integration    # Integration tests
```

### Marker Enforcement

`tests/conftest.py` enforces:
- All tests in `tests/validation/` MUST have `@pytest.mark.validation`
- Validation marker CANNOT be used outside `tests/validation/`

**Rationale:** Prevent accidental inclusion of slow tests in PR gates

---

## Hypothesis Configuration

### Profiles

Defined in `tests/conftest.py`:

```python
settings.register_profile("quick", max_examples=100, deadline=5000)
settings.register_profile("ci-quick", max_examples=50, deadline=5000)
settings.register_profile("thorough", max_examples=1000, deadline=20000)
```

**Auto-Loading:**
- `CI=true` → loads `ci-quick` profile
- `HYPOTHESIS_PROFILE=thorough` → loads specified profile

---

## Debugging Workflow Failures

### Smoke Tests Failing?

1. Check step summary in GitHub UI
2. Download artifacts (if uploaded)
3. Reproduce locally:
   ```bash
   pytest -m "not (validation or property)" -v
   ```

### Claims Coverage Gate Failing?

1. Run validator:
   ```bash
   make validate-claims-coverage
   ```
2. Fix incomplete claims in `claims/claims.yml`
3. Ensure all normative claims have: bibkey, locator, verification_paths, status

### Validation Tests Failing (Non-Blocking)?

1. **Note:** These don't block PRs
2. Check `validation.log` artifact
3. Investigate specific test failures
4. Fix if determinism broken, otherwise file issue

### Benchmarks Showing Regression?

1. **Note:** Non-blocking, manual review
2. Download `benchmark_report.json`
3. Check if regression is real or noise
4. If real: investigate, optimize, or update baseline

---

## Local Development

### Run All PR Checks Locally

```bash
# SSOT validation
make ssot
make validate-claims-coverage

# Quality checks
make quality

# Tests (smoke suite only)
make test
make coverage

# Security
make security
```

### Run Validation Tests

```bash
# Full validation suite (~10 min)
make test-validation

# Specific validation test
pytest tests/validation/test_claims_validation.py::test_clm_001_determinism_across_runs -v
```

### Run Property Tests

```bash
# With ci-quick profile (fast)
HYPOTHESIS_PROFILE=ci-quick pytest -m property -v

# With thorough profile (slow, 1000 examples)
HYPOTHESIS_PROFILE=thorough pytest -m property -v
```

---

## Workflow Modifications

### Adding New Blocking Test

1. Add test file to `tests/`
2. **Do NOT** mark with `@pytest.mark.validation` or `@pytest.mark.property`
3. Ensure runtime <10 seconds for smoke suite budget
4. Verify it runs in `ci-pr.yml` smoke job

### Adding New Validation Test

1. Create test in `tests/validation/`
2. **Must** mark with `@pytest.mark.validation`
3. Runtime budget: ~2 minutes per test (10 tests = 20 min total)
4. Runs in `ci-validation.yml` (mode: `elite`), NOT in PR gates

### Adding New Property Test

1. Create test in `tests/properties/`
2. **Must** mark with `@pytest.mark.property`
3. Use Hypothesis `@given` decorator
4. Budget: 50 examples × 5s deadline = ~4 min max per test
5. Runs in `ci-validation.yml` (mode: `elite`), NOT in PR gates

---

## References

- **CI Gates:** `docs/CI_GATES.md`
- **Workflow Contracts:** `.github/WORKFLOW_CONTRACTS.md`
- **Pytest Config:** `pyproject.toml` (`[tool.pytest.ini_options]`)
- **Hypothesis Profiles:** `tests/conftest.py`

---

**Last Updated:** 2026-01-27  
**Maintained By:** @neuron7x
