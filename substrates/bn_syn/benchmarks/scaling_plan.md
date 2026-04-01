# BN-Syn Scaling Plan: Performance Jacobian Analysis

## Executive Summary

This document identifies computational bottlenecks and proposes physics-preserving
transformations to scale biophysical throughput while maintaining exact emergent dynamics.

**Goal**: Increase `updates_per_sec` while preserving spike statistics, σ, attractor structure.

---

## Kernel Analysis (from kernel_profile.json)

### Top Time Consumers

1. **full_step** - O(synapses + neurons)
   - Integrated network step
   - Contains all sub-kernels
   - Primary optimization target

2. **adex_update** - O(neurons)
   - AdEx differential equations
   - Per-neuron voltage and adaptation updates
   - Vectorizable

3. **synapse_propagation** - O(synapses)
   - Sparse matrix-vector multiplication
   - Currently: dense operations on sparse data
   - **HIGH OPTIMIZATION POTENTIAL**

4. **conductance_decay** - O(neurons)
   - Exponential decay for AMPA, NMDA, GABA_A
   - Already vectorized

5. **criticality_estimation** - O(neurons)
   - Branching ratio tracking
   - Sequential summation

---

## Identified Scaling Surfaces

### 1. **O(N²) Operations → Sparse**

**Current**: Synapse propagation uses dense matrix storage and operations

**Issue**:
- Connectivity is ~5% (p_conn = 0.05)
- Storing 95% zeros
- Dense matmul wastes 95% of operations

**Proposal**:
- Use CSR (Compressed Sparse Row) format
- Event-driven spike propagation
- Only update postsynaptic targets of spiking neurons

**Expected Gain**: 10-20x for synapse propagation

**Physics Impact**: None (exact same values)

---

### 2. **Python Loops → Vectorization**

**Current**: Some operations iterate in Python

**Issue**:
- Python loop overhead
- Poor cache locality

**Proposal**:
- Full NumPy vectorization
- Eliminate explicit Python loops in hot paths

**Expected Gain**: 2-5x

**Physics Impact**: None (floating-point determinism preserved)

---

### 3. **Redundant Memory Copies → In-place Updates**

**Current**: Multiple intermediate arrays created per step

**Issue**:
- Memory allocation overhead
- Cache pollution

**Proposal**:
- Preallocate buffers
- In-place updates where safe

**Expected Gain**: 1.5-2x

**Physics Impact**: None (same numerical results)

---

### 4. **JIT Compilation → Numba/JAX**

**Current**: Pure NumPy/Python execution

**Issue**:
- Interpreter overhead
- No compile-time optimization

**Proposal**:
- Numba JIT for hot kernels (AdEx, conductance)
- JAX backend (optional, behind flag)

**Expected Gain**: 3-10x

**Physics Impact**: Minimal (validated against reference)

**Note**: Must be behind `--backend accelerated` flag

---

## Optimization Roadmap

### Phase 1: Sparse Synapse Propagation (HIGHEST IMPACT)

**Target**: `synapse_propagation` kernel

**Approach**:
1. Convert dense weight matrices to CSR format
2. Implement event-driven spike propagation
3. Only process postsynaptic targets of spiking neurons

**Validation**:
- Compare spike counts per timestep
- Verify conductance values match reference
- Check determinism (same seed → same results)

**Expected**: 10-20x speedup for synapse operations

---

### Phase 2: Vectorization Pass

**Target**: All kernels with Python loops

**Approach**:
1. Identify remaining Python loops
2. Replace with NumPy broadcasting
3. Preallocate intermediate buffers

**Validation**:
- Bit-exact match with reference backend
- Spike histograms identical

**Expected**: 2-3x overall speedup

---

### Phase 3: JIT Acceleration (Optional)

**Target**: AdEx, conductance, eligibility traces

**Approach**:
1. Wrap hot kernels with Numba @jit
2. Validate numerical equivalence
3. Add JAX backend option

**Validation**:
- Physics equivalence test suite
- Δt-invariance maintained
- Attractor structure preserved

**Expected**: 3-5x additional speedup

---

## Physics Invariants (NEVER CHANGE)

The following must remain bit-exact between backends:

1. **AdEx Equations** (docs/SPEC.md#P0-1)
   - Voltage dynamics
   - Adaptation dynamics
   - Spike threshold and reset

2. **3-Factor Plasticity** (docs/SPEC.md#P0-4)
   - STDP
   - Eligibility traces
   - Neuromodulation

3. **Criticality Control** (docs/SPEC.md#P1-7)
   - σ estimation (branching ratio)
   - Gain controller

4. **Determinism**
   - Same seed → same results
   - Δt-invariance (dt vs dt/2 equivalence)

---

## Proposed Backend Architecture

```
bnsyn/
  backends/
    __init__.py
    reference.py      # Current implementation (never changes)
    sparse.py         # Sparse synapse propagation
    vectorized.py     # Full vectorization
    jit.py            # Numba/JAX acceleration
```

**API**:
```python
net = Network(..., backend="reference")  # Default
net = Network(..., backend="accelerated")  # All optimizations
```

---

## Next Steps

1. ✅ Establish physics baseline
2. ✅ Profile kernels (this document)
3. ⬜ Implement sparse backend
4. ⬜ Validate physics equivalence
5. ⬜ Measure throughput gains
6. ⬜ Add CI gate

---

## Success Metrics

- `updates_per_sec` increased by **10-100x**
- Spike statistics: **< 0.1% deviation**
- Sigma (σ): **< 0.001 drift**
- Attractor structure: **correlation > 0.999**
- Determinism: **bit-exact for same seed**

---

**Status**: Analysis complete. Ready for implementation.

**Approved by**: Physics-preserving transformation framework

**Date**: 2026-01-26
