# Metrics Contract

This document defines the contract for the primary metrics validated in MyceliumFractalNet. Each
metric lists its definition, formula, units, valid input domain, expected range, edge cases, and
interpretation rules.

## Signal quality metrics (`src/mycelium_fractal_net/metrics.py`)

| Metric | Definition | Formula (code reference) | Units | Input domain | Expected range / invariants | Edge cases | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Mean Squared Error (MSE)** | Average squared difference between reference and test signals. | `np.mean((a-b)**2)` (`mse`) | Raw error | Same shape, finite, non-empty; `float32/float64`; arrays or torch tensors | `mse >= 0`; `mse == 0` iff signals identical | Returns `0` for identical inputs; raises on NaN/Inf or shape mismatch | Lower is better |
| **Signal-to-Noise Ratio (SNR)** | Ratio of signal power to noise power in decibels. | `10*log10(signal_power/noise_power)` where `noise = noisy - clean` (`snr`) | dB | Same shape, finite | `snr == +inf` when noise power is zero; `-inf` when signal power is zero with noise present | Identical arrays ⇒ `+inf`; zero signal with noise ⇒ `-inf` | Higher is better |
| **Peak Signal-to-Noise Ratio (PSNR)** | Peak ratio between dynamic range and reconstruction error. | `10*log10(data_range^2 / mse)` (`psnr`) | dB | Same shape, finite; `data_range` inferred from min/max if not provided | `psnr == +inf` when `mse == 0`; decreases monotonically as MSE increases | Identical arrays ⇒ `+inf`; if inferred `data_range == 0`, uses epsilon to avoid div/0 | Higher is better |
| **Structural Similarity Index (SSIM)** | Per-luminance/contrast/structure similarity score. | `((2μxμy+C1)(2σxy+C2))/((μx²+μy²+C1)(σx+σy+C2))` (`ssim`) | Unitless | Same shape, finite; global (no window) | Clipped to `[-1, 1]`; `ssim==1` for identical inputs | If denominator is zero (constant inputs), returns `1.0`; clips outputs to bounds | Higher is better |

**NaN/Inf policy:** All metric helpers validate inputs and raise `ValueError` for non-finite or
empty inputs to fail fast.

## HTTP observability metrics (`src/mycelium_fractal_net/integration/metrics.py`)

These metrics are already implemented in the existing middleware; this contract documents their
expected behavior without modifying the runtime code.

| Metric | Definition | Labels | Units | Expected range / invariants | Edge cases | Interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| `mfn_http_requests_total` | Counter of HTTP requests processed. | `endpoint`, `method`, `status` | Count | Monotonic non-decreasing | Present only when `prometheus_client` installed | Higher = more traffic |
| `mfn_http_request_duration_seconds` | Histogram of request latency. | `endpoint`, `method` | Seconds | Samples fall into fixed buckets `(0.005 … 10.0)`; non-negative | Absent if Prometheus is disabled; bucket underflow/overflow captured automatically | Lower bucket densities are better |
| `mfn_http_requests_in_progress` | Gauge of in-flight requests. | `endpoint`, `method` | Count | `>= 0`; increment on dispatch, decrement on completion | Always decremented in `finally` to avoid leaks | Lower is better |

### Invariants & failure modes
- Metrics middleware normalizes unknown paths to `/other` to prevent label explosion.
- When Prometheus is unavailable, metrics objects are `None` and middleware becomes a no-op.
- Latency and in-progress gauges are updated in a `finally` block to avoid leaks on exceptions.

### Runtime validation
- `validate_quality_metrics` validates input domains and returns `(mse, snr, psnr, ssim)` for
  synthetic fixtures. Use in tests/CI only (not required in hot paths).
