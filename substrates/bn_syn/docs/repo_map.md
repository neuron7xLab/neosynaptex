# Repository Map

## Purpose
This map provides a fast routing guide to core code, operational scripts, and governance artifacts in this repository.

## Canonical Directory Map

| Path | Purpose | Stability |
|---|---|---|
| `src/bnsyn/` | Runtime simulation, CLI entrypoints, and deterministic model implementation. | Stable public implementation |
| `src/contracts/` | Assertion-style mathematical contracts used for validation invariants. | Stable validation API |
| `scripts/` | Operational automation (validation, benchmark, governance, release readiness, docs checks). | Mixed; review script-level safety |
| `tests/` | Pytest suite (smoke, validation, property, integration, performance). | Stable quality gate |
| `benchmarks/` | Benchmark harnesses, scenarios, baselines, and reporting utilities. | Evolving (performance-focused) |
| `docs/` | Sphinx source docs, architecture references, governance, and runbooks. | Stable, continuously updated |
| `.github/workflows/` | CI/CD and quality-gate automation definitions. | Stable policy surface |
| `schemas/` | JSON schemas for artifacts and readiness reports. | Stable contract surface |
| `entropy/` | Entropy/quality tracking policies and guard scripts. | Experimental/governance tooling |
| `proof_bundle/` | Command logs, repo-state snapshot, inventory, and hashes for this documentation formalization run. | Generated evidence artifact |

## Where to Find X

| If you need... | Go to... |
|---|---|
| Run the simulator from CLI | `src/bnsyn/cli.py` and `README.md` |
| Understand architecture and boundaries | `docs/ARCHITECTURE.md` + `docs/repo_map.md` |
| Follow operational workflows | `docs/usage_workflows.md` |
| Locate all scripts and safe usage guidance | `scripts/README.md` + `docs/scripts/index.md` |
| Inspect mathematical validation contracts | `src/contracts/math_contracts.py` + `docs/contracts/index.md` |
| Build docs locally | `docs/BUILD_DOCS.md` + `make docs` |
| Validate claims/evidence governance | `scripts/validate_claims.py` + `docs/EVIDENCE_COVERAGE.md` |
| Review release readiness automation | `scripts/release_readiness.py` + `docs/RELEASE_READINESS.md` |

## Notes
- Stability labels are documentation-level guidance; authoritative behavior remains source code.
- Script-level mutation risk is documented per script page under `docs/scripts/`.
