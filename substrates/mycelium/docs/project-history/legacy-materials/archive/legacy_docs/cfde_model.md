## CFDE (Canonical Fractal Denoiser Engine) Model Contract

### A) Purpose
- Location: `src/mycelium_fractal_net/signal/denoise_1d.py::OptimizedFractalDenoise1D`.
- Role: structure-preserving 1D denoising for MFN pipelines (returns, biosignals) using fractal domain matching and overlap-add smoothing.
- Non-goal: must **not** amplify noise or rescale signals when the gate rejects reconstruction (identity fallback remains valid).

### B) Input / Output Contract
- Accepted shapes: `[L]`, `[B, L]`, `[B, C, L]` via `_canonicalize_1d` in `signal/denoise_1d.py`.
- Dtype: inputs preserved; internal ops run in `torch.float64` and outputs are cast back to the original dtype in `OptimizedFractalDenoise1D.forward`.
- Device: CPU/GPU respected; tensors stay on the caller’s device (no implicit host/device moves).

### C) Cognitive Loop Mapping (code-tied)
- **Thalamic Filter** — variance-ranked domain selection: `_denoise_fractal` → `var_pool`/`topk` in `signal/denoise_1d.py`.
- **Basal Ganglia Gate** — acceptance rule `mse_best < baseline_mse * gate_ratio`: `apply_fractal` mask inside `_denoise_fractal` in `signal/denoise_1d.py`.
- **Dopamine Gating** — ridge + clamp of scale `s`: `ridge_lambda`, `s_max`, `s_threshold` handling in `_denoise_fractal` in `signal/denoise_1d.py`.
- **Recursion Loop** — acceptor iterations: enforced minimum via `acceptor_iterations` in `OptimizedFractalDenoise1D.__init__` and applied in `forward` (fractal mode) in `signal/denoise_1d.py`.

### D) Invariants (testable)
- **Do No Harm gate**: when `do_no_harm=True`, regions with `mse_best >= baseline_mse * gate_ratio` bypass reconstruction, preserving baseline (`_denoise_fractal` in `signal/denoise_1d.py`).
- **Stability**: recursive passes should not increase proxy energy; validated by `tests/test_signal_denoise_1d.py::test_recursive_energy_stability` and `tests/test_signal_denoise_1d.py::test_cfde_recursive_monotonic_energy`.
- **Bounded outputs (debug mode)**: when `debug_checks=True`, CFDE asserts finite outputs and caps absolute magnitude growth relative to the input baseline.

### E) Multiscale + Observability (MFN-grade)
- **Scale modes**: `cfde_mode="single"` (default) keeps the legacy single-scale loop; `cfde_mode="multiscale"` evaluates up to three range sizes (derived from `(r, 2r, 4r)` and auto-clamped) and aggregates them with a bounded rule (see Multiscale Mode below).
- **Stats hook**: calling `forward(..., return_stats=True)` returns `(output, stats)` where `stats` includes:
  - `inhibition_rate`: percent of segments gated off by the basal ganglia rule
  - `reconstruction_mse` / `baseline_mse`: averaged per-range errors
  - `effective_iterations`: passes executed (counts multiscale branches)
  - `selected_range_size` (multiscale only): winning or weighted scale for the run
- **MFN integration**: `Fractal1DPreprocessor` forwards stats and accepts `cfde_mode` overrides plus multiscale `scales` and `aggregate` overrides for pipeline-level control.

### F) Failure Modes / Limitations
- Gate-off: if `fractal_dim_threshold` inhibits all ranges, `forward` returns the input unchanged (`signal/denoise_1d.py`).
- Edge padding: reflect padding falls back to replicate on very short signals in `_denoise_fractal`, so boundary artifacts may persist.
- Sensitivity: extremely small `population_size`/`range_size` reduce effectiveness; no exception is raised (see `Fractal1DPreprocessor` presets in `signal/preprocessor.py`).

### Canonical Pipeline Hook
- Finance pipeline hook: `examples/finance_regime_detection.py::map_returns_to_field` (parameter `denoise` + `cfde_preset`) applies `Fractal1DPreprocessor` before mapping returns into the MFN field.

### Multiscale Mode (optional)
- **Configuration surface**: `OptimizedFractalDenoise1D(cfde_mode="multiscale", multiscale_range_sizes=<tuple>|None, multiscale_aggregate="best"|"weighted")`; `Fractal1DPreprocessor(scales=..., aggregate=...)` passes these through presets.
- **Scales**: defaults derive from the base `range_size` as `(r, 2r, 4r)` (deduped, capped to three). Any scale larger than the signal length is skipped; if all are skipped the call falls back to a single-scale pass.
- **Compute bounds**: population per scale shrinks with scale (`pop_scale = max(64, min(population_size, population_size * r_base // r_scale))`, clamped by `max_population_ci`). At most three branches are evaluated; iterations remain unchanged to keep CI/runtime safe.
- **Aggregation rule**:
  - `aggregate="best"` (default): **best-scale-wins** using proxy `baseline_mse` from each scale with deterministic tie-breaking.
  - `aggregate="weighted"`: softmax over proxy errors blends branch outputs (temperature uses the proxy stddev, clamped > 0).
  - Inhibition mask from fractal-dimension gating is applied after aggregation to retain MFN safety.
- **Failure modes**: extremely short sequences may skip larger scales; if proxies are identical, deterministic ordering picks the earliest scale. Weighted aggregation can blur sharp spikes; use `aggregate="best"` when preserving peaks matters most.
