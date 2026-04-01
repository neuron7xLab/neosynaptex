# Project Operating Contract for Agents
## Mission & Non-Goals
- Mission: complete pseudo-structures into real implementations, maintain intended behavior.
- Non-Goals: feature expansion, refactors beyond necessity, style rewrites, dependency churn.

## Repo Truth Sources (Priority Order)
1) Existing architecture docs (docs/**, ADRs, README)
2) Source code contracts/types (src/**, schemas)
3) Tests
4) CI configs
5) Issues/PR description (if present)

## Definition of “Pseudo-structure”
- Any placeholder that suggests intended capability but is not implemented or is non-functional:
  TODO/FIXME/WIP, NotImplementedError, stub returns, mocked production paths, empty handlers, “pass”, placeholder configs, fake data pipelines, skeleton modules without integration, unhooked CLI commands, dead code behind flags with no path.

## Allowed Changes
- Implement missing logic within intended modules only.
- Add/adjust tests to validate implementations.
- Minimal doc updates required for comprehension.
- Minimal config fixes needed to run checks.

## Forbidden Changes
- Changing product logic/requirements.
- Large-scale rewrites, renaming sprees, style-only diffs.
- Introducing new external services without explicit repo precedent.
- Disabling tests/linters/typechecks.

## Canonical Vectors and Anti-Drift
- V1 Result: keep `bnsyn run --profile canonical --plot --export-proof` as the single canonical proof command.
- V2 Narrative: keep README + docs/CANONICAL_PROOF.md aligned with mechanism (AdEx + STDP + criticality), measurable outputs, and reproducibility.
- V3 Audience: keep clone->install->`bnsyn run --profile canonical --plot --export-proof`->inspect path obvious for external technical reviewers.
- Canonical artifact contract for `bnsyn run --profile canonical --plot --export-proof`: `emergence_plot.png`, `summary_metrics.json`, `criticality_report.json`, `avalanche_report.json`, `phase_space_report.json`, `population_rate_trace.npy`, `sigma_trace.npy`, `coherence_trace.npy`, `phase_space_rate_sigma.png`, `phase_space_rate_coherence.png`, `phase_space_activity_map.png`, `avalanche_fit_report.json`, `robustness_report.json`, `envelope_report.json`, `run_manifest.json`, `proof_report.json`.
- Treat changes that obscure or fragment canonical proof path as drift.

## Tooling & Commands (Project-Specific)
- Tests: `python -m pytest -m "not (validation or property)" -q` (Makefile `test`, used by CI reusable pytest workflows)
- Linters: `ruff check .` and `pylint src/bnsyn` (Makefile `lint`)
- Typechecks: `mypy src --strict --config-file pyproject.toml` (Makefile `mypy`)
- Build: `python -m build` (CI workflow `ci-pr-atomic.yml`)

## Evidence & Logging Standard
- All commands must be logged under proof_bundle/logs/.
- All key findings must have evidence pointers (file:line, or cmd log).
- No evidence => treat as unknown and do not claim.

## Human-in-the-loop Review Points
- Before first major implementation batch
- Before final PR ready claim
