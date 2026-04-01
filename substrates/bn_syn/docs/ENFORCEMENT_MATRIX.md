# Enforcement Matrix

Single normalized mapping between SSOT requirements and verification.

| Requirement | Source (SSOT path) | Enforcement mechanism | Command to verify | Failure mode |
|---|---|---|---|---|
| Smoke test suite must pass (exclude `validation`) | AGENTS.md | Make target + pytest marker policy | `python -m pytest -m "not validation" -q` | non-zero exit from pytest |
| Ruff lint must pass | AGENTS.md, Makefile | `make lint` subcommand | `ruff check .` | non-zero exit from ruff |
| Pylint quality gate must pass | AGENTS.md, pyproject.toml | `make lint` subcommand | `pylint src/bnsyn` | non-zero exit from pylint |
| Strict typecheck must pass | AGENTS.md, pyproject.toml | `make mypy` | `mypy src --strict --config-file pyproject.toml` | non-zero exit from mypy |
| Build must be installable | AGENTS.md, .github/workflows/ci-pr-atomic.yml | package build gate | `python -m build` | non-zero exit from build |
| Traceability table must be machine-parseable | docs/TRACEABILITY.md | `scripts/validate_traceability.py` | `python -m scripts.validate_traceability` | non-zero exit from validator |
| Public surfaces doc must be generated deterministically | pyproject.toml, src/bnsyn/__init__.py, schemas/** | `scripts/discover_public_surfaces.py` | `python -m scripts.discover_public_surfaces` | generated doc missing/inconsistent |
| Core docs must keep valid internal repo-relative links | README.md, docs/INDEX.md, docs/TRACEABILITY.md | `scripts/check_internal_links.py` | `python -m scripts.check_internal_links` | non-zero exit from link checker |
| Coverage threshold governance is inherited from existing baseline | docs/TESTING.md, quality/coverage_gate.json | existing coverage gate only | `python -m scripts.check_coverage_gate --coverage-xml coverage.xml --baseline quality/coverage_gate.json` | non-zero exit from coverage gate |

## Coverage policy
- Threshold already exists in `quality/coverage_gate.json`; inherited as-is.
- `NO_THRESHOLD` is not applicable.
