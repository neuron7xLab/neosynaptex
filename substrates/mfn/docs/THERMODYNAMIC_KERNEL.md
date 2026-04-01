# Thermodynamic Kernel

**First in category:** no R-D framework combines free energy tracking, Lyapunov stability
gating, and adaptive timestep control in a single deterministic loop.

## Concept

Every R-D simulation produces a pattern — but is the pattern *physically meaningful*
or a numerical artifact? The ThermodynamicKernel answers this by tracking three quantities:

1. **Free energy** F[u] = E_grad + E_potential
2. **Leading Lyapunov exponent** λ₁ from reaction Jacobian
3. **Energy drift** |dF/dt| per step

A simulation passes the thermodynamic gate only if all three are well-behaved.

## Gate Logic

```
λ₁ < -0.05  →  STABLE      →  gate OPEN
-0.05 < λ₁ < 0.05  →  METASTABLE  →  gate OPEN only if allow_metastable=True
λ₁ > 0.05  →  UNSTABLE    →  gate CLOSED
drift > 2× threshold  →  gate CLOSED regardless
```

**Why metastable matters:** Turing pattern formation IS a controlled instability.
The activator-inhibitor system is locally unstable (λ₁ ≈ 0+ε) — that's what creates
the patterns. The gate distinguishes this *productive instability* from *numerical divergence*.

## Components

### FreeEnergyTracker

```python
F[u] = ½ ∫ |∇u|² dx  +  ∫ V(u) dx

V(u) = u²(1-u)² / 4    # double-well potential
```

- Gradient energy: spatial structure cost
- Potential energy: distance from equilibrium wells at u=0, u=1
- Curvature landscape: Laplacian statistics for pattern boundary detection

### LyapunovAnalyzer

- Exact Jacobian for N ≤ 64 (finite differences)
- Randomized SVD for N > 64 (O(k·N) instead of O(N²))
- Samples every `lyapunov_sample_every` steps (default: 10)

### AdaptiveTimestepController

```
if |dF/dt| > threshold:     dt *= 0.75  (reduce)
if |dF/dt| < 0.1×threshold: dt *= 1.1   (expand)
dt ∈ [dt_min, dt_max]       always
```

Raises `ValueError("ThermodynamicDivergence")` after 10 consecutive reductions
with drift still > 10× threshold.

## Usage

```python
from mycelium_fractal_net import ThermodynamicKernel, ThermodynamicKernelConfig

kernel = ThermodynamicKernel(ThermodynamicKernelConfig(
    allow_metastable=True,      # allow Turing zone
    drift_threshold=1e-4,       # max energy change per step
    lyapunov_sample_every=10,   # Jacobian every N steps
))

# frames = list of (u, v) numpy arrays from your simulation
report = kernel.analyze_trajectory(frames, reaction_fn)

print(report.summary())
# [THERMO] gate=OPEN verdict=metastable λ₁=-0.012 drift=4.2e-05 steps=60 adaptive=0

if not report.gate_passed:
    raise RuntimeError(report.gate_message)
```

## References

- Cross & Hohenberg (1993) "Pattern formation outside equilibrium" Rev. Mod. Phys. 65:851
- Strogatz (1994) "Nonlinear Dynamics and Chaos" Ch. 6
- Murray (2003) "Mathematical Biology II" Ch. 2 (Turing instability)
