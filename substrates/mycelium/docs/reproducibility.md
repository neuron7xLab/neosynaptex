# Reproducibility

## Canonical Reproduction

```bash
uv run python experiments/reproduce.py
```

Runs a fixed simulation (N=32, T=60, seed=42) through all subsystems and compares actual output against `experiments/expected_output.json`.

### Expected Numbers (seed=42)

| Metric | Value | Subsystem |
|--------|-------|-----------|
| field_hash | `b407b808c7c8a03f` | Simulation (SHA256, deterministic) |
| anomaly_score | 0.2157 | Core diagnosis |
| ews_score | 0.4623 | Early warning |
| causal_decision | pass | Causal validation (46 rules) |
| basin_stability | 0.9333 | Levin morphospace |
| delta_alpha | 3.5932 | Fractal arsenal |
| hurst_exponent | 2.1046 | Fractal dynamics (DFA) |
| chi_invariant | 0.5986 | Basin invariant (S_bb x S_B) |
| W2_speed | 1.3306 | Wasserstein geometry |
| RMT r_ratio | 0.0251 | Random Matrix Theory |

### Tolerance

Float comparisons use tolerance of 0.01. Field hash must be exact.

### If Reproduction Fails

1. Check Python version (3.10-3.13 supported)
2. Check numpy/scipy versions match `uv.lock`
3. If hash differs, the simulation engine changed — investigate before merging

## What Is Not Deterministic

- Benchmark timings (vary by hardware)
- DiagnosticMemory learned rules (depend on observation order)
- Adversarial labels for specific seeds (stochastic by design)

These are validated by adversarial run, not canonical reproduction.
