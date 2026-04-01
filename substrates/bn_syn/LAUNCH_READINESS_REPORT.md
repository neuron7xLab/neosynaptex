# Launch Readiness Report

## Scorecard

| Area | Status | Evidence |
|---|---|---|
| Install (`-e .`, `-e .[test]`) | PASS | `artifacts/audit/logs/step4_rerun.log` |
| Test gate (`make test-gate`) | PASS | `artifacts/audit/logs/step4_rerun.log` |
| Build (`make build`) | PASS | `artifacts/audit/logs/step4_rerun.log` |
| Wheel install smoke | PASS | `artifacts/audit/logs/wheel_install.log` |
| Docs (`make docs`) | PASS | `artifacts/audit/logs/make_docs.log` |
| Security (`make security`) | PASS | `artifacts/audit/logs/make_security.log` + `artifacts/pip-audit.json` |
| CI canonical targets alignment | PASS | `.github/workflows/ci-pr-atomic.yml`, `Makefile` |
| Release sanity (build artifact path) | PASS | `dist/bnsyn-0.2.0-py3-none-any.whl` generation in build log |

## Remaining Known Risks

1. `pip_audit` excludes local editable package (`bnsyn`) from PyPI advisory matching; this is expected for local package names and not a blocker. Owner: maintainers. Acceptance criterion: continue scanning transitive dependencies and monitor advisories during release.
2. Docs build emits warnings (non-fatal). Owner: docs maintainers. Acceptance criterion: optionally introduce warning budget and fail-on-warning policy in a dedicated hardening pass.

## Verification Commands

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -e ".[test]"
make test-gate
make build
make docs
make security
python -m venv .venv-wheel && source .venv-wheel/bin/activate && python -m pip install dist/*.whl && python -c "import bnsyn"
```
