# Test Taxonomy + Flake Elimination Orchestration — 2026-02-19

## 1) Inventory updates (targets/markers/config changed)

- **pytest markers currently registered**: `smoke`, `validation`, `benchmark`, `performance`, `integration`, `e2e`, `property`, `chaos`.
- **Canonical test entrypoints**:
  - `make test` (fast default, excludes `validation`, `property`, `e2e`)
  - `make test-all` (full suite)
  - `make test-integration`
  - `make test-e2e`
  - `make test-property`
- **CI fast-path alignment**:
  - `.github/workflows/ci-pr-atomic.yml` runs `make test`.

### Test taxonomy mapping

- **unit**: default tests under `tests/` without `validation/property/e2e` markers.
- **integration**: tests marked `@pytest.mark.integration`.
- **e2e**: tests marked `@pytest.mark.e2e` (CLI end-to-end smoke path).
- **property**: tests in `tests/properties/` with `@pytest.mark.property`.
- **chaos**: tests in `tests/validation/` with `@pytest.mark.chaos`.

## 2) Baseline results (failures + runtime)

### Environment
- `python --version` → `Python 3.12.12`
- `python -m pip --version` → `pip 25.3 (...)`
- `python -m pytest --version` captured in evidence logs.

### Baseline `make test` (before fixes)
- **Command**: `time make test`
- **Runtime**: `real 1m4.104s`
- **Failing tests**:
  - `tests/test_generate_inventory.py::test_inventory_json_matches_repository_state`
  - `tests/test_generate_inventory.py::test_build_inventory_render_matches_file`
- **Failure type**: assertion failures due stale generated artifact (`INVENTORY.json` docs count mismatch).

### Root-cause map

| failing test | suspected cause | determinism risk | proposed fix | proof plan |
|---|---|---|---|---|
| `test_inventory_json_matches_repository_state` | tracked docs count changed after docs edits, `INVENTORY.json` not regenerated | high | regenerate `INVENTORY.json` via canonical generator | rerun `make test` |
| `test_build_inventory_render_matches_file` | same stale generated file mismatch | high | regenerate `INVENTORY.json` via canonical generator | rerun `make test` |

## 3) Fixes applied (file list + rationale)

- `Makefile`
  - added canonical targets: `test-all`, `test-integration`, `test-e2e`.
  - updated default `TEST_CMD` to exclude `e2e` from fast path.
- `pyproject.toml`
  - registered `e2e` marker in pytest marker SSOT.
- `.github/workflows/ci-pr-atomic.yml`
  - switched fast test step to `make test` entrypoint.
- `tests/test_e2e_cli_smoke.py`
  - added deterministic e2e smoke test to prevent empty e2e bucket and enforce end-to-end CLI health.
- `docs/TESTING.md`, `README.md`
  - documented canonical split commands.
- `INVENTORY.json`
  - regenerated to fix deterministic generated-artifact drift that broke tests.

## 4) Verification commands + outputs (key lines)

- `time make test` → pass, `real 1m1.672s`.
- `time make test-all` → pass, `real 2m25.766s`.
- `make test-integration` → pass.
- `make test-e2e` → pass.
- `python -m pytest -m "not (validation or property)" -q` → pass.
- `ruff check .` and `mypy src --strict --config-file pyproject.toml` retained as compatible with test gate.

## 5) Gate status

- **G2 Tests**: **yes** (baseline failure fixed; canonical targets pass).
- **Flake risk**: **low** (failure was deterministic stale generated file, not intermittent timing randomness).
- **Runtime budget met**:
  - `make test` budget `<= 120s`: **yes** (`~62s`).
  - `make test-all` budget `<= 600s`: **yes** (`~146s`).

## 6) PR description scaffold

### WHAT
Standardized canonical pytest entrypoints (`test`, `test-all`, `test-integration`, `test-e2e`, `test-property`), added e2e marker/test, aligned CI fast path, and regenerated `INVENTORY.json` to resolve deterministic test failures.

### WHY
`make test` was red due stale generated inventory and there was no fully standardized split entrypoint surface for integration/e2e categories.

### EVIDENCE
See `proof_bundle/logs/22_*.log` through `proof_bundle/logs/36_*.log` for environment, baseline failures, fixes, and post-fix pass runs with runtimes.

### COMPATIBILITY
No product logic changes. Changes are test/build orchestration, generated inventory refresh, and a deterministic e2e smoke test.
