# Regime Controller Specification

Claim status: `compute_gamma` = TESTED OPERATIONAL_PROXY; biological meaning of gamma = HYPOTHESIS.

## State variables
weights, grad, activations, entropy, gamma, velocity, gate_signal, rest_phase.

## Update equation
`activations -> compute_gamma -> gate(gamma, entropy) -> adaptive_update(weights, grad, gate_signal)`.

## Domains
- entropy: any float input, clipped to [0,1] in diagnostics.
- gate_signal: [0,1].
- learning_rate: >=0.
- weights/grad: same shape.

## Invalid states and fail-closed behavior
- non-finite/short activations: `compute_gamma` returns NaN; controller uses `gamma_target`.
- non-finite gamma input to gate: raise ValueError.
- non-finite gate_signal: raise ValueError.
- negative learning_rate: raise ValueError.
- mismatched weights/grad shapes: raise ValueError.

## Traceability matrix
| spec req | invariant | test | impl |
|---|---|---|---|
| short/non-finite activations handled | I-RGM-1 | test_compute_gamma_rejects_short_or_non_finite | src/bnsyn/regime.py::compute_gamma |
| entropy threshold enforces rest bias | I-RGM-2 | test_regime_gate_enforces_entropy_rest | src/bnsyn/regime.py::RegimeGate.gate |
| shape contract enforced | I-RGM-3 | test_adaptive_update_contracts | src/bnsyn/regime.py::adaptive_update |
| controller emits diagnostics | I-RGM-4 | test_regime_controller_step_contract | src/bnsyn/regime.py::RegimeController.step |
