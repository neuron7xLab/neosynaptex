# ADR 0001: Math integrator finite/step guardrails

## Context / problem
The numerical core relied on Euler/RK2/exp-decay helpers without explicit finite-step validation. Invalid `dt`/`tau` or non-finite intermediate values could propagate NaN/Inf into downstream summaries before failing.

## Decision
Add strict input/output finite checks in `src/bnsyn/numerics/integrators.py`:
- Euler/RK2 require finite positive `dt`.
- Exponential decay requires finite non-negative `dt` and finite positive `tau`.
- All integrators coerce to `float64` and fail fast if output contains non-finite values.

## Expected numerical effect (stability/error)
No equation changes; this is a fail-closed safety hardening. Semantics are preserved for valid finite inputs while preventing silent NaN/Inf propagation.

## Tests added/updated
- `tests/test_math_core_hardening.py` (new): finite-smoke checks, dt-halving bounded check, and invalid-input/NaN guard tests for integrators.
- `tests/test_determinism.py` (updated): subprocess reproducibility across different `PYTHONHASHSEED` values.

## Compatibility impact
No public API/schema/metric-key changes. Behavior only differs for invalid/non-finite numeric inputs, which now raise deterministic `ValueError` earlier.
