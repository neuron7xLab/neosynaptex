# BN-Syn Benchmarks

## Scope

This repository defines deterministic, CI-enforced benchmarks that validate core scientific
properties of BN-Syn: determinism, Δt invariance, criticality, and scalability.

## Benchmarks and Metrics

### Determinism (`benchmarks/determinism.py`)

* **Identical seeds → identical traces**
  * Metric: `determinism_max_abs_error`
  * Threshold: `< 1e-12`
* **Different seeds → statistically different traces**
  * Metric: seed correlation for sigma and firing rate
  * Threshold: correlation `< 0.95`

Command:

```
python benchmarks/determinism.py
```

### Δt-Invariance (`benchmarks/scaling.py`)

Compares `dt = 0.1` vs `dt = 0.05` across the same wall-clock duration and reports:

* Firing rate drift (`dt_rate_drift`) ≤ 0.15
* Sigma drift (`dt_sigma_drift`) ≤ 0.05
* Weight distribution drift (`dt_weight_*_drift`) ≤ 1e-12

Command:

```
python benchmarks/scaling.py
```

### Criticality (`benchmarks/criticality.py`)

Measures avalanche statistics, sigma, and power-law fit of avalanche sizes.

* Sigma drift from target ≤ 0.2
* Power-law slope < 0 (negative)

Command:

```
python benchmarks/criticality.py
```

### Scalability (`benchmarks/scalability.py`)

Runs the network at `N ∈ {50, 100, 500, 1000}` and measures runtime, memory, and per-step cost.

Command:

```
python benchmarks/scalability.py
```

## CI Enforcement

The `benchmarks.yml` workflow runs determinism, Δt-invariance, and criticality benchmarks on every PR
using the standard tier and `ci` profile. See `.github/workflows/benchmarks.yml` for details.
