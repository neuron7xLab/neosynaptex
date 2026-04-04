#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "[validation-preflight] ERROR: $1" >&2
  exit 1
}

info() {
  echo "[validation-preflight] $1"
}

info "Checking required toolchain"
command -v python >/dev/null 2>&1 || fail "python is not available in PATH"
command -v pylint >/dev/null 2>&1 || fail "pylint is not installed or not in PATH"

info "Running strict mypy gate"
python -m mypy src --strict --config-file pyproject.toml || fail "mypy strict gate failed (see logs above)"

info "Running packaging build gate"
python -m build || fail "python -m build failed (install 'build' package and inspect build logs)"

info "Running smoke pytest collection/execution gate"
python -m pytest -m "not (validation or property)" -q || fail "pytest smoke gate failed (import/collection/runtime issue)"

info "All validation-preflight gates passed"
