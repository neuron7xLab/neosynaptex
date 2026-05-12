# Audit Gap Report

## Blocking finding
Final audit evidence is blocked: `python -m pip install -e ".[dev]"` fails, so coverage and release-gate evidence cannot be regenerated from a clean environment.

## Root cause
The environment cannot fetch missing dev dependencies from package index (network/proxy restricted), specifically `pytest-cov` during editable install.

## Affected files
- `pyproject.toml`
- `docs/audit/final-review-2026/coverage_100.exit`
- `docs/audit/final-review-2026/coverage_100.log`
- `scripts/validate_audit_bundle.py`

## Why this invalidates release evidence
Without successful editable install, test/coverage evidence is incomplete and non-reproducible; therefore release readiness is not provable.

## Required fix
1. Ensure clean runner with index access (or internal wheelhouse) for dev dependencies.
2. Re-run install, full tests, and coverage gate.
3. Regenerate audit logs from actual command output.

## Verification commands
- `python -m pip install -e ".[dev]"`
- `python -m pytest --cov=src/bnsyn --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=90 -q`
- `python scripts/validate_audit_bundle.py docs/audit/final-review-2026`
- `python scripts/check_regime_release_gate.py`

## Final status
BLOCKED
