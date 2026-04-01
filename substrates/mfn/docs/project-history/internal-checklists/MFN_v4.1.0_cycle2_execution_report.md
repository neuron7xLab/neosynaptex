# MFN v4.1.0 — Evolutionary Cycle Execution Report

## Closed in this cycle

### 1. Strict Forecast contract
- `src/mycelium_fractal_net/types/forecast.py`
  - introduced strict Pydantic/TypeAdapter validation boundary for `ForecastResult`
  - removed silent `evaluation_metrics or benchmark_metrics` substitution
  - enforced non-empty `uncertainty_envelope`, `predicted_state_summary`, `evaluation_metrics`, `benchmark_metrics`
  - enforced required benchmark keys: `forecast_structural_error`, `adaptive_damping`
- `benchmarks/benchmark_quality.py`
  - now validates forecast payload before consuming structural metrics
  - no zero-backfill path for missing keys
- tests added:
  - `tests/test_forecast_contract_strict_cycle2.py`

### 2. Torch -> optional `[ml]` contour and CPU-only core import
- `pyproject.toml`
  - moved `torch` to `[project.optional-dependencies].ml`
  - added `[accel]` with `numba`
- optional dependency helper added:
  - `src/mycelium_fractal_net/_optional.py`
- CPU-safe lazy/optional import boundaries hardened in:
  - `src/mycelium_fractal_net/__init__.py`
  - `src/mycelium_fractal_net/core/__init__.py`
  - `src/mycelium_fractal_net/core/stability.py`
  - `src/mycelium_fractal_net/core/nernst.py`
  - `src/mycelium_fractal_net/signal/__init__.py`
  - `src/mycelium_fractal_net/integration/__init__.py`
  - `src/mycelium_fractal_net/metrics.py`
  - ML-only modules now require `require_ml_dependency("torch")`
- deterministic proof:
  - `import mycelium_fractal_net` now works when `torch` import is blocked
  - ML-only surfaces emit explicit optional-dependency error instead of crashing
- tests:
  - `tests/test_optional_dependencies.py`

### 3. JIT Laplacian + numeric parity
- `src/mycelium_fractal_net/numerics/grid_ops.py`
  - added optional numba-JIT Laplacian path for periodic / neumann / dirichlet
  - retained numpy reference implementation
  - feature flag / selection via `use_accel` and `MFN_ENABLE_ACCEL_LAPLACIAN`
- `src/mycelium_fractal_net/numerics/__init__.py`
  - converted update-rule exports to lazy loading to break circular import path
- tests:
  - `tests/test_accel_and_history_cycle2.py`
- benchmark:
  - `benchmarks/benchmark_scalability.py` now includes `laplacian_numpy_vs_jit`

### 4. AdaptiveAlphaGuard + soft boundary damping
- `src/mycelium_fractal_net/core/reaction_diffusion_engine.py`
  - added `alpha_guard_enabled`, `alpha_guard_threshold`, `soft_boundary_damping`, `accel_laplacian`
  - added runtime metrics: `alpha_guard_triggered`, `alpha_guard_triggers`, `substeps_used`, `effective_dt`, `soft_boundary_pressure`, `hard_clamp_events`
  - implemented substep splitting near CFL boundary
  - implemented soft damping before hard clamp safety rail
- `src/mycelium_fractal_net/core/engine.py`
  - propagated new metrics into metadata
- tests:
  - `tests/test_accel_and_history_cycle2.py`

### 5. Memmap history path
- `src/mycelium_fractal_net/core/simulate.py`
  - added `history_backend='memmap'`
  - added disk-backed history persistence + metadata (`history_memmap_path`, cleanup policy)
- `src/mycelium_fractal_net/types/field.py`
  - preserved memmap-backed arrays via `np.asanyarray`
- tests:
  - `tests/test_accel_and_history_cycle2.py`
- benchmark:
  - `benchmarks/benchmark_scalability.py` now includes memmap-backed scale benchmark contour

### 6. Bundle verification + Ed25519 signing
- added `src/mycelium_fractal_net/artifact_bundle.py`
  - SHA-256 hashing
  - deterministic Ed25519 signing based on `configs/crypto.yaml`
  - signature verification
  - bundle verification for report/release/showcase manifests
- `configs/crypto.yaml`
  - deterministic artifact seed integrated
- `src/mycelium_fractal_net/cli.py`
  - added `mfn verify-bundle`
- `src/mycelium_fractal_net/pipelines/reporting.py`
  - signs `report.md` and `manifest.json`
- `scripts/release_prep.py`
  - signs `release_manifest.json` and verifies bundle
- `scripts/showcase_run.py`
  - signs `showcase_manifest.json` and verifies bundle
- tests:
  - `tests/test_bundle_and_symbolic_cycle2.py`

### 7. SymbolicContext export
- added `src/mycelium_fractal_net/types/symbolic.py`
- `src/mycelium_fractal_net/types/report.py`
  - exports deterministic symbolic context from `AnalysisReport`
  - symbolic identity is now derived from runtime evidence, not transient timestamp run-id
- `src/mycelium_fractal_net/pipelines/reporting.py`
  - writes `symbolic_context.json`
- tests:
  - `tests/test_bundle_and_symbolic_cycle2.py`

### 8. Docs / CI / operational surfaces
- `README.md`
  - documented `core` vs `ml` vs `accel` install profiles
  - documented `mfn verify-bundle`
- `docs/LOCAL_RUNBOOK.md`
  - added install profiles and bundle verification commands
- `.github/workflows/ci-reusable.yml`
  - added `VERIFY_CORE` / `VERIFY_ML` separation
  - ML benchmark path now explicitly syncs with `--extra ml`
- `KNOWN_LIMITATIONS.md`
  - added scale-limit / experimental-scale policy language

## Verification actually executed

### Targeted tests
```bash
PYTHONPATH=src pytest -o addopts='' \
  tests/test_optional_dependencies.py \
  tests/test_forecast_contract_strict_cycle2.py \
  tests/test_accel_and_history_cycle2.py \
  tests/test_bundle_and_symbolic_cycle2.py \
  tests/test_showcase_bundle.py
```
Result: **22 passed**

### Script / CLI verification
```bash
PYTHONPATH=src python scripts/showcase_run.py
PYTHONPATH=src python benchmarks/benchmark_scalability.py
PYTHONPATH=src python -m mycelium_fractal_net.cli verify-bundle artifacts/showcase/showcase_manifest.json
PYTHONPATH=src python -m mycelium_fractal_net.cli verify-bundle artifacts/release/release_manifest.json
```
Result: **PASS**

## Remaining not fully closed
These were advanced but not fully driven to evidence-complete closure in this cycle:
- exhaustive 512x512 / 1024x1024 OOM profiling with published thresholds
- formal public config limit reduction / promotion policy backed by fresh benchmark evidence
- full release/report/showcase multi-artifact signature fan-out beyond manifest/report core path
- comprehensive nightly/perf-only abort-path evidence for extreme-scale runs

## Practical status
- strict forecast contract: **closed**
- `torch -> [ml]` migration: **closed**
- CPU-only core install: **closed**
- JIT Laplacian + parity: **closed**
- `AdaptiveAlphaGuard`: **closed**
- soft boundary damping: **closed**
- memmap history: **closed**
- `mfn verify-bundle`: **closed**
- report/showcase/release signature + verify core path: **closed**
- `SymbolicContext` export: **closed**
- scale/OOM evidence contour: **partially advanced, not final**
