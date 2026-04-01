# Placeholder Closure Plan

## Scope Constraints

Touch only placeholder registry, placeholder validation tests, and required closure artifacts.

## Canonical Discovery

- SCAN_CMD: `python -m scripts.scan_placeholders --format text`
- TEST_CMD: `python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=term-missing:skip-covered --cov-report=json --cov-report=xml:coverage.xml --cov-report=html --cov-fail-under=85 --junit-xml=junit.xml -v`
- CI_WORKFLOW: `.github/workflows/ci-pr-atomic.yml`

## PH_BATCHES

### PH_BATCH_01

- IDs: `PH-0001`
- Strategy: `guard_fail_closed`
- Test: `tests/test_crystallizer_edge_cases.py::test_crystallizer_pca_failure_retains_previous`

### PH_BATCH_02

- IDs: `PH-0002`, `PH-0003`
- Strategy: `implement_minimal`, `guard_fail_closed`
- Tests:
  - `tests/test_coverage_gate.py::test_read_coverage_percent_missing_file_fails`
  - `tests/validation/test_chaos_integration.py::test_adex_bounds_enforcement`

## Final

- Registry normalized with CLOSED statuses and `evidence_ref` for each PH.
- Meta scan and registry validation tests are required gates.
