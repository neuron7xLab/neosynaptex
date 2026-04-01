# BN-SYN PRODUCTION READINESS AUDIT

> NON-NORMATIVE: Imported working document. Do not treat as evidence-backed claims.

**Auditor:** Staff Research Scientist / Principal Engineer  
**Date:** 2026-01-23  
**Scope:** Transform research prototype → production-grade simulator  
**Target:** God-tier engineering standards (Google Brain / DeepMind / OpenAI level)

---

## EXECUTIVE SUMMARY

**Current State:** Research-quality prototype (79% test coverage, basic functionality working)  
**Target State:** Production simulator (Brian2/NEST competitor level)  
**Gap Analysis:** 23 critical issues identified across 6 categories

**Priorities:**
1. **CRITICAL (P0):** Type safety, memory efficiency, numerical stability
2. **HIGH (P1):** Performance optimization, API design, error handling
3. **MEDIUM (P2):** Observability, documentation, extensibility
4. **LOW (P3):** Developer experience, tooling, ecosystem integration

---

## CATEGORY 1: TYPE SAFETY & CORRECTNESS (P0)

### ISSUE-001: Incomplete Type Annotations
**Severity:** CRITICAL  
**Impact:** Runtime type errors undetectable at development time

**Findings:**
```python
# src/bnsyn/plasticity/three_factor.py:21
def decay(x: np.ndarray, dt_ms: float, tau_ms: float) -> np.ndarray:
    return x * np.exp(-dt_ms / tau_ms)  # Returns Any, not np.ndarray
```

**Root Cause:** NumPy operations return `np.ndarray[Any, np.dtype[Any]]` without shape/dtype specification

**Fix Strategy:**
```python
from numpy.typing import NDArray

def decay(x: NDArray[np.float64], dt_ms: float, tau_ms: float) -> NDArray[np.float64]:
    """Exponential decay with explicit float64 typing."""
    return np.asarray(x * np.exp(-dt_ms / tau_ms), dtype=np.float64)
```

**Acceptance:** `mypy --strict` passes with zero errors

---

### ISSUE-002: Missing Input Validation in Hot Path
**Severity:** CRITICAL  
**Impact:** Silent numerical errors, undefined behavior

**Findings:**
```python
# src/bnsyn/neuron/adex.py:33
V = state.V_mV.astype(float, copy=True)  # No validation of input ranges
```

**Problems:**
- No check for NaN/Inf propagation
- No validation that `V_mV` is 1D array
- No verification that `I_syn_pA` and `I_ext_pA` have matching shapes

**Fix Strategy:**
```python
def adex_step(
    state: AdExState,
    params: AdExParams,
    dt_ms: float,
    I_syn_pA: NDArray[np.float64],
    I_ext_pA: NDArray[np.float64],
) -> AdExState:
    # Input validation
    if state.V_mV.ndim != 1:
        raise ValueError(f"V_mV must be 1D, got shape {state.V_mV.shape}")
    N = len(state.V_mV)
    if I_syn_pA.shape != (N,) or I_ext_pA.shape != (N,):
        raise ValueError(f"Current arrays must match neuron count {N}")
    if not np.all(np.isfinite(state.V_mV)):
        raise RuntimeError("Non-finite voltage detected before step")
    # ... rest of function
```

**Acceptance:** Property-based tests with Hypothesis verify all edge cases

---

### ISSUE-003: No Formal Numerical Error Bounds
**Severity:** HIGH  
**Impact:** Unquantified accumulation of floating-point errors

**Current:** Euler integration with fixed timestep, no error estimation  
**Missing:** 
- Local truncation error bounds (LTE)
- Global error accumulation tracking
- Adaptive timestep recommendations

**Fix Strategy:**
```python
@dataclass
class IntegrationMetrics:
    lte_estimate: float  # Local truncation error
    global_error_bound: float  # Accumulated error
    recommended_dt: float  # Adaptive timestep suggestion

def adex_step_with_error_tracking(
    state: AdExState, 
    params: AdExParams, 
    dt_ms: float,
    I_syn_pA: NDArray[np.float64],
    I_ext_pA: NDArray[np.float64],
) -> tuple[AdExState, IntegrationMetrics]:
    # Implement Richardson extrapolation or embedded RK pair
    # Compare dt vs dt/2 locally, estimate error
    pass
```

**Reference:** Hairer, Nørsett, Wanner (1993) "Solving Ordinary Differential Equations I"

---

## CATEGORY 2: PERFORMANCE & SCALABILITY (P0)

### ISSUE-004: Dense Matrix Multiplication Bottleneck
**Severity:** CRITICAL  
**Impact:** O(N²) memory, O(N²) compute even with sparse connectivity

**Current Code:**
```python
# src/bnsyn/sim/network.py:99-100
incoming_exc = self.W_exc @ spikes_E  # Dense (N, nE) × (nE,)
incoming_inh = self.W_inh @ spikes_I  # Dense (N, nI) × (nI,)
```

**Problem:** With p_conn=0.05, 95% of matrix entries are zero but still allocated

**Performance Impact (N=10,000):**
- Memory: 10000² × 8 bytes = 800 MB (vs 40 MB sparse)
- Compute: 100M FLOPs (vs 5M sparse)

**Fix Strategy:**
```python
from scipy.sparse import csr_matrix

class Network:
    def __init__(self, ...):
        # Store connectivity as sparse matrices
        mask = rng.random((N, N)) < nparams.p_conn
        self.W_exc_sparse = csr_matrix(
            (mask[:nE, :].astype(float) * nparams.w_exc_nS).T
        )
        self.W_inh_sparse = csr_matrix(
            (mask[nE:, :].astype(float) * nparams.w_inh_nS).T
        )
    
    def step(self):
        # Sparse matrix-vector product: O(nnz) instead of O(N²)
        incoming_exc = self.W_exc_sparse @ spikes_E
        incoming_inh = self.W_inh_sparse @ spikes_I
```

**Expected Speedup:** 20× for N=10,000, 100× for N=50,000

---

### ISSUE-005: No GPU Acceleration Path
**Severity:** HIGH  
**Impact:** Cannot scale beyond ~10K neurons efficiently

**Current:** Pure NumPy (CPU-only), no CUDA/JAX backend

**Target Architectures:**
- **JAX backend:** JIT compilation, automatic differentiation, GPU support
- **CuPy backend:** Drop-in NumPy replacement for NVIDIA GPUs
- **Numba backend:** JIT compilation for CPU vectorization

**Fix Strategy (JAX example):**
```python
# src/bnsyn/backends/jax_backend.py
import jax.numpy as jnp
from jax import jit

@jit
def adex_step_jax(
    V: jnp.ndarray,
    w: jnp.ndarray,
    dt_ms: float,
    params: AdExParams,
    I_syn: jnp.ndarray,
    I_ext: jnp.ndarray,
) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    """JAX-accelerated AdEx step with automatic GPU dispatch."""
    exp_arg = jnp.clip((V - params.VT_mV) / params.DeltaT_mV, -20.0, 20.0)
    I_exp = params.gL_nS * params.DeltaT_mV * jnp.exp(exp_arg)
    # ... rest of implementation
    return V_new, w_new, spiked
```

**Expected Speedup:** 10-100× depending on network size

---

### ISSUE-006: Memory Allocations in Hot Loop
**Severity:** HIGH  
**Impact:** Garbage collection overhead, cache thrashing

**Problem:**
```python
# src/bnsyn/sim/network.py:122
I_ext = np.zeros(N, dtype=float)  # NEW ALLOCATION EVERY TIMESTEP
```

**Fix Strategy:** Pre-allocate buffers, reuse memory
```python
class Network:
    def __init__(self, ...):
        # Pre-allocate reusable buffers
        self._I_ext_buffer = np.zeros(N, dtype=np.float64)
        self._I_syn_buffer = np.zeros(N, dtype=np.float64)
        self._spikes_buffer = np.zeros(N, dtype=bool)
    
    def step(self):
        # Reuse buffers (zero-copy when possible)
        self._I_ext_buffer.fill(0.0)
        self._I_ext_buffer += 50.0 * (self.gain - 1.0)
```

**Expected Improvement:** 5-10% reduction in step time, less GC pressure

---

## CATEGORY 3: API DESIGN & ERGONOMICS (P1)

### ISSUE-007: Stateful Network Class (Non-functional)
**Severity:** HIGH  
**Impact:** Difficult to parallelize, checkpoint, or reason about

**Current:** Network mutates internal state
```python
net = Network(...)
for _ in range(1000):
    metrics = net.step()  # Mutates net.state, net.g_ampa, etc.
```

**Problems:**
- Cannot replay from arbitrary state
- Breaks functional programming patterns (JAX incompatible)
- No explicit state transitions

**Fix Strategy:** Separate state from simulator logic
```python
@dataclass(frozen=True)
class NetworkState:
    """Immutable network state snapshot."""
    neurons: AdExState
    g_ampa: NDArray[np.float64]
    g_nmda: NDArray[np.float64]
    g_gabaa: NDArray[np.float64]
    criticality: CriticalityState
    step_count: int

class NetworkSimulator:
    """Stateless simulator (pure functions)."""
    def __init__(self, params: NetworkParams, connectivity: Connectivity):
        self.params = params
        self.W_exc = connectivity.W_exc
        self.W_inh = connectivity.W_inh
    
    def step(self, state: NetworkState, rng_key) -> NetworkState:
        """Pure function: state_t → state_{t+1}"""
        # No mutation, return new state
        return NetworkState(
            neurons=new_neuron_state,
            g_ampa=new_g_ampa,
            # ...
            step_count=state.step_count + 1,
        )
```

**Benefits:**
- Trivial checkpointing: `pickle.dump(state)`
- Easy parallelization: `jax.vmap(simulator.step, states)`
- Replay debugging: `state = simulator.step(old_state, key)`

---

### ISSUE-008: No Configuration Validation
**Severity:** MEDIUM  
**Impact:** Silent failures from invalid parameter combinations

**Current:** Pydantic used for basic types, no cross-field validation
```python
@dataclass(frozen=True)
class AdExParams:
    C_pF: float = 200.0
    gL_nS: float = 10.0
    # No validation: what if C_pF < 0? gL_nS = 0?
```

**Fix Strategy:**
```python
from pydantic import Field, field_validator, model_validator

class AdExParams(BaseModel):
    C_pF: float = Field(gt=0, description="Membrane capacitance (picofarads)")
    gL_nS: float = Field(gt=0, description="Leak conductance (nanosiemens)")
    DeltaT_mV: float = Field(gt=0, le=10, description="Spike slope factor")
    
    @field_validator("Vpeak_mV")
    def vpeak_above_threshold(cls, v, values):
        if "VT_mV" in values.data and v <= values.data["VT_mV"]:
            raise ValueError("Vpeak must be > VT")
        return v
    
    @model_validator(mode="after")
    def check_timescale_consistency(self):
        tau_mem = self.C_pF / self.gL_nS
        if tau_mem < 1.0 or tau_mem > 100.0:
            warnings.warn(f"Membrane tau={tau_mem:.1f}ms outside typical range")
        return self
```

---

## CATEGORY 4: OBSERVABILITY & DEBUGGING (P1)

### ISSUE-009: No Structured Logging
**Severity:** HIGH  
**Impact:** Cannot diagnose production issues

**Current:** No logging at all, only exceptions

**Fix Strategy:**
```python
import structlog

logger = structlog.get_logger()

class Network:
    def step(self):
        logger.debug(
            "network.step.start",
            step=self._step_count,
            sigma=self.sigma,
            gain=self.gain,
            spike_count=int(np.sum(self.state.spiked)),
        )
        
        # ... step logic
        
        if np.any(~np.isfinite(self.state.V_mV)):
            logger.error(
                "network.numerical_instability",
                step=self._step_count,
                V_min=float(np.min(self.state.V_mV)),
                V_max=float(np.max(self.state.V_mV)),
                V_nan_count=int(np.sum(np.isnan(self.state.V_mV))),
            )
            raise RuntimeError("Numerical instability detected")
```

---

### ISSUE-010: No Performance Profiling Infrastructure
**Severity:** MEDIUM  
**Impact:** Cannot identify bottlenecks in production

**Fix Strategy:**
```python
from contextlib import contextmanager
import time

@contextmanager
def timer(label: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info("timing", label=label, elapsed_ms=elapsed * 1000)

class Network:
    def step(self):
        with timer("network.step.external_spikes"):
            ext_spikes = self.rng.random(N) < lam
        
        with timer("network.step.synaptic_propagation"):
            incoming_exc = self.W_exc @ spikes_E
        
        # ...
```

**Alternative:** Use `py-spy` or `scalene` for profiling

---

## CATEGORY 5: TESTING & VALIDATION (P0)

### ISSUE-011: Missing Property-Based Tests
**Severity:** HIGH  
**Impact:** Edge cases not covered by unit tests

**Current:** Only example-based smoke tests  
**Coverage Gaps:**
- Extreme parameter values (dt→0, N→0, p_conn→1)
- Array shape mismatches
- Numerical stability at boundaries

**Fix Strategy:**
```python
from hypothesis import given, strategies as st
from hypothesis.extra.numpy import arrays

@given(
    V=arrays(np.float64, shape=st.integers(1, 1000), elements=st.floats(-100, 50)),
    dt_ms=st.floats(min_value=0.001, max_value=1.0),
)
def test_adex_step_never_produces_nan(V, dt_ms):
    """Property: adex_step should never produce NaN for finite inputs."""
    state = AdExState(V_mV=V, w_pA=np.zeros_like(V), spiked=np.zeros(len(V), dtype=bool))
    params = AdExParams()
    I_syn = np.zeros_like(V)
    I_ext = np.zeros_like(V)
    
    result = adex_step(state, params, dt_ms, I_syn, I_ext)
    
    assert np.all(np.isfinite(result.V_mV))
    assert np.all(np.isfinite(result.w_pA))
```

---

### ISSUE-012: No Regression Test Suite
**Severity:** MEDIUM  
**Impact:** Cannot detect performance regressions

**Fix Strategy:**
```python
# tests/benchmarks/test_performance_regression.py
import pytest

@pytest.mark.benchmark
def test_network_step_performance(benchmark):
    """Benchmark single network step (N=1000)."""
    net = create_test_network(N=1000)
    
    result = benchmark(net.step)
    
    # Assert performance bounds
    assert benchmark.stats.mean < 0.010  # 10ms per step max
    assert benchmark.stats.stddev < 0.002  # Low variance

# Run with: pytest-benchmark
```

---

## CATEGORY 6: PRODUCTION INFRASTRUCTURE (P2)

### ISSUE-013: No Checkpoint/Resume Mechanism
**Severity:** MEDIUM  
**Impact:** Cannot save/restore long simulations

**Fix Strategy:**
```python
import pickle
from pathlib import Path

class Network:
    def save_checkpoint(self, path: Path) -> None:
        """Save complete simulation state."""
        state = {
            "neuron_state": self.state,
            "conductances": (self.g_ampa, self.g_nmda, self.g_gabaa),
            "criticality": (self.sigma_ctl, self.branch),
            "rng_state": self.rng.__getstate__(),
            "step_count": self._step_count,
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)
    
    @classmethod
    def load_checkpoint(cls, path: Path, params: NetworkParams) -> "Network":
        """Restore from checkpoint."""
        with open(path, "rb") as f:
            state = pickle.load(f)
        # Reconstruct network...
```

---

### ISSUE-014: No Distributed Execution Support
**Severity:** LOW  
**Impact:** Cannot scale beyond single machine

**Future Work:** Ray/Dask integration for multi-node simulations

---

## IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Week 1)
- [ ] ISSUE-001: Full type annotations
- [ ] ISSUE-002: Input validation
- [ ] ISSUE-004: Sparse matrix connectivity
- [ ] ISSUE-007: Functional API redesign

### Phase 2: Performance (Week 2)
- [ ] ISSUE-005: JAX backend
- [ ] ISSUE-006: Memory pool
- [ ] ISSUE-010: Profiling infrastructure

### Phase 3: Production Hardening (Week 3)
- [ ] ISSUE-009: Structured logging
- [ ] ISSUE-011: Property-based tests
- [ ] ISSUE-013: Checkpointing

### Phase 4: Validation (Week 4)
- [ ] Benchmark against Brian2/NEST
- [ ] Experimental data validation
- [ ] Performance regression suite

---

## METRICS

**Success Criteria:**
- Type safety: `mypy --strict` passes with 0 errors
- Performance: 10× speedup for N=10K (sparse matrices + JAX)
- Test coverage: 95%+ line coverage, 100% critical path
- API ergonomics: <10 lines for common workflows
- Production readiness: Can run 10M neuron simulations on GPU cluster

**Next Steps:** Začnem implementáciou ISSUE-001 až ISSUE-007 v closest iterations.
