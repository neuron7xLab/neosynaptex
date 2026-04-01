# Release Checklist

**Version**: 1.2.0
**Last Updated**: November 2025
**Purpose**: Release gate verification synced with `.github/workflows/release.yml`

---

## Release Gates (CI/CD)

The following gates must **ALL PASS** before a release can be published. These gates are enforced automatically in the release workflow and are triggered by pushing a tag `vX.Y.Z`.

| Gate | Workflow Job | Required | Description |
|------|--------------|----------|-------------|
| ✅ Unit Tests | `unit-tests` | **Yes** | All unit tests in `tests/unit/` must pass |
| ✅ Integration Tests | `integration-tests` | **Yes** | All integration tests in `tests/integration/` must pass |
| ✅ Property Tests | `property-tests` | **Yes** | All property-based tests in `tests/property/` must pass |
| ✅ Validation Tests | `validation-tests` | **Yes** | All validation tests in `tests/validation/` must pass |
| ✅ Security Tests | `security-tests` | **Yes** | All security tests in `tests/security/` must pass |
| ✅ Observability Tests | `observability-tests` | **Yes** | All observability tests in `tests/observability/` must pass |
| ✅ Benchmarks | `benchmarks` | **Yes** | Performance benchmarks must meet SLO |
| ✅ Code Quality | `code-quality` | **Yes** | Linting (ruff) and type checking (mypy) must pass |
| ✅ Coverage | `coverage-check` | **Yes** | Test coverage must be >= 90% |

---

## Local Verification Commands

Run these commands locally before tagging a release:

```bash
# 1. Install dependencies
pip install -e ".[test]"
pip install ruff mypy

# 2. Gate: Unit Tests
pytest tests/unit/ -v --tb=short

# 3. Gate: Integration Tests
pytest tests/integration/ -v --tb=short

# 4. Gate: Property Tests
pytest tests/property/ -v --tb=short --maxfail=5

# 5. Gate: Validation Tests
pytest tests/validation/ -v --tb=short

# 6. Gate: Security Tests
pytest tests/security/ -v --tb=short

# 7. Gate: Observability Tests
pytest tests/observability/ -v --tb=short

# 8. Gate: Benchmarks
pytest benchmarks/test_neuro_engine_performance.py -v -s --tb=short

# 9. Gate: Code Quality - Linting
ruff check src tests

# 10. Gate: Code Quality - Type Checking
mypy src/mlsdm --ignore-missing-imports

# 11. Gate: Coverage Check
# Uses same command as CI (see docs/METRICS_SOURCE.md for current metrics)
# Threshold: 75% (policy) | Actual: 80.04% (see artifacts/evidence/2025-12-26/2a6b52dd6fd4)
pytest --cov=src/mlsdm --cov-report=term-missing --cov-fail-under=75 \
  --ignore=tests/load -m "not slow and not benchmark" -q
```

---

## Release Process

### 1. Pre-Release Verification

- [ ] All local verification commands pass
- [ ] CHANGELOG.md updated with version notes
- [ ] Version in `pyproject.toml` matches release tag
- [ ] No critical security advisories pending

### 2. Create Release Tag

```bash
# Ensure you're on main with latest changes
git checkout main
git pull origin main

# Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0: Production Observability & Security"

# Push tag to trigger release workflow
git push origin v1.2.0
```

### 3. Monitor Release Workflow

1. Go to GitHub Actions → Release workflow
2. Verify all gates pass:
   - [ ] unit-tests (matrix: py3.10, py3.11)
   - [ ] integration-tests
   - [ ] property-tests
   - [ ] validation-tests
   - [ ] security-tests
   - [ ] observability-tests
   - [ ] benchmarks
   - [ ] code-quality
   - [ ] coverage-check

3. After all gates pass, verify:
   - [ ] build-and-push-docker succeeds
   - [ ] GitHub Release is created
   - [ ] Docker image is pushed to ghcr.io
   - [ ] TestPyPI publish succeeds (if configured)

### 4. Post-Release Verification

- [ ] Docker image pulls successfully:
  ```bash
  docker pull ghcr.io/$REPO_OWNER/mlsdm-neuro-engine:1.2.0
  docker run --rm ghcr.io/$REPO_OWNER/mlsdm-neuro-engine:1.2.0 python -c "import mlsdm; print(mlsdm.__version__)"
  ```

- [ ] GitHub Release page shows correct version and notes
- [ ] Security scan completed (check GitHub Security tab)

---

## Gate Failure Troubleshooting

### Unit/Integration/Property/Validation Tests Fail

1. Check the specific test output in GitHub Actions
2. Run the failing tests locally with verbose output:
   ```bash
   pytest tests/<category>/test_<failing_file>.py -v -s
   ```
3. Fix the issue and push to main before re-tagging

### Security Tests Fail

1. Review `tests/security/` test output
2. Common causes:
   - Secure mode invariants violated
   - PII leakage in logs
   - Emergency shutdown behavior changed
3. Fix security issues before release

### Observability Tests Fail

1. Review `tests/observability/` test output
2. Common causes:
   - New metrics not properly exported
   - Logging format changed
   - Tracing configuration issues

### Benchmarks Fail

1. Review benchmark output for SLO violations
2. Check for performance regressions
3. Latency SLOs:
   - Pre-flight: P95 < 20ms
   - End-to-end: P95 < 500ms

### Code Quality Fails

1. **Linting (ruff)**: Run `ruff check src tests --fix` for auto-fixes
2. **Type checking (mypy)**: Review type errors and add annotations

### Coverage Fails

1. Coverage must be >= 90%
2. Add tests for uncovered code paths
3. Check coverage report: `pytest --cov=src --cov-report=html`

---

## Rollback Procedure

If issues are discovered after release:

```bash
# 1. Retag with patch version
git tag -a v1.2.1 -m "Hotfix: <description>"
git push origin v1.2.1

# 2. Or rollback to previous Docker image
docker pull ghcr.io/$REPO_OWNER/mlsdm-neuro-engine:1.1.0

# 3. Update Kubernetes (if deployed)
kubectl set image deployment/mlsdm-api mlsdm=ghcr.io/$REPO_OWNER/mlsdm-neuro-engine:1.1.0 -n mlsdm-production
```

---

## Version History

| Version | Date | Release Manager | Notes |
|---------|------|-----------------|-------|
| 1.2.0 | 2025-11 | - | Production observability & security gates |
| 1.1.0 | 2025-10 | - | Initial release gates |
