# BN-Syn Benchmarks

Research-grade benchmarking framework for BN-Syn scalability, physical validity, and reproducibility.

## Overview

This directory contains tools for deterministic benchmarking across scale and physics-relevant sweeps. Benchmarks measure:

- **Stability:** NaN rate, divergence rate
- **Physics:** spike rate, criticality σ
- **Learning:** weight entropy, convergence error
- **Thermostat:** temperature vs exploration
- **Reproducibility:** bitwise delta
- **Performance:** wall time, memory, throughput

---

## 🧬 Throughput Scaling Framework (NEW)

The BN-Syn throughput scaling framework implements **physics-preserving optimizations**
while maintaining exact emergent dynamics. This follows a rigorous 7-step validation process.

### Quick Start

Run the complete validation suite:

```bash
python -m scripts.orchestrate_throughput_scaling
```

This executes all 7 steps and generates comprehensive reports in `benchmarks/`.

### The 7-Step Framework

#### STEP 1: Ground-Truth Baseline
```bash
python -m scripts.benchmark_physics --backend reference --output benchmarks/physics_baseline.json
```
Establishes the reference physics manifold that all optimizations must preserve.

#### STEP 2: Kernel Profiling
```bash
python -m scripts.profile_kernels --output benchmarks/kernel_profile.json
```
Creates the "Performance Jacobian" - identifies computational bottlenecks.

#### STEP 3: Scaling Surface Analysis
See `benchmarks/scaling_plan.md` for analysis of optimization opportunities.

#### STEP 4: Accelerated Backend
```bash
python -m scripts.benchmark_physics --backend accelerated --output benchmarks/physics_accelerated.json
```
Runs the optimized backend (sparse synapse propagation, vectorization).

#### STEP 5: Physics Equivalence Verification
```bash
python -m scripts.verify_equivalence \
  --reference benchmarks/physics_baseline.json \
  --accelerated benchmarks/physics_accelerated.json \
  --output benchmarks/equivalence_report.md
```
Validates that accelerated backend preserves all physics within tolerance.

#### STEP 6: Throughput Gains
```bash
python -m scripts.calculate_throughput_gain \
  --reference benchmarks/physics_baseline.json \
  --accelerated benchmarks/physics_accelerated.json \
  --output benchmarks/throughput_gain.json
```
Records speedup, memory reduction, and energy savings.

#### STEP 7: CI Gate
The workflow `.github/workflows/physics-equivalence.yml` automatically validates
physics preservation on every PR.

### Key Files

- `physics_baseline.json` - Ground-truth reference backend metrics
- `physics_accelerated.json` - Optimized backend metrics
- `kernel_profile.json` - Performance Jacobian (kernel timings)
- `scaling_plan.md` - Optimization roadmap and analysis
- `equivalence_report.md` - Physics validation report
- `throughput_gain.json` - Performance improvements

### Backend Modes

**Reference Backend** (`--backend reference`)
- Dense matrix operations
- Exact baseline for validation
- NEVER modified

**Accelerated Backend** (`--backend accelerated`)
- Sparse CSR matrix format
- Vectorized operations
- Physics-preserving optimizations

### Success Criteria

All optimizations must meet:

- ✅ Spike statistics: < 1% deviation
- ✅ Sigma (σ): < 0.1% drift
- ✅ Attractor structure: correlation > 0.999
- ✅ Determinism: bit-exact for same seed
- ✅ Δt-invariance: maintained

### Physics Invariants (NEVER CHANGE)

- AdEx equations
- 3-factor plasticity laws
- Criticality control (σ)
- Temperature gating semantics
- SSOT, claims, bibliography
- Δt-invariance
- Determinism

---

## Quick Start (Legacy Benchmarks)

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run baseline benchmark (local development):
```bash
python benchmarks/run_benchmarks.py --scenario small_network --repeats 1 --json results/bench.json
```

## Scenario Sets

- **small_network**: Baseline small network
- **medium_network**: Baseline medium network
- **large_network**: Baseline large network
- **criticality_sweep**: σ target sweep
- **temperature_sweep**: Temperature schedule sweep
- **dt_sweep**: Integration timestep sweep
- **full**: All scenarios combined

## Design

### Isolation

Each benchmark run executes in a fresh subprocess to avoid cross-run contamination. This ensures:
- Clean memory state
- Independent RNG seeding
- No accumulation of numerical drift

### Determinism

All benchmarks use:
- Fixed seeds (default: 42)
- Pinned `numpy.random.Generator` via `bnsyn.rng.seed_all()`
- Exact parameter serialization

### Output Format

**JSON:**
- One entry per scenario
- Includes: git SHA, Python version, timestamp, parameters, and metrics

## Reproducibility

See [`docs/benchmarks/PROTOCOL.md`](../docs/benchmarks/PROTOCOL.md) for:
- Exact environment requirements
- Interpretation guidelines
- Known variability sources

## Files

- `run_benchmarks.py`: CLI harness
- `metrics.py`: Metrics collection utilities
- `scenarios/`: Scenario definitions

## CI Integration

Nightly benchmarks are run via `.github/workflows/benchmarks.yml` (standard tier, nightly profile) and upload artifacts.
