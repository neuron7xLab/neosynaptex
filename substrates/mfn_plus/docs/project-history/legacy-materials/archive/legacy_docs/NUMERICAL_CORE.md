# Numerical Core Implementation Guide

This document describes the numerically stable core engines added in Phase 2.

## Overview

The `core/` module provides three specialized engines that implement the mathematical
models described in [`MFN_MATH_MODEL.md`](./MFN_MATH_MODEL.md) with:

- **Numerical stability guarantees** (CFL conditions, clamping, NaN/Inf detection)
- **Reproducibility** (fixed random seeds)
- **Parameterized APIs** (dataclass configurations)
- **Metrics collection** for monitoring and debugging

## Module Structure

```
src/mycelium_fractal_net/core/
├── __init__.py              # Public exports
├── exceptions.py            # StabilityError, ValueOutOfRangeError, etc.
├── membrane_engine.py       # Nernst potential, ODE integration
├── reaction_diffusion_engine.py  # Turing morphogenesis PDEs
└── fractal_growth_engine.py # IFS fractals, box-counting
```

---

## 1. Membrane Engine

Implements Nernst equation and ODE integration for membrane potentials.

**Reference:** MFN_MATH_MODEL.md Section 1

### Configuration

```python
from mycelium_fractal_net.core import MembraneConfig, MembraneEngine

config = MembraneConfig(
    temperature_k=310.0,        # Body temperature (37°C)
    ion_clamp_min=1e-6,         # Minimum concentration (prevents log(0))
    potential_min_v=-0.150,     # -150 mV physical limit
    potential_max_v=0.150,      # +150 mV physical limit
    integration_scheme="euler", # or "rk4"
    dt=1e-4,                    # 0.1 ms time step
    check_stability=True,       # Check for NaN/Inf
    random_seed=42,             # For reproducibility
)

engine = MembraneEngine(config)
```

### Nernst Potential Calculation

```python
# Single ion potential (K+)
e_k = engine.compute_nernst_potential(
    z_valence=1,
    concentration_out_molar=5e-3,   # 5 mM extracellular
    concentration_in_molar=140e-3,  # 140 mM intracellular
)
print(f"E_K = {e_k * 1000:.2f} mV")  # Expected: ~-89 mV

# Vectorized computation
import numpy as np
c_out = np.array([5e-3, 145e-3, 2e-3])
c_in = np.array([140e-3, 12e-3, 0.1e-3])
potentials = engine.compute_nernst_potential_array(1, c_out, c_in)
```

### ODE Integration

```python
import numpy as np

# Define derivative function
def membrane_decay(v: np.ndarray) -> np.ndarray:
    return -0.1 * v  # Simple exponential decay

# Integrate
v0 = np.array([-0.070])  # -70 mV initial
v_final, metrics = engine.integrate_ode(v0, membrane_decay, steps=1000)

print(f"Steps: {metrics.steps_computed}")
print(f"Clamping events: {metrics.clamping_events}")
```

### Stability Features

- **Ion clamping:** Concentrations clamped to `ion_clamp_min` to prevent `log(0)`
- **Potential clamping:** Values clamped to `[potential_min_v, potential_max_v]`
- **NaN/Inf detection:** Raises `NumericalInstabilityError` if detected
- **Metrics tracking:** Records min/max/mean/std and clamping events

---

## 2. Reaction-Diffusion Engine

Implements Turing morphogenesis with activator-inhibitor dynamics.

**Reference:** MFN_MATH_MODEL.md Section 2

### Configuration

```python
from mycelium_fractal_net.core import (
    ReactionDiffusionConfig, 
    ReactionDiffusionEngine
)

config = ReactionDiffusionConfig(
    grid_size=64,           # 64x64 lattice
    d_activator=0.1,        # Activator diffusion (< 0.25 for stability)
    d_inhibitor=0.05,       # Inhibitor diffusion
    r_activator=0.01,       # Reaction rate
    r_inhibitor=0.02,       # Reaction rate
    turing_threshold=0.75,  # Pattern activation threshold
    alpha=0.18,             # Field diffusion (< 0.25 for CFL)
    boundary_condition="periodic",  # "periodic", "neumann", or "dirichlet"
    quantum_jitter=False,   # Stochastic noise
    jitter_var=0.0005,      # Noise variance
    spike_probability=0.25, # Growth event probability
    check_stability=True,
    random_seed=42,
)

engine = ReactionDiffusionEngine(config)
```

### Simulation

```python
# Run simulation
field, metrics = engine.simulate(steps=500, turing_enabled=True)

print(f"Field range: [{field.min()*1000:.1f}, {field.max()*1000:.1f}] mV")
print(f"Growth events: {metrics.growth_events}")
print(f"Turing activations: {metrics.turing_activations}")

# Get field history for Lyapunov analysis
history, metrics = engine.simulate(steps=100, return_history=True)
print(f"History shape: {history.shape}")  # (100, 64, 64)
```

### CFL Stability

The diffusion coefficients must satisfy:

```
dt * D * 4/dx² ≤ 1
```

With `dt = dx = 1`: **D ≤ 0.25**

The configuration validates this automatically:

```python
# This will raise StabilityError:
try:
    bad_config = ReactionDiffusionConfig(alpha=0.30)
except StabilityError as e:
    print(f"CFL violation: {e}")
```

### Boundary Conditions

| Condition | Description | Implementation |
|-----------|-------------|----------------|
| `periodic` | Wrap-around | `np.roll` |
| `neumann` | Zero-flux | Mirror at boundary |
| `dirichlet` | Fixed value | Zero at boundary |

---

## 3. Fractal Growth Engine

Implements IFS fractals and box-counting dimension estimation.

**Reference:** MFN_MATH_MODEL.md Section 3

### Configuration

```python
from mycelium_fractal_net.core import FractalConfig, FractalGrowthEngine

config = FractalConfig(
    num_points=10000,       # IFS points to generate
    num_transforms=4,       # Number of affine transforms
    scale_min=0.2,          # Minimum contraction (must be > 0)
    scale_max=0.5,          # Maximum contraction (must be < 1)
    translation_range=1.0,  # Translation range [-r, +r]
    min_box_size=2,         # Minimum box size for dimension
    max_box_size=None,      # Auto: grid_size/2
    num_scales=5,           # Number of scales for regression
    check_stability=True,
    random_seed=42,
)

engine = FractalGrowthEngine(config)
```

### IFS Fractal Generation

```python
# Generate IFS fractal
points, lyapunov = engine.generate_ifs()

print(f"Points shape: {points.shape}")      # (10000, 2)
print(f"Lyapunov exponent: {lyapunov:.3f}") # Expected: < 0 (stable)

# Access stored transforms
for i, (a, b, c, d, e, f) in enumerate(engine.transforms):
    det = abs(a * d - b * c)
    print(f"Transform {i}: det = {det:.4f}")  # All < 1 (contractive)
```

### Box-Counting Dimension

```python
import numpy as np

# Create binary pattern
rng = np.random.default_rng(42)
binary = rng.random((64, 64)) > 0.5

# Estimate dimension
dim = engine.estimate_dimension(binary)
print(f"Fractal dimension: {dim:.3f}")  # Expected: ~1.8-2.0 for random

# Check R² of regression
print(f"R² = {engine.metrics.dimension_r_squared:.4f}")
```

### Contraction Requirement

For stable IFS, all transforms must satisfy: **|ad - bc| < 1**

```python
# Validation
assert engine.validate_contraction()  # True if all transforms contractive

# Dimension validation
assert engine.validate_dimension_range(dim)  # [0, 2] for 2D
assert engine.validate_dimension_range(1.6, biological=True)  # [1.4, 1.9]
```

---

## Exception Classes

```python
from mycelium_fractal_net.core import (
    StabilityError,
    ValueOutOfRangeError,
    NumericalInstabilityError,
)

# StabilityError - CFL violations, divergence
try:
    config = ReactionDiffusionConfig(alpha=0.30)
except StabilityError as e:
    print(f"Stability: {e}")  # Includes step and value info

# ValueOutOfRangeError - Parameter validation
try:
    config = FractalConfig(scale_max=1.5)
except ValueOutOfRangeError as e:
    print(f"Range: {e}")  # Includes parameter name, value, bounds

# NumericalInstabilityError - NaN/Inf detection
try:
    engine.simulate(steps=10000)  # If unstable
except NumericalInstabilityError as e:
    print(f"NaN/Inf: {e}")  # Includes field name, count
```

---

## Metrics Collection

All engines collect metrics for monitoring:

### MembraneMetrics

```python
metrics = engine.metrics
print(f"V range: [{metrics.potential_min_v*1000:.1f}, {metrics.potential_max_v*1000:.1f}] mV")
print(f"Clamping events: {metrics.clamping_events}")
print(f"NaN detected: {metrics.nan_detected}")
```

### ReactionDiffusionMetrics

```python
metrics = engine.metrics
print(f"Steps: {metrics.steps_computed}")
print(f"Growth events: {metrics.growth_events}")
print(f"Turing activations: {metrics.turing_activations}")
print(f"Activator mean: {metrics.activator_mean:.4f}")
print(f"Steps to instability: {metrics.steps_to_instability}")
```

### FractalMetrics

```python
metrics = engine.metrics
print(f"Lyapunov: {metrics.lyapunov_exponent:.3f}")
print(f"Dimension: {metrics.fractal_dimension:.3f}")
print(f"R²: {metrics.dimension_r_squared:.4f}")
print(f"Contractive: {metrics.is_contractive}")
```

---

## Testing

Tests are in `tests/core/`:

```bash
# Run all core tests
pytest tests/core/ -v

# Stability smoke tests
pytest tests/core/ -k "smoke"

# Determinism tests
pytest tests/core/ -k "determinism"

# Performance tests
pytest tests/core/ -k "performance"
```

### Test Categories

1. **Stability Smoke Tests** - Run N steps, verify no NaN/Inf
2. **Determinism Tests** - Same seed → same result
3. **Performance Sanity** - Complete in reasonable time
4. **Range Validation** - Values within expected bounds
5. **Config Validation** - Invalid parameters raise errors

---

## Best Practices

1. **Always use fixed seeds** for reproducibility:
   ```python
   config = ReactionDiffusionConfig(random_seed=42)
   ```

2. **Check CFL condition** before simulation:
   ```python
   assert engine.validate_cfl_condition()
   ```

3. **Monitor metrics** for early warning of issues:
   ```python
   if metrics.clamping_events > 1000:
       print("Warning: excessive clamping")
   ```

4. **Catch exceptions** for graceful degradation:
   ```python
   try:
       field, _ = engine.simulate(steps=10000)
   except NumericalInstabilityError:
       field, _ = engine.simulate(steps=1000)  # Fallback
   ```

---

## References

- [MFN_MATH_MODEL.md](./MFN_MATH_MODEL.md) - Mathematical formulations
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [VALIDATION_NOTES.md](./VALIDATION_NOTES.md) - Expected metric ranges
