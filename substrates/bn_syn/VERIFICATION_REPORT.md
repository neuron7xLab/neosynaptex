# Verification Report

## Scope
- Change type: documentation/evidence artifacts only.
- Runtime target: local Linux container, Python toolchain.

## Executed Commands & Results

1) Repo identity capture  
- cmd:`timeout 600 bash -lc 'echo "branch=$(git branch --show-current)"; echo "sha=$(git rev-parse HEAD)"; echo "status:"; git status --short'`  
- log:`PROOF_BUNDLE/logs/git_identity.log`  
- exit:`0` timeout:`600s`

2) Toolchain fingerprint capture  
- cmd:`timeout 600 bash -lc 'echo "os=$(uname -srm)"; echo "python=$(python --version 2>&1)"; echo "pip=$(pip --version 2>&1)"; echo "pytest=$(python -m pytest --version 2>&1 | head -n 1)"; echo "git=$(git --version)"'`  
- log:`PROOF_BUNDLE/logs/toolchain_raw.log`  
- exit:`0` timeout:`600s`

3) Lockfile hash capture  
- cmd:`timeout 600 bash -lc 'for f in pyproject.toml uv.lock poetry.lock requirements.txt requirements-dev.txt; do if [ -f "$f" ]; then sha256sum "$f"; fi; done'`  
- log:`PROOF_BUNDLE/logs/lockfile_hashes.log`  
- exit:`0` timeout:`600s`

4) Lint gate  
- cmd:`timeout 600 bash -lc 'ruff check .'`  
- log:`PROOF_BUNDLE/logs/ruff_check.log`  
- exit:`1` timeout:`600s`  
- result: **FAIL** (pre-existing violations reported by Ruff).

5) Unit/default tests (pre-install attempt)  
- cmd:`timeout 600 bash -lc 'make test'`  
- log:`PROOF_BUNDLE/logs/make_test.log`  
- exit:`1` timeout:`600s`  
- result: **FAIL** due to missing `hypothesis`, `yaml`, and `psutil`.

6) Install test extras  
- cmd:`timeout 600 bash -lc 'python -m pip install -e ".[test]"'`  
- log:`PROOF_BUNDLE/logs/pip_install_test.log`  
- exit:`0` timeout:`600s`

7) Unit/default tests (post-install)  
- cmd:`timeout 600 bash -lc 'make test'`  
- log:`PROOF_BUNDLE/logs/make_test_after_install.log`  
- exit:`0` timeout:`600s`  
- result: **PASS**.

8) Type check  
- cmd:`timeout 600 bash -lc 'python -m mypy src --strict --config-file pyproject.toml'`  
- log:`PROOF_BUNDLE/logs/mypy.log`  
- exit:`0` timeout:`600s`  
- result: **PASS**.

9) Build check  
- cmd:`timeout 600 bash -lc 'python -m pip install build && python -m build --sdist --wheel'`  
- log:`PROOF_BUNDLE/logs/python_build.log`  
- exit:`0` timeout:`600s`  
- result: **PASS** (sdist/wheel generated).

10) Security tooling presence checks  
- cmd:`timeout 600 bash -lc 'python -m pip_audit --version'`  
- log:`PROOF_BUNDLE/logs/pip_audit_version.log`  
- exit:`1` timeout:`600s`  
- result: **UNKNOWN** (tool missing in environment).  

- cmd:`timeout 600 bash -lc 'bandit --version'`  
- log:`PROOF_BUNDLE/logs/bandit_version.log`  
- exit:`1` timeout:`600s`  
- result: **UNKNOWN** (tool missing in environment).

## Test Matrix
- Unit/default suite (`make test`): PASS after dependency installation.
- Integration/e2e: covered implicitly by repository default `make test` selection; no standalone e2e command discovered.
- Build/package: PASS.

## Regressions Check
- No source-code behavior changes were introduced in this patch.
- Existing lint/security-tooling gaps are documented; no silent bypass was applied.

## Reproducibility Artifacts
- Command index: `PROOF_BUNDLE/commands_executed.txt`
- Toolchain fingerprint: `PROOF_BUNDLE/toolchain_fingerprint.txt`
- Audit hash: `PROOF_BUNDLE/audit_hash.txt`
