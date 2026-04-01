# Known Limitations

## Scale Limits

| Grid Size | Status | Notes |
|-----------|--------|-------|
| Up to 512x512 | Recommended | Production-ready, benchmarked |
| 512x512 long-history | Stress contour | Requires memmap history backend |
| 1024x1024 | Experimental | OOM profiling incomplete; explicit opt-in only |

The default release contour is CPU-first and deterministic. ML/GPU surfaces are optional extras.

For temporal history beyond 64 steps on grids larger than 128x128, use disk-backed history:
```python
mfn.simulate(spec, history_backend="memmap")
```

## Frozen Surfaces

The following surfaces are frozen and excluded from the v1 release contract:

| Surface | Location | Status |
|---------|----------|--------|
| Cryptography helpers | `src/mycelium_fractal_net/crypto/` | Deprecated; signing via `artifact_bundle.py`. Removal in v5.0. |
| Federated logic | `src/mycelium_fractal_net/core/federated.py` | Frozen; no active development |
| WebSocket adapters | `src/mycelium_fractal_net/integration/ws_*` | Frozen; not in v1 scope |
| Infrastructure | `infra/` | Deployment material; not library code |
| Historical docs | `docs/project-history/` | Archive; not maintained |

## Type Checking

- `mypy --strict` is enforced for `types/`, `security/`, `core/`, `analytics/`, and `neurochem/` modules.
- Frozen modules (`turing.py`, `federated.py`, `stdp.py`) are excluded from strict checking due to torch dependencies.
- CI blocks merge on any strict typing regression in core/analytics/neurochem.

## Causal Validation

- 46 rules cover the six pipeline stages plus cross-stage and perturbation checks.
- Exhaustive 512x512 / 1024x1024 OOM profiling with published thresholds is not yet closed.
- Formal public config limit reduction / promotion policy is not yet established.

## Neuromodulation

- Occupancy conservation is enforced numerically (error < 1e-6) but not algebraically proven.
- Observation noise model (`observation_noise_gaussian_temporal`) applies Gaussian temporal smoothing, not a hemodynamic response function. A true BOLD model requires HRF convolution (Buxton et al. 1998). Planned for v5.0 under profile `observation_noise_hrf_bold`.
- Profile parameter ranges are based on published literature but not independently calibrated.

## Fractal Dimension

- Box-counting fractal dimension (`D_box`) is estimated via log-log regression.
- For grids smaller than 8x8 or when `D_r2 < 0.8`, the estimate is marked as `low_confidence`.
- Low-confidence fractal estimates should not be treated as strong signals in detection scoring.

## Sensitivity Analysis

Threshold sensitivity sweep (±5%, ±10%, ±20%) identifies fragile decision thresholds:

| Threshold | Fragility | Notes |
|-----------|-----------|-------|
| DYNAMIC_ANOMALY_BASELINE | Moderate | Label flips near boundary |
| PATHOLOGICAL_NOISE_THRESHOLD | High | Regime-sensitive |
| REORGANIZED_COMPLEXITY_THRESHOLD | Moderate | Interaction with plasticity |

See `scripts/sensitivity_sweep.py` for the full report.

## Bio Layer

- Benchmark gates are hardware-dependent — recalibrate with `uv run python benchmarks/calibrate_bio.py` after changing machines.
- `ComputeBudget` glycogen reserve stores eigendecompositions keyed by `(sum(D_h), sum(D_v), shape)` — hash collisions possible for very different networks with same sum. TTL=300s mitigates stale cache.
- Memory anonymization `cosine_anonymity` at default pipeline parameters may be low (~0.05) for small grids. Increase `alpha_diffusion` for stronger effect.

## Mathematical Frontier

- TDA uses superlevel filtration (field inversion). For fields with positive activator, use `compute_tda(-field)` explicitly.
- Causal emergence CE depends on discretization quality. With few unique states in trajectory, CE may underestimate true causal structure.
- Fisher Information Matrix (`compute_fim`) requires 2×n_params PDE solves — expensive. Use `run_math_frontier(seq, run_fim=False)` for speed.
- RMT r-ratio interpretation assumes Physarum Laplacian is the primary structure. Custom Laplacians may need different GOE/Poisson thresholds.

## Dependencies

- `torch` is optional (`[ml]` extra). All core operations work without it.
- `numba` is optional (`[accel]` extra). JIT acceleration for Laplacian computation only.
- `fastapi`, `pandas`, `pyarrow`, `prometheus_client`, `websockets`, `httpx` are optional extras (`[api]`, `[data]`, `[metrics]`, `[ws]`). Core path requires only numpy, sympy, pydantic, cryptography.
- Root compatibility imports (e.g., `import analytics`) are deprecated and will be removed in v5.0.
