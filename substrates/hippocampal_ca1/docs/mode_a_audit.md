# MODE A — Memory Core Audit & Deterministic Harness Prep

Date: 2025-12-18  
Owner: Copilot SWE Agent

## 1) Memory Core Boundary (CA1/LAM)

- **Core namespace (`core/`)**: public API exported via `core/__init__.py` (e.g., `CA1Network`, `SimulationResult`, config helpers, contracts, invariants, metrics).  
- **State contracts**: `MemoryState`, `EncodeInput`, `RecallQuery`, `RecallResult`, `UpdateInput`, `SimulationConfig` (shape/seed explicitly carried).  
- **Execution surfaces**:
  - Simulation: `CA1Network.simulate(duration_ms, dt=None)` → `dict(time, spikes, voltages, weights)` (seeded RNG, no global state; `dt` defaults to constructor value).  
  - Configuration: `create_deterministic_config`, `validate_config`, `merge_configs`, YAML/JSON loaders.  
  - Guards: `set_guards_enabled/guards_enabled`, invariant helpers (`check_shape_*`, `check_finite`, `check_bounded`, `check_spectral_radius`, etc.).  
  - Metrics: `compute_report` with stable `REPORT_KEYS` (`capacity_proxy`, `stability`, `weight_stats`, `activation_stats`, `recall_accuracy_cosine`, `recall_accuracy_overlap`, `weight_drift_relative`, `weight_drift_max`, `finite_weights`, `finite_activations`, `spectral_radius_safe`).  
- **Side-effects**: none beyond seeded `numpy` RNG inside `CA1Network`; plotting only when `matplotlib` is imported ad hoc.

## 2) Public vs Internal Interfaces

- **Public (stable)**: symbols re-exported from `core/__init__.py` (above), config objects, contracts, and invariant guards.  
- **Internal (keep encapsulated)**: helper shapes/utility functions inside `laminar_structure.py`, `hierarchical_laminar.py`, `neuron_model.py`, and `theta_swr_switching.py` that are **not** re-exported; private RNG/state on `CA1Network` (`_rng`, `_weights`, `_last_result`).  
- **Cross-boundary imports**: `ai_integration/` and `plasticity/` should depend on `core` only; no reverse imports allowed (currently clean).

## 3) System Invariants (determinism & safety)

- **Shape-safety**: `check_shape_1d/2d`, `check_square_matrix`, `validate_memory_state`.  
- **Finite-safety**: `check_finite`, `check_no_nan`; tests assert no NaN/Inf in outputs.  
- **Bounds**: `check_bounded`, `check_non_negative`; weights constrained via contracts/config (`weight_min/max`).  
- **Spectral stability**: `check_spectral_radius` + metrics track `ρ(W)`.  
- **Determinism**: seeded RNG (`SimulationConfig.seed`, `CA1Network` constructor). `TestDeterminism` in `tests/test_core_contracts.py` asserts identical outputs for same seed.  
- **Runtime guards**: global toggle via `set_guards_enabled`; defaults to enabled in debug paths.  
- **Shape/state limits**: state dimensions fixed by contracts; traces optional and bounded via explicit arrays.

## 4) Deterministic Harness (ready-to-use)

- **Quick run** (seeded, guard-on; `PYTHONPATH=.` keeps the repo root on the module search path when the package is not installed):
  ```bash
  PYTHONPATH=. pytest -q tests/test_core_contracts.py tests/test_config.py
  ```
  (Covers determinism, shape/finite safety, config reproducibility.)
- **Programmatic entry**:
  ```python
  from core import CA1Network, create_deterministic_config, set_guards_enabled

  set_guards_enabled(True)
  cfg = create_deterministic_config(seed=42, n_neurons=64)
  net = CA1Network(N=cfg.core.n_neurons, seed=cfg.core.seed, dt=cfg.core.dt)
  result = net.simulate(duration_ms=int(cfg.core.duration_ms))
  ```
- **Toggle guards**: `set_guards_enabled(False)` only for perf-critical runs; tests rely on guards being **on**.

## 5) Failure Map (risks to determinism/safety)

- **Seed drift**: constructing RNGs outside the provided `seed`/config flow; mitigation is centralizing seed injection.  
- **Guard bypass**: disabling `_GUARDS_ENABLED` hides shape/finite violations; CI should run with guards on.  
- **Unbounded state**: writing long traces (`trace` optional) without caps can grow memory.  
- **Silent API divergence**: changing return keys from `CA1Network.simulate` or `compute_report` breaks tests/consumers.  
- **External randomness**: downstream modules using `np.random` directly without `Generator` seeded from config.  
- **Config skew**: loading configs without validation (`validate_config`) can admit invalid `theta_frequency`, `spectral_radius_target`, etc.

## 6) Roadmap — 3–5 small PRs

1. **CI Deterministic Harness Gate**  
   - Scope: Add dedicated CI job running `PYTHONPATH=. pytest -q tests/test_core_contracts.py tests/test_config.py` with guards explicitly forced on (e.g., fixture calling `set_guards_enabled(True)`).  
   - Risk: Low (test-only).  
   - Metrics: Pass/fail; runtime < 2 min.

2. **Seed Propagation Adapter**  
   - Scope: Ensure `ai_integration.memory_module` and `plasticity` accept injected `numpy.random.Generator` seeded from `SimulationConfig.seed`.  
   - Risk: Medium (touches RNG usage).  
   - Metrics: Determinism delta test: same seed → identical recall results; coverage of seed plumbing.

3. **State Size Guardrail**  
   - Scope: Add optional `max_trace_steps`/`max_duration_ms` guard in `SimulationConfig` + invariant enforcing bounded trace/history.  
   - Risk: Low-Medium (new guard path).  
   - Metrics: Guard triggers on overflow; memory usage bounded in benchmark.

4. **Metrics Contract Check**  
   - Scope: Add lightweight validator that fails if `compute_report` misses required `REPORT_KEYS` or contains NaN; wire into tests.  
   - Risk: Low.  
   - Metrics: 100% `REPORT_KEYS` presence; zero NaN/Inf in reports across seed=42 smoke run.

5. **Config Lint (pre-commit)**  
   - Scope: Pre-commit hook to run `core.validate_config` over sample configs in `configs/` with `guards_enabled` true.  
   - Risk: Low.  
   - Metrics: Hook time < 10s; zero invalid configs merged.
