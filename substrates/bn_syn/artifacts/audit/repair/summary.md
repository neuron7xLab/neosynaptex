# Launch Blocker Elimination Summary

## What changed

- Added a dedicated `docs` optional dependency group in `pyproject.toml` with pinned Sphinx toolchain packages (`sphinx`, `myst-parser`, `furo`, `sphinx-autodoc-typehints`, `sphinx-copybutton`).
- Hardened `make security` in `Makefile` to be reproducible on clean machines:
  - installs pinned dev security dependencies via `python -m pip install -e ".[dev]"`,
  - bootstraps pinned gitleaks via `python -m scripts.ensure_gitleaks`,
  - runs `python -m pip_audit --desc` and `python -m bandit -r src/ -ll`.
- Added `scripts/ensure_gitleaks.py`:
  - pinned version `v8.24.3`,
  - platform-aware archive selection,
  - SHA256 checksum verification,
  - local cache under `.tools/gitleaks/v8.24.3/`,
  - prints tool version and executes gitleaks command.
- Updated CI/workflows for truthfulness:
  - `.github/workflows/docs.yml` installs `.[test,docs]` before `make docs`,
  - `.github/workflows/ci-pr-atomic.yml` docs job installs `.[test,docs]`,
  - `.github/workflows/ci-pr-atomic.yml` security job runs `make security`.
- Updated operator docs:
  - `README.md` now documents `python -m pip install -e ".[test,docs]"` and includes `make docs` / `make security` in canonical local suites.
  - `docs/SECURITY_GITLEAKS.md` local testing now uses reproducible bootstrap (`make security` / `python -m scripts.ensure_gitleaks`).
  - Added `docs/BUILD_DOCS.md` with canonical build commands and expected artifact path.
  - Updated `SECURITY.md` with canonical local secret-scan command.
- Added `.tools/` to `.gitignore` for local bootstrap cache.

## Why

- Fixes launch blocker A (docs): `make docs` failed in a clean env due to missing Sphinx.
- Fixes launch blocker B (security): `make security` previously depended on external preinstalled `gitleaks` binary.
- Ensures local commands match CI behavior and remain deterministic/pinned.

## Exact reproduction commands

```bash
# Baseline failure reproduction
python -m venv artifacts/audit/repair/.venv
source artifacts/audit/repair/.venv/bin/activate
python -m pip install -e ".[test]"
make test-gate
make docs      # pre-fix failed in baseline log
make security  # pre-fix failed in baseline log

# Post-fix verification matrix
python -m venv artifacts/audit/repair/.venv-fixed
source artifacts/audit/repair/.venv-fixed/bin/activate
python -m pip install -e .
python -m pip install -e ".[test,docs]"
python -m pytest --collect-only -q
make test-gate
make docs
test -f docs/_build/html/index.html
make security
python -m pip install build
python -m build
```

## Evidence pointers

- Baseline reproduction (pre-fix failures):
  - `artifacts/audit/repair/logs/01_baseline_repro.log`
- Post-fix verification matrix:
  - `artifacts/audit/repair/logs/02_verify_after_fix.log`
- Security clean-machine reproducibility (bootstrap + tool versions + pass):
  - `artifacts/audit/repair/logs/03_security_recheck.log`
- Post-fix security + build smoke:
  - `artifacts/audit/repair/logs/04_postfix_security_build.log`

## Compatibility notes

- Python: verified on 3.12.12.
- OS: verified on Linux x86_64.
- Gitleaks bootstrap support in script:
  - Linux: x86_64, aarch64
  - macOS: x86_64, arm64
- Tool cache path: `.tools/gitleaks/v8.24.3/gitleaks`.

## Scope expansion justification

- Added `scripts/ensure_gitleaks.py` and `.gitignore` update to make local security checks self-bootstrapping and reproducible.
- Added `docs/BUILD_DOCS.md` to make docs build path discoverable as a canonical operator command.

## Remaining known risks

- `make docs` emits Sphinx deprecation warnings from `sphinx-autodoc-typehints` integration, but build completes and outputs HTML.
  - Evidence: `artifacts/audit/repair/logs/02_verify_after_fix.log`.
- `python -m pip_audit --desc` reports local package `bnsyn` as "Dependency not found on PyPI" skip reason; no vulnerabilities found.
  - Evidence: `artifacts/audit/repair/logs/03_security_recheck.log`, `artifacts/audit/repair/logs/04_postfix_security_build.log`.
