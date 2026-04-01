# Physical Equivalence Report

## Executive Summary

✅ **PASSED**: Accelerated backend preserves physics within tolerance.

- **Tolerance**: 1.00%
- **Comparisons**: 14
- **Failures**: 0

---

## Configuration

### Reference Backend

- Backend: `reference`
- Neurons: 200
- Synapses: 1990
- Steps: 1000
- dt: 0.1 ms

### Accelerated Backend

- Backend: `accelerated`
- Neurons: 200
- Synapses: 1990
- Steps: 1000
- dt: 0.1 ms

---

## Performance Comparison

| Metric | Reference | Accelerated | Speedup |
| ------ | --------- | ----------- | ------- |
| Updates/sec | 1.91e+07 | 1.81e+07 | 0.95x |
| Wall time (sec) | 0.1041 | 0.1102 | 0.95x |

---

## Physics Equivalence Tests

| Metric | Reference | Accelerated | Rel. Diff (%) | Status |
| ------ | --------- | ----------- | ------------- | ------ |
| spike_mean | 0.000000 | 0.000000 | 0.0000 | ✅ |
| spike_std | 0.000000 | 0.000000 | 0.0000 | ✅ |
| spike_min | 0.000000 | 0.000000 | 0.0000 | ✅ |
| spike_max | 0.000000 | 0.000000 | 0.0000 | ✅ |
| spike_median | 0.000000 | 0.000000 | 0.0000 | ✅ |
| sigma_mean | 1.000000 | 1.000000 | 0.0000 | ✅ |
| sigma_std | 0.000000 | 0.000000 | 0.0000 | ✅ |
| sigma_final | 1.000000 | 1.000000 | 0.0000 | ✅ |
| gain_mean | 1.000000 | 1.000000 | 0.0000 | ✅ |
| gain_final | 1.000000 | 1.000000 | 0.0000 | ✅ |
| attractor_mean_activity | 0.000000 | 0.000000 | 0.0000 | ✅ |
| attractor_variance | 0.000000 | 0.000000 | 0.0000 | ✅ |
| attractor_autocorr_lag1 | 0.000000 | 0.000000 | 0.0000 | ✅ |
| total_spikes | 0.000000 | 0.000000 | 0.0000 | ✅ |
---

## Conclusion

✅ The accelerated backend is **physics-equivalent** to the reference backend.

All emergent dynamics metrics (spike statistics, σ, gain, attractors) are preserved
within the specified tolerance. The optimization is **APPROVED** for deployment.
