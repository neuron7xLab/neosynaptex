# Contracts Documentation

## Conceptual Overview
`src/contracts` contains machine-checkable assertion helpers for mathematical and numerical invariants used throughout BN-Syn validation workflows. Contracts are designed to fail fast via `AssertionError` with structured messages that identify violated preconditions.

## What Contracts Validate
- Input sanity (`assert_non_empty_text`, finite/bounded numeric ranges).
- Numerical stability constraints (`assert_dt_stability`, integration tolerance coherence).
- State and metric validity (finite states, energy monotonicity/bounds, phase/range correctness).
- Matrix/data integrity (adjacency binary constraints, matrix symmetry, probability normalization, dataset quality checks).

## Extension Guidance
When adding a new contract:
1. Keep behavior side-effect free.
2. Raise `AssertionError` with diagnostic tokens suitable for automated parsing.
3. Add docstrings with intent, invariants, and failure semantics.
4. Add tests to `tests/` verifying both pass and fail paths.

## API Reference
- [contracts package API](../api/generated/contracts.rst)
- [contracts.math_contracts module API](../api/generated/contracts.math_contracts.rst)
