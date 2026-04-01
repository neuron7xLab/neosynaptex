# Placeholder Registry

Canonical registry for placeholder remediation cycles.

## Canonical Commands

- Placeholder scan (text): `python -m scripts.scan_placeholders --format text`
- Placeholder scan (json): `python -m scripts.scan_placeholders --format json`
- Canonical test command: `python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=term-missing:skip-covered --cov-report=json --cov-report=xml:coverage.xml --cov-report=html --cov-fail-under=85 --junit-xml=junit.xml -v`
- CI workflow: `.github/workflows/ci-pr-atomic.yml`

## Normalized PH Entries

- ID: PH-0001
- Path: `src/bnsyn/emergence/crystallizer.py:283`
- Signature: `pass_in_except`
- Risk: `runtime_critical`
- Owner: `UNKNOWN`
- Fix Strategy: `guard_fail_closed`
- Test Strategy: `regression`
- Status: CLOSED
- evidence_ref: `tests/test_crystallizer_edge_cases.py::test_crystallizer_pca_failure_retains_previous`

- ID: PH-0002
- Path: `tests/test_coverage_gate.py:24`
- Signature: `pass_in_except`
- Risk: `tests`
- Owner: `UNKNOWN`
- Fix Strategy: `implement_minimal`
- Test Strategy: `regression`
- Status: CLOSED
- evidence_ref: `tests/test_coverage_gate.py::test_read_coverage_percent_missing_file_fails`

- ID: PH-0003
- Path: `tests/validation/test_chaos_integration.py:256`
- Signature: `pass_in_except`
- Risk: `tests`
- Owner: `UNKNOWN`
- Fix Strategy: `guard_fail_closed`
- Test Strategy: `regression`
- Status: CLOSED
- evidence_ref: `tests/validation/test_chaos_integration.py::test_adex_bounds_enforcement`
