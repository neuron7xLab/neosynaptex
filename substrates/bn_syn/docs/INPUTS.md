# Inputs and Boundaries

## Domain inputs
- CLI numeric controls (`--steps`, `--dt-ms`, `--seed`, `--N`) are accepted by `src/bnsyn/cli.py`.
- Declarative experiment YAML is validated against `schemas/experiment.schema.json` in `src/bnsyn/experiments/declarative.py`.

## Math core boundaries
- Integrators and neuron/synapse dynamics live under `src/bnsyn/numerics/`, `src/bnsyn/neuron/`, `src/bnsyn/synapse/`.
- Contracts for numerical safety checks are in `src/contracts/math_contracts.py`.

## Artifact formats
- Experiment config contract: `schemas/experiment.schema.json`.
- Readiness contract: `schemas/readiness_report.schema.json`.
- Audit reproducibility contract: `schemas/audit_reproducibility.schema.json`.
- Attack-path graph contract: `schemas/attack_paths_graph.schema.json`.

## Supported platforms / constraints
- Required Python: `>=3.11` (`pyproject.toml`).
- Optional accelerator extras exist (`jax`, `torch`) and are non-mandatory (`pyproject.toml`).
- MISSING: explicit CPU architecture support matrix.
  - DERIVE FROM: CI runner matrix in `.github/workflows/*.yml`.
  - ACTION: add supported CPU/OS matrix to `docs/MAINTENANCE.md` once SSOT owner confirms scope.
