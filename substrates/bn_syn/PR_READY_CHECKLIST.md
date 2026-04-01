# PR Ready Checklist

| Gate | Status | Evidence |
|---|---|---|
| Build/package | PASS | `python -m build --sdist --wheel` succeeded. log:`PROOF_BUNDLE/logs/python_build.log` |
| Tests | PASS | `make test` passed after installing test extras. log:`PROOF_BUNDLE/logs/make_test_after_install.log` |
| Lint | FAIL | `ruff check .` returned violations. log:`PROOF_BUNDLE/logs/ruff_check.log` |
| Type check | PASS | `python -m mypy src --strict --config-file pyproject.toml` succeeded. log:`PROOF_BUNDLE/logs/mypy.log` |
| Security scan (`pip-audit`) | UNKNOWN | Tool unavailable: `No module named pip_audit`. log:`PROOF_BUNDLE/logs/pip_audit_version.log` |
| Security scan (`bandit`) | UNKNOWN | Tool unavailable: `command not found`. log:`PROOF_BUNDLE/logs/bandit_version.log` |
| Migrations safety | UNKNOWN | No DB migration changes in this patch; migration gate not applicable to changed files. |
| Documentation updated | PASS | Added required execution artifacts and evidence bundle index files. |

## Stop-Ship Evaluation
- **NOT READY** for merge under strict gates because lint is failing and security scan evidence is incomplete (UNKNOWN).
