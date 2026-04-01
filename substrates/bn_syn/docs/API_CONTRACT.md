# BN-Syn API Contract

This document defines the public API surface of BN-Syn and identifies stable vs internal interfaces.

## Stable Public API (Supported)

The following modules are considered stable for external use and are covered by documentation and CI:

- `bnsyn.config`
- `bnsyn.rng`
- `bnsyn.cli`
- `bnsyn.neurons` (alias for `bnsyn.neuron`)
- `bnsyn.synapses` (alias for `bnsyn.synapse`)
- `bnsyn.control` (criticality + temperature + energy control utilities)
- `bnsyn.simulation` (alias for `bnsyn.sim.network`)
- `bnsyn.sim.network`
- `bnsyn.neuron.adex`
- `bnsyn.synapse.conductance`
- `bnsyn.plasticity.three_factor`
- `bnsyn.criticality.branching`
- `bnsyn.temperature.schedule`
- `bnsyn.connectivity.sparse`

Recommended import style:

```python
from bnsyn import config, rng
from bnsyn.simulation import Network, NetworkParams, run_simulation
from bnsyn.neurons import adex_step
from bnsyn.synapses import ConductanceSynapses
```

## Stable Function Contracts

The following functions/classes have stable signatures and semantic meaning:

- `bnsyn.neuron.adex.adex_step` / `bnsyn.neurons.adex_step`  
  Integrates AdEx neuron dynamics for one timestep. Parameters define membrane state,
  currents, and timestep in milliseconds. Deterministic for fixed inputs.
- `bnsyn.synapse.conductance.ConductanceSynapses` / `bnsyn.synapses.ConductanceSynapses`  
  Implements conductance-based synapse dynamics with delayed buffering.
- `bnsyn.plasticity.three_factor.three_factor_update`  
  Implements three-factor plasticity updates (eligibility × neuromodulator).
- `bnsyn.criticality.branching.BranchingEstimator` and `SigmaController`  
  Implements sigma tracking and gain control.
- `bnsyn.temperature.schedule.TemperatureSchedule` and `gate_sigmoid`  
  Implements temperature scheduling and gating.
- `bnsyn.sim.network.Network` / `bnsyn.simulation.Network`  
  Reference network dynamics used for determinism and integration tests.
- `bnsyn.rng.seed_all`  
  Seeds deterministic RNG sources.

## Determinism Guarantees

The following operations are deterministic when provided identical inputs and RNG seeds:

- `bnsyn.rng.seed_all` and all functions that accept explicit `np.random.Generator` objects.
- `bnsyn.sim.network.run_simulation` and `Network.step` for fixed parameters and seed.
- `bnsyn.neuron.adex` integration helpers (`adex_step`, `adex_step_with_error_tracking`).

## Allowed to Change Without Notice

The following may change without breaking the API contract:

- Internal helper modules not listed in the stable API.
- Logging, diagnostics, and performance optimizations that do not alter semantics.
- Documentation layout, as long as API content remains accurate.

## Internal / Private Modules (Not Stable)

Modules not listed above are considered internal and may change without notice. Internal modules may be used
in tests or experiments but are not part of the public API contract.

## References

- [SPEC](SPEC.md)
- [SSOT](SSOT.md)
- [REPRODUCIBILITY](REPRODUCIBILITY.md)
