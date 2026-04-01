# BN-Syn Mathematical Surfaces (Implementation Scope Lock)

## Inputs

### A) Model types already defined in repo
- **BN-Syn Thermostated Bio-AI System** (`docs/SPEC.md` title; version v0.2.0).
- Component model surfaces explicitly defined by SPEC: AdEx neuron dynamics (P0-1), conductance synapses (P0-2), three-factor learning (P0-3), criticality control (P0-4), temperature gating (P1-5), consolidation (P1-6), energy regularization (P1-7), numerical methods (P2-8), determinism protocol (P2-9), calibration (P2-10), reference network simulator (P2-11), bench harness (P2-12).

### B) Mathematical Core module list (ONLY math modules touched)
- `src/bnsyn/neuron/adex.py`
- `src/bnsyn/synapse/conductance.py`
- `src/bnsyn/numerics/integrators.py`
- `src/bnsyn/criticality/branching.py`
- `src/bnsyn/rng.py`
- `src/bnsyn/sim/network.py`

### C) Artifact / metric formats relied upon
- `schemas/experiment.schema.json`
- `schemas/audit_reproducibility.schema.json`
- `schemas/readiness_report.schema.json`
- `schemas/attack_paths_graph.schema.json`
- Runtime summary metrics from `run_simulation()` (`sigma_mean`, `rate_mean_hz`, `sigma_std`, `rate_std`) in `src/bnsyn/sim/network.py`.
- Deterministic manifest + metrics artifacts under `artifacts/**` and `results/**` as documented in `docs/math/PROVENANCE.md`.

### D) Supported execution environments
- CPU-first environment is normative for v0.2.0 (`docs/SPEC.md`: “Scaling to large-N / GPU is explicitly out-of-scope”).
- Optional accelerator toggles exist in implementation (PyTorch/JAX extras), but are non-normative for deterministic CI.
- Python requirement: `>=3.11` (`pyproject.toml`).
- CI target shown in workflows: Ubuntu (`runs-on: ubuntu-latest`).
- OS support matrix beyond CI: **UNKNOWN** (source gap: no explicit OS compatibility matrix in SSOT docs).

### E) Explicit exclusions (scope guard)
- No UI/readme/branding edits.
- No dependency upgrades unless required by SSOT conflict.
- No new experiment families, metrics, invariants, or model parameters.
- No unrelated refactors/renames/format sweeps.
- No docs edits outside math/spec/ADR surfaces unless required for SSOT alignment.

## SSOT Order Used for This Hardening Pass
1. `docs/spec/**` (normative spec): **UNKNOWN / missing directory**; fallback to `docs/SPEC.md` with conflict note.
2. `schemas/**` machine contracts.
3. `claims/**` + `bibliography/**` claim/evidence constraints.
4. `quality/**` + `.github/WORKFLOW_CONTRACTS.md` + `docs/CI_GATES.md`.
5. `src/**` implementation.
6. Other `docs/**`.
7. Code comments.

## Numeric Environment Policy
- Default dtype for math core: `float64` (`numpy.float64`) in integration/state updates.
- Determinism policy uses explicit `numpy.random.Generator` seeding; no hidden global RNG.
- CI already sets `PYTHONHASHSEED=0` in PR workflows; deterministic behavior must not depend on hash-iteration randomness.
- No GPU required for conformance validation; CPU path is primary.
- Platform drift policy for tests:
  - use bounded `atol`/`rtol` from `tests/tolerances.py` for stochastic dt checks,
  - require exact-equality only for same-seed same-config deterministic summaries where implementation is purely deterministic.

## Spec↔Code Map (Math behaviors to implementation)
- AdEx membrane/adaptation Euler update + spike reset: `src/bnsyn/neuron/adex.py::adex_step`.
- AdEx overflow guard `exp_arg<=20`: `src/bnsyn/neuron/adex.py::adex_step` and `adex_step_adaptive`.
- NMDA magnesium block equation: `src/bnsyn/synapse/conductance.py::nmda_mg_block`.
- Exponential conductance decay `g(t+dt)=g(t)exp(-dt/tau)`: `src/bnsyn/numerics/integrators.py::exp_decay_step`; used by network/synapse modules.
- Euler/RK2 integrators: `src/bnsyn/numerics/integrators.py::{euler_step,rk2_step}`.
- Deterministic RNG seeding/splitting: `src/bnsyn/rng.py::{seed_all,split}`.
- Small-N deterministic simulator and bounded voltage guard: `src/bnsyn/sim/network.py::{Network.step,Network._raise_if_voltage_out_of_bounds,run_simulation}`.
- Criticality sigma estimate + gain control update path: `src/bnsyn/criticality/branching.py` and `src/bnsyn/sim/network.py`.

## Tolerance Triangle Policy (Operationalized)
- `rtol`: tied to relative comparison of stochastic summaries (`rate_mean_hz`) where scale varies with firing regime.
- `atol`: used on bounded sigma statistic (`sigma_mean`) where absolute drift is interpretable and expected to be small.
- dt-halving policy for current stochastic simulator:
  - Since Poisson drive and thresholded spiking reduce strict asymptotic order visibility in short runs, enforce bounded dt-vs-dt/2 deviation (existing CI-style invariant) instead of strict observed order ratio.
  - Exponential decay subcomponent still validated with exact half-step equivalence tests.

## Acceptance Criteria Applied
- Zero NaN/Inf in canonical smoke path summary metrics.
- Determinism: same seed + same params => identical metric payload.
- dt-halving bounded deviation (`rate_mean_hz` rtol and `sigma_mean` atol).
- Integrator guards reject invalid timesteps and non-finite outputs.
