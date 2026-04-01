# Architecture & Invariants

This page defines runtime invariants and safety boundaries for core modules.

## Core modules

- `bnsyn.validation.inputs`: strict boundary validators for array shape/dtype/finiteness.
- `bnsyn.schemas.experiment`: declarative config schema and admissible simulation grid.
- `bnsyn.sleep.cycle`: wake/sleep orchestration with deterministic stage transitions.
- `bnsyn.provenance.manifest_builder`: deterministic manifest metadata capture.

## Invariants

### Input validation invariants

- State vectors must be `np.ndarray`, `float64`, shape `(N,)`, finite (no NaN/Inf).
- Spike vectors must be `np.ndarray`, `bool`, shape `(N,)`.
- Connectivity matrices must be `np.ndarray`, `float64`, exact expected shape, finite.

Failure mode:
- Raises `TypeError` for non-array API boundary values.
- Raises `ValueError` for dtype/shape/non-finite constraint violations.

### Experiment schema invariants

- `experiment.name` must match `^[a-z0-9_-]+$`.
- `experiment.version` must match `^v[0-9]+$`.
- `experiment.seeds` must be unique positive integers.
- `simulation.dt_ms` must be one of: `0.01, 0.05, 0.1, 0.5, 1.0`.
- `simulation.duration_ms / dt_ms` must be integral within tolerance.

Failure mode:
- Raises `pydantic.ValidationError` with explicit constraint message.

### Sleep cycle invariants

- `wake(duration_steps)` requires `duration_steps > 0`.
- If memory recording is enabled, `record_interval` must be a positive integer.
- Stage callbacks trigger exactly on stage transitions.

Failure mode:
- Raises `ValueError` for invalid step or interval parameters.

### Provenance invariants

- `git` SHA capture must use fixed non-shell command.
- If git metadata is unavailable, fallback identifier is deterministic: `release-<version>`.
- Manifest excludes `manifest.json` self-hash recursion.

Failure mode:
- Emits `UserWarning` and falls back without failing experiment generation.

## Determinism controls

- Hypothesis test generation is derandomized via project config.
- Tests use fixed seeds for simulation reproducibility.
- Fuzz-style validator test uses fixed RNG seed and bounded iterations.
