# API Reference — neosynaptex

> **Version:** 3.0.0
> **Source:** [`neosynaptex.py`](../neosynaptex.py)
> **License:** AGPL-3.0-or-later

This document covers all public interfaces exported from `neosynaptex.py`.
The public surface is defined by `__all__`.

---

## Quick Import

```python
from neosynaptex import (
    Neosynaptex,
    NeosynaptexState,
    DomainAdapter,
    MockBnSynAdapter,
    MockMfnAdapter,
    MockPsycheCoreAdapter,
    MockMarketAdapter,
    METASTABLE, COLLAPSING, CONVERGING, DIVERGING, DEGENERATE, DRIFTING, INITIALIZING,
)
```

---

## Class: `Neosynaptex`

Integrating mirror layer for the NFI subsystem. Observes registered domain
adapters and computes ten diagnostic layers per tick.

### Constructor

```python
Neosynaptex(window: int = 16)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `window` | `int` | `16` | Sliding window size for circular buffers. Must be >= 8. Larger window = more stable gamma but slower response to changes. |

**Raises:** `ValueError` if `window < 8`.

**Example:**

```python
nx = Neosynaptex(window=32)
```

---

### Method: `register`

```python
register(adapter: DomainAdapter) -> None
```

Register a domain adapter. Each adapter represents one subsystem to observe.

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `adapter` | `DomainAdapter` | Object implementing the domain adapter protocol |

**Raises:**
- `ValueError` if `len(adapter.state_keys) > 4` (MAX_STATE_KEYS invariant)
- `ValueError` if a domain with the same name is already registered

**Notes:**
- Maximum 4 domains can be registered (Invariant MAX_DOMAINS).
- Domain names must be unique (taken from `adapter.domain`).
- Register all adapters before calling `observe()`.

**Example:**

```python
nx = Neosynaptex()
nx.register(MockBnSynAdapter())
nx.register(MockMfnAdapter())
```

---

### Method: `observe`

```python
observe() -> NeosynaptexState
```

Collect state from all registered adapters and compute all ten diagnostic
layers. Returns an immutable snapshot.

**Returns:** `NeosynaptexState` — immutable dataclass with all diagnostic fields.

**Raises:** `RuntimeError` if no adapters are registered.

**Behavior:**
- Increments internal tick counter.
- Pushes (state, topo, cost) to each domain's circular buffer.
- Computes per-domain Jacobian, gamma, and bootstrap CI.
- Computes cross-domain coherence, Granger causality, anomaly isolation,
  phase portrait, resilience, modulation, and universal scaling test.
- Appends state to internal history (used by `export_proof`).

**Warm-up:** At least `window` ticks needed before all diagnostics produce
finite values. During warm-up, some fields return `NaN`.

**Example:**

```python
for _ in range(32):
    state = nx.observe()

print(state.phase)          # METASTABLE
print(state.gamma_mean)     # ~1.0
```

---

### Method: `export_proof`

```python
export_proof(path: str | None = None) -> dict
```

Export the proof bundle from the most recent observation as a
JSON-serializable dict. Optionally write to a file.

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `path` | `str \| None` | `None` | If provided, write JSON to this file path |

**Returns:** `dict` with the following top-level keys:

| Key | Type | Description |
|-----|------|-------------|
| `version` | `str` | Engine version (e.g., `"3.0.0"`) |
| `ticks` | `int` | Number of ticks observed |
| `gamma` | `dict` | Per-domain and mean gamma values with CIs |
| `jacobian` | `dict` | Per-domain spectral radius and condition number |
| `phase` | `str` | Current phase label |
| `anomaly` | `dict` | Per-domain anomaly scores |
| `granger` | `dict` | Granger causality graph `{src: {tgt: score}}` |
| `portrait` | `dict` | Phase portrait metrics |
| `resilience` | `float \| None` | Resilience score |
| `modulation` | `dict` | Per-domain modulation signals |
| `coherence` | `float \| None` | Cross-domain coherence |
| `verdict` | `str` | `"COHERENT"` / `"PARTIAL"` / `"INCOHERENT"` |
| `coupling_tensor` | `dict` | Cross-domain Jacobian and condition number |
| `chain` | `dict` | Hash-linked proof chain entry |

**Chain integrity:** Each bundle includes `chain.self_hash` (SHA-256 of the
bundle excluding the self_hash field) and `chain.prev_hash` linking to the
previous bundle. This forms a tamper-evident proof chain.

**Raises:** Returns `{"error": "no observations"}` if `observe()` has not
been called.

**Example:**

```python
proof = nx.export_proof(path="xform_proof_bundle.json")
print(proof["verdict"])       # COHERENT
print(proof["chain"]["self_hash"])
```

---

### Method: `save_state` / `load_state`

> **Note:** State persistence is handled via `export_proof()` for the proof
> bundle. For full internal state serialization, use the `evl/` ledger
> tooling (`evl/` directory) which captures adapter state and replay context.

---

## Dataclass: `NeosynaptexState`

Immutable snapshot returned by `Neosynaptex.observe()`. All fields are
frozen (cannot be modified after creation).

```python
@dataclass(frozen=True)
class NeosynaptexState:
    ...
```

### Fields

#### Timing

| Field | Type | Description |
|-------|------|-------------|
| `t` | `int` | Tick counter (number of `observe()` calls so far) |

#### State vectors

| Field | Type | Description |
|-------|------|-------------|
| `phi` | `np.ndarray` | Concatenated state vector across all domains |
| `phi_per_domain` | `dict[str, np.ndarray]` | Per-domain state vectors |

#### Gamma

| Field | Type | Description |
|-------|------|-------------|
| `gamma_per_domain` | `dict[str, float]` | Theil-Sen gamma per domain. `NaN` during warm-up. |
| `gamma_ci_per_domain` | `dict[str, tuple[float, float]]` | Bootstrap 95% CI `(low, high)` per domain |
| `gamma_mean` | `float` | Mean gamma across all domains with finite values |
| `gamma_std` | `float` | Std of gamma across domains |
| `cross_coherence` | `float` | `1 - std/mean` of gammas, clamped to `[0, 1]`. Measures cross-domain agreement. |

#### Gamma dynamics

| Field | Type | Description |
|-------|------|-------------|
| `dgamma_dt` | `float` | Rate of change of `gamma_mean` over the recent window (Theil-Sen slope) |
| `gamma_ema_per_domain` | `dict[str, float]` | Exponential moving average of gamma per domain (alpha=0.3) |

#### Universal scaling

| Field | Type | Description |
|-------|------|-------------|
| `universal_scaling_p` | `float` | Permutation p-value for the hypothesis that all domains share the same gamma. Low p = substrates diverging. |

#### Jacobian

| Field | Type | Description |
|-------|------|-------------|
| `sr_per_domain` | `dict[str, float]` | Spectral radius of per-domain Jacobian |
| `cond_per_domain` | `dict[str, float]` | Condition number of the design matrix |
| `spectral_radius` | `float` | Median spectral radius across domains |

#### Phase

| Field | Type | Description |
|-------|------|-------------|
| `phase` | `str` | Current phase label. One of: `INITIALIZING`, `METASTABLE`, `COLLAPSING`, `DIVERGING`, `DEGENERATE`, `CONVERGING`, `DRIFTING` |

#### Diagnostics

| Field | Type | Description |
|-------|------|-------------|
| `anomaly_score` | `dict[str, float]` | Leave-one-out anomaly score per domain. High = domain is outlier. |
| `granger_graph` | `dict[str, dict[str, float]]` | Pairwise Granger causality `{src: {tgt: influence}}`. Values in `[0, 1]`. |
| `portrait` | `dict[str, float]` | Phase portrait metrics: `area`, `recurrence`, `distance_to_ideal` |
| `resilience_score` | `float` | Fraction of METASTABLE departures that recovered. `NaN` if no departures. |
| `modulation` | `dict[str, float]` | Per-domain modulation signal. Bounded `[-0.05, +0.05]`. |
| `diagnostic` | `dict` | Full diagnostic dict including `r2_per_domain` and other internal metrics |

#### Cross-domain Jacobian (computed after 64 ticks)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cross_jacobian` | `dict[str, dict[str, float]] \| None` | `None` | Cross-domain Jacobian `J[i][j] = d(gamma_i)/d(state_mean_j)` |
| `cross_jacobian_cond` | `float` | `NaN` | Condition number of cross-domain Jacobian |
| `adaptive_window` | `int` | `16` | Current adaptive window size |
| `ci_width_mean` | `float` | `NaN` | Mean width of gamma CI across domains |

#### Value function

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `value_estimate` | `ValueEstimate \| None` | `None` | Internal value function estimate (X8 v2) |

#### Gradient diagnosis

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `gradient_diagnosis` | `str` | `"unknown"` | Gradient ontology classification: `living_gradient` / `static_capacitor` / `dead_equilibrium` / `transient` |

---

## Protocol: `DomainAdapter`

Structural protocol (PEP 544) that every substrate adapter must implement.
No explicit inheritance is required — duck typing suffices.

```python
class DomainAdapter(Protocol):
    @property
    def domain(self) -> str: ...

    @property
    def state_keys(self) -> list[str]: ...

    def state(self) -> dict[str, float]: ...

    def topo(self) -> float: ...

    def thermo_cost(self) -> float: ...
```

### Protocol members

| Member | Kind | Type | Description |
|--------|------|------|-------------|
| `domain` | property | `str` | Unique domain identifier (ASCII only — Invariant VI). Used as dict key in all per-domain outputs. |
| `state_keys` | property | `list[str]` | Ordered list of state variable names. Length must be 1–4 (MAX_STATE_KEYS). |
| `state()` | method | `dict[str, float]` | Returns current state as `{key: value}`. Keys must match `state_keys`. |
| `topo()` | method | `float` | Topological complexity C. Must be > 0 (values < 0.01 are clamped). |
| `thermo_cost()` | method | `float` | Thermodynamic cost K. Must be > 0 (values < 0.01 are clamped). |

**Invariants:**
- `domain` must be unique across all registered adapters.
- `state()` must return keys that are a superset of `state_keys`.
- `topo()` and `thermo_cost()` must return finite, positive values during
  normal operation. `NaN` or <= 0 values are replaced with the floor value
  `_TOPO_FLOOR = 0.01`.

### Implementing a custom adapter

```python
class MySubstrateAdapter:
    @property
    def domain(self) -> str:
        return "my_substrate"   # ASCII only

    @property
    def state_keys(self) -> list[str]:
        return ["activity", "entropy"]   # 1..4 keys

    def state(self) -> dict[str, float]:
        return {
            "activity": self._compute_activity(),
            "entropy": self._compute_entropy(),
        }

    def topo(self) -> float:
        return self._compute_topological_complexity()

    def thermo_cost(self) -> float:
        return self._compute_thermodynamic_cost()
```

---

## Mock Adapters

Four mock adapters are provided for testing and demonstration. They produce
synthetic time series that converge toward the metastable gamma ≈ 1.0 regime.

### `MockBnSynAdapter`

Simulates a BN-Syn spiking network oscillating near criticality (gamma ≈ 0.95).

```python
from neosynaptex import MockBnSynAdapter
adapter = MockBnSynAdapter()
print(adapter.domain)       # "bn_syn"
print(adapter.state_keys)   # ["rate", "cv", "sync", "branching"]
```

State keys: `rate`, `cv`, `sync`, `branching`

### `MockMfnAdapter`

Simulates an MFN+ memory-formation network.

```python
from neosynaptex import MockMfnAdapter
adapter = MockMfnAdapter()
print(adapter.domain)   # "mfn"
```

State keys: `hebbian`, `consolidation`, `decay`, `retrieval`

### `MockPsycheCoreAdapter`

Simulates a PsycheCore cognitive substrate.

```python
from neosynaptex import MockPsycheCoreAdapter
adapter = MockPsycheCoreAdapter()
print(adapter.domain)   # "psyche_core"
```

State keys: `attention`, `working_mem`, `integration`, `valence`

### `MockMarketAdapter`

Simulates market Kuramoto dynamics.

```python
from neosynaptex import MockMarketAdapter
adapter = MockMarketAdapter()
print(adapter.domain)   # "market"
```

State keys: `coherence`, `volatility`, `momentum`, `liquidity`

---

## Phase Constants

```python
INITIALIZING = "INITIALIZING"   # before window filled
METASTABLE   = "METASTABLE"     # gamma in [0.85, 1.15], rho in [0.80, 1.25]
CONVERGING   = "CONVERGING"     # rho < 0.80 (damped)
DIVERGING    = "DIVERGING"      # gamma > 1.15
COLLAPSING   = "COLLAPSING"     # gamma < 0.85
DRIFTING     = "DRIFTING"       # mild amplification
DEGENERATE   = "DEGENERATE"     # rho >= 1.5 for 3+ ticks (circuit breaker)
```

---

## Full Example

```python
from neosynaptex import (
    Neosynaptex,
    MockBnSynAdapter,
    MockMfnAdapter,
    MockPsycheCoreAdapter,
    METASTABLE,
)

# Build engine with 4 domains
nx = Neosynaptex(window=32)
nx.register(MockBnSynAdapter())
nx.register(MockMfnAdapter())
nx.register(MockPsycheCoreAdapter())

# Warm up
for _ in range(64):
    state = nx.observe()

# Inspect results
print(f"Phase        : {state.phase}")
print(f"Gamma mean   : {state.gamma_mean:.4f}")
print(f"Coherence    : {state.cross_coherence:.4f}")
print(f"Univ. scaling: p = {state.universal_scaling_p:.4f}")

for domain, gamma in state.gamma_per_domain.items():
    ci = state.gamma_ci_per_domain[domain]
    print(f"  {domain:20s}: gamma={gamma:.3f}  CI=[{ci[0]:.3f}, {ci[1]:.3f}]")

# Export proof
proof = nx.export_proof("my_proof_bundle.json")
print(f"Verdict: {proof['verdict']}")
print(f"Hash   : {proof['chain']['self_hash'][:16]}...")
```
