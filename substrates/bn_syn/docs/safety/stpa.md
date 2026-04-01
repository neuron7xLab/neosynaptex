# System-Theoretic Process Analysis (STPA)

**Navigation**: [INDEX](../INDEX.md)

## Losses (L)

- **L1**: Loss of deterministic, reproducible simulation outputs.
- **L2**: Loss of safe bounded dynamics (unstable or invalid state propagation).
- **L3**: Loss of memory consistency across model updates.

## Control Structure (Minimal)

- **Controllers**: CLI/API entrypoints, experiment runners, configuration loaders.
- **Controlled Process**: Network simulation step (`Network.step`/`step_adaptive`) and memory updates.
- **Sensors/Feedback**: Metrics returned from steps (sigma, gain, spike rate), validation errors, test telemetry.
- **Actuators**: Parameter updates (criticality gain, external current injection), configuration defaults.

## Hazards (H)

- **H1**: Invalid external arrays (shape/dtype/NaN) enter the system state.
- **H2**: Network configuration or external current bounds are invalid at runtime.
- **H3**: RNG seeding drift or missing seed propagation breaks determinism.
- **H4**: Nondeterministic execution from thread-level parallelism or BLAS settings.
- **H5**: NaN/Inf propagation in dynamics due to missing runtime numeric health checks.

## Unsafe Control Actions (UCA)

- **UCA1**: Accepting state/connectivity arrays without validating dtype, shape, or NaN.
- **UCA2**: Creating a network with invalid parameters (non-positive N, invalid fractions, non-positive dt).
- **UCA3**: Accepting external current vectors with mismatched shapes.
- **UCA4**: Omitting or diverging RNG seed propagation across simulation entrypoints.
- **UCA5**: Allowing uncontrolled thread/BLAS parallelism that alters numeric results.
- **UCA6**: Continuing simulation updates when NaN/Inf values are present in state.

## Safety Constraints (SC)

- **SC-1**: External arrays **must** be validated for dtype, shape, and NaN presence before use.
- **SC-2**: Network initialization **must** reject invalid parameters and external current shapes.
- **SC-3**: All stochastic execution **must** use explicit seed control and reproducible RNG streams.
- **SC-4**: Threaded or BLAS execution **must** be bounded to deterministic settings.
- **SC-5**: Runtime numeric health checks **must** fail closed on NaN/Inf state.

## Enforcement & Test Mapping

| Safety Constraint | Enforcement (Code) | Tests | Gate | Status |
| --- | --- | --- | --- | --- |
| SC-1 | `bnsyn.validation.inputs` validators | `tests/test_validation_inputs.py` | `pytest -q` | enforced |
| SC-2 | `Network.__init__` and `Network.step` validation | `tests/test_network_validation_edges.py`, `tests/test_network_external_input.py` | `pytest -q` | enforced |
| SC-3 | `bnsyn.rng.seed_all` | `tests/properties/test_properties_determinism.py` | `pytest -m property` | enforced |
| SC-4 | _unmitigated_ | _unmitigated_ | _unmitigated_ | unmitigated |
| SC-5 | _unmitigated_ | `tests/validation/test_chaos_numeric.py` (numeric health utilities only) | _unmitigated_ | unmitigated |

## Notes

Safety constraints are enforced at API boundaries to prevent invalid data from
propagating into dynamics or memory updates. The test suite provides regression
coverage for these boundaries under deterministic seeds.
