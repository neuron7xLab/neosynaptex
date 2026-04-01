# Production Readiness Dossier

## Status
FAIL (fail-closed): Gate G cannot be proven in this environment because Docker is unavailable.

## Assumptions Used
- Deployment target: Docker container on Linux amd64 (default).
- Runtime constraints: latest stable Python + one previous version (repo currently pins Python >=3.11).
- Security posture: no known critical vulnerabilities, secret scan, SAST, dependency audit.
- Release type: beta.
- Primary persona/JTBD: research engineers running deterministic phase-controlled neural simulation experiments.

## Project Summary
BN-Syn is a research-grade CLI package for deterministic phase-controlled emergent dynamics simulation with demos, experiment YAML execution, dt invariance checking, and sleep-stack workflows.

## Inventory Map
- Languages/frameworks: Python 3.11+ package (`pyproject.toml`, setuptools), Sphinx docs.
- Entry points: CLI (`bnsyn`, `python -m bnsyn`).
- Build system: Makefile as canonical command layer.
- Tests: pytest (+ markers validation/property), hypothesis.
- CI presence: GitHub Actions workflows.
- Deployment scaffolding: Dockerfile + docker-compose present, but not executable in this runtime.

Detailed directory inventory: `artifacts/prod_ready/reports/inventory_map.txt`.

## Canonical Commands (Verified)
- setup: `make setup`
- build: `python -m build`
- test: `python -m pytest -m "not validation" -q`
- lint: `ruff check .` and `pylint src/bnsyn`
- typecheck: `mypy src --strict --config-file pyproject.toml`
- docs: `make docs`
- security: `python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.`; `python -m pip_audit --desc`; `python -m bandit -r src/ -ll`
- run: `python -m bnsyn --help`; `bnsyn demo --steps 50 --dt-ms 0.1 --seed 123 --N 16`
- package: `python -m build` (wheel + sdist)
- deploy-local: blocked by missing Docker runtime in this environment.

## Gate Scorecard
| Gate | Result | Evidence |
|---|---|---|
| A Build & Run | PASS | `gateA_setup.log`, `gateA_build_rerun.log`, `gateA_cli_help.log`, `gateA_demo_smoke.log` |
| B Tests | PASS | `gateB_pytest_not_validation.log` |
| C Lint/Format/Static | PASS | `gateC_ruff_rerun.log`, `gateC_pylint_rerun.log`, `gateC_mypy.log` |
| D Security baseline | PASS | `gateD_gitleaks.log`, `gateD_pip_audit_final.log`, `gateD_bandit.log` |
| E Docs & onboarding truth | PASS | `gateE_docs_rerun.log`, `gateE_quickstart_smoke.log` |
| F Packaging/versioning/release | PASS | `gateA_build_rerun.log`, `gateF_package_install_smoke.log` |
| G Deployability | UNKNOWN | `gateG_docker_version.log` (docker command not found) |
| H Observability & operations | PASS | CLI smoke logs + troubleshooting/runbook docs in `docs/` and reproducible demo log |
| I Product readiness | PASS | This dossier + backlog + release/launch sections |

## P0/P1/P2 Backlog
### P0
1. Enable deployability proof in CI/container where Docker runtime is available.
   - Acceptance: `docker build` + smoke run + health/success signal captured under `artifacts/prod_ready/logs/`.

### P1
1. Reduce docs warning volume (224 warnings) to improve maintainability signal.
   - Acceptance: docs build completes with materially reduced warning count and tracked warning budget.

### P2
1. Add explicit healthcheck command/script for CLI runtime and package install smoke in Makefile.
   - Acceptance: `make deploy-local` and `make smoke` deterministic and documented.

## Risk Register
| Risk | Severity | Likelihood | Detection | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| Deploy path unproven in current runtime (no Docker executable) | High | Medium | `docker --version` fails | Run Gate G in Docker-capable runner; attach image digest + run log | Maintainer | Open |
| Docs warning debt obscures real regressions | Medium | High | `make docs` shows 224 warnings | Set warning baseline budget and burn-down plan | Docs owner | Open |
| Tool bootstrap drift on clean env | Medium | Medium | missing build/pylint/sphinx/pip-audit/bandit initially | Add dev/setup profile installing all gate tooling | Maintainer | Mitigated (local) |

## Beta→GA Release Plan
1. **Beta hardening (now)**: pass all gates except environment-limited Gate G; publish dossier + proof bundle.
2. **Pre-GA**: close Gate G with deterministic Docker smoke and health path; reduce docs warnings; establish SLO-oriented runbook.
3. **GA readiness**: lock reproducible toolchain manifest, green CI on canonical make targets, publish release notes/changelog, define rollback playbook.

Rollback plan: pin to prior known-good wheel version and previous tagged Docker image digest; revert release tag if smoke fails.

## Product Readiness (PM Bar)
- Positioning: deterministic bio-inspired simulation CLI for researchers exploring phase-controlled emergence and memory consolidation dynamics.
- Personas: computational neuroscientists, ML systems researchers, reproducibility auditors.
- JTBD: run deterministic experiment quickly; validate stability/invariance; produce interpretable artifacts.
- Primary flow acceptance criteria: install <=10 min, run demo, run YAML experiment, reproduce output with seed.
- Success metrics (beta): quickstart success rate, test-gate pass rate, reproducible demo parity by seed.
- Onboarding: `make setup`, `make demo`, `make test`, plus quickstart smoke proof.
- Distribution assumption: internal/beta Python package via wheel + source distribution.
- Launch checklist: release notes, changelog, gate evidence refresh, CI green, known-issues section.

## Remaining Blockers
1. Gate G deployability cannot be validated in this environment.
   - Next action: execute deploy-local commands in Docker-enabled runner and append logs to proof bundle.
