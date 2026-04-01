# Testing & Coverage (Canonical)

This document is the **single source of truth** for running tests and coverage in this repository.

## Install test dependencies

```bash
python -m pip install -e ".[test]"
```

Expected output pattern:
- `Successfully installed bnsyn-...`
- No import errors for `pytest`, `pytest-cov`, `hypothesis`.

## Run default test suite

```bash
make test
```

Equivalent explicit command:

```bash
python -m pytest -m "not (validation or property)" -q
```

Expected output pattern:
- Dots for passing tests.
- Final summary with `passed` and optional `skipped`.

## Canonical split targets

```bash
make test-gate
make test-all
make test-integration
make test-e2e
make test-validation
make test-property
```

Equivalent explicit commands:

```bash
python -m pytest -m "not (validation or property)" -q
python -m pytest -m "validation" -q
python -m pytest -m "property" -q
```

All three suites are expected to **collect successfully** when test dependencies are installed.

## Run smoke marker tests

```bash
python -m pytest -m smoke -q
```

Expected output pattern:
- Only smoke-marked tests.


## Property test contour (Hypothesis)

Hypothesis profiles are defined only in:
- `tests/properties/conftest.py`

Run property tests (requires `hypothesis` installed):

```bash
HYPOTHESIS_PROFILE=ci python -m pytest tests/properties -m property -q
```

Alternate profiles:

```bash
HYPOTHESIS_PROFILE=quick python -m pytest tests/properties -m property -q
HYPOTHESIS_PROFILE=thorough python -m pytest tests/properties -m property -q
```

Run non-property tests without Hypothesis dependency:

```bash
python -m pytest -m "not property" -q
```

Behavior when `hypothesis` is missing:
- `python -m pytest -m "not property" -q` succeeds.
- `python -m pytest tests/properties -m property -q` fails with explicit `ModuleNotFoundError: No module named 'hypothesis'`.

## Generate fast local coverage artifacts (canonical dev path)

```bash
make coverage-fast
```

Equivalent explicit command:

```bash
python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=term-missing --cov-report=xml:coverage.xml -q
```

Artifacts:
- Terminal report with missing lines by module (`term-missing`).
- `coverage.xml` at repository root.

## Generate coverage artifacts

```bash
make coverage
```

Equivalent explicit command:

```bash
python -m pytest --cov=bnsyn --cov-report=term-missing:skip-covered --cov-report=xml:coverage.xml -q
```

Artifacts:
- Terminal report with missing lines by module.
- `coverage.xml` at repository root.

## Generate / refresh coverage baseline

```bash
make coverage-baseline
```

Equivalent explicit command:

```bash
python -m scripts.generate_coverage_baseline --coverage-xml coverage.xml --output quality/coverage_gate.json --minimum-percent 99.0
```

This baseline uses the same metric enforced by the gate: `coverage.xml line-rate`.

## Enforce coverage gate

```bash
make coverage-gate
```

Gate behavior:
- Fails if current coverage drops below baseline in `quality/coverage_gate.json`.
- Fails if current coverage drops below minimum floor in `quality/coverage_gate.json`.


## API contract check (canonical)

```bash
make api-contract
```

Equivalent explicit command:

```bash
python -m scripts.check_api_contract --baseline quality/api_contract_baseline.json
```

Expected output pattern:
- `API contract check passed`

## CI parity checks (local)

Use the same checks enforced in PR CI:

```bash
python -m pytest --collect-only -q
python -m pytest -m "not (validation or property)" -q
python -m pytest --cov=bnsyn --cov-report=term-missing:skip-covered --cov-report=xml:coverage.xml -q
ruff check .
```

If a tool is unavailable locally, install via:

```bash
python -m pip install -e ".[test]"
```

Deferred gate note:
- `mypy` is configured in CI quality workflow; run locally only after full `.[dev]` install.


## Offline dependency workflow (Python 3.11)

Notes:
- `wheelhouse/` is platform-specific (implementation/ABI/platform tag). Build and validate for the same target.
- `wheelhouse-build` requires internet access. `wheelhouse-validate` and `dev-env-offline` are offline.
- `wheelhouse-build` uses `pip download --only-binary=:all: --no-deps`; lock file must stay fully pinned.
- `wheelhouse-validate` writes `artifacts/wheelhouse_report.json` by default.

Build the local wheelhouse from pinned lock dependencies:

```bash
make wheelhouse-build
```

Validate that every pinned dependency in `requirements-lock.txt` has a matching wheel in `wheelhouse/`:

```bash
make wheelhouse-validate
make wheelhouse-report
```

Install the development environment fully offline from the local wheelhouse:

```bash
make dev-env-offline
```

Equivalent install commands:

```bash
python -m pip install --no-index --find-links wheelhouse -r requirements-lock.txt
python -m pip install --no-index --find-links wheelhouse --no-deps -e .
```

Failure modes:
- Locked package has no wheel for the configured target tuple.
- Marker applicability differs from the target environment.
- Wheelhouse built for a different platform/ABI than the install target.

Validation exit codes:
- `0`: wheelhouse fully covers applicable locked requirements.
- `1`: one or more applicable locked requirements are missing wheels.
- `2`: lock contains unsupported or duplicate applicable requirement entries.

Report contains additional diagnostics:
- `duplicate_requirements`
- `incompatible_wheels`
- `malformed_wheels`

## Updating lock and wheelhouse

1. Refresh lock file after dependency changes:

```bash
pip-compile --extra=dev --generate-hashes --allow-unsafe --strip-extras --output-file=requirements-lock.txt pyproject.toml
```

2. Rebuild wheels for Python 3.11 and re-run validation:

```bash
make wheelhouse-build
make wheelhouse-validate
```
