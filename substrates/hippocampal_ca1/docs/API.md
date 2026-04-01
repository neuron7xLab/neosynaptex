# API Reference

Complete API documentation for CA1 Hippocampus Framework v2.0

## Core Modules

### `data.biophysical_parameters`

#### `get_default_parameters() -> CA1Parameters`

Returns default parameter set with all values from literature.

**Returns:**
- `CA1Parameters`: Complete parameter container

**Example:**
```python
params = get_default_parameters()
print(params.plasticity.theta_p)  # 2.0 μM (Graupner 2012)
```

---

### `plasticity.unified_weights`

#### `class UnifiedWeightMatrix`

Unified synaptic weight matrix with integrated STP and Ca²⁺ plasticity.

**Constructor:**
```python
UnifiedWeightMatrix(
    connectivity: np.ndarray,      # [N, N] bool adjacency
    initial_weights: np.ndarray,   # [N, N] initial weights
    source_types: np.ndarray,      # [N, N] InputSource enum
    params: CA1Parameters
)
```

**Methods:**

##### `get_effective_weights() -> np.ndarray`

Returns effective weights W_eff = W_base × u × R

**Returns:**
- `np.ndarray [N, N]`: Effective connectivity matrix

##### `update_stp(spikes_pre: np.ndarray, spikes_post: np.ndarray)`

Update short-term plasticity (Tsodyks-Markram PNAS 1997).

**Args:**
- `spikes_pre`: [N] bool array (presynaptic spikes)
- `spikes_post`: [N] bool array (postsynaptic spikes)

##### `update_calcium(spikes_pre, spikes_post, V_dendrite: np.ndarray)`

Update Ca²⁺ concentration per synapse.

**Args:**
- `spikes_pre`: [N] bool
- `spikes_post`: [N] bool
- `V_dendrite`: [N] float, dendritic voltages (mV)

##### `update_plasticity_ca_based(M: float, G: np.ndarray)`

Ca²⁺-based LTP/LTD (Graupner-Brunel PNAS 2012).

**Args:**
- `M`: Global modulatory signal ∈ [0,1]
- `G`: [N] OLM gating per neuron ∈ [0,1]

##### `enforce_spectral_constraint(rho_target: float = 0.95)`

Enforce ρ(W) ≤ rho_target for network stability.

**Args:**
- `rho_target`: Target spectral radius

---

### `core.hierarchical_laminar`

#### `class HierarchicalLaminarModel`

ZINB inference with random effects and MRF prior.

**Constructor:**
```python
HierarchicalLaminarModel(
    n_layers: int = 4,
    n_markers: int = 4,
    lambda_mrf: float = 0.5
)
```

**Methods:**

##### `fit_em_vectorized(cells: List[CellDataHier], max_iter: int) -> np.ndarray`

Variational EM with vectorized operations.

**Args:**
- `cells`: List of cell data with neighbors
- `max_iter`: Maximum EM iterations

**Returns:**
- `np.ndarray [N, n_layers]`: Responsibilities q(L_n)

##### `assign_layers(cells, q: np.ndarray) -> np.ndarray`

MAP layer assignment.

**Args:**
- `cells`: List of cells
- `q`: [N, n_layers] responsibilities

**Returns:**
- `np.ndarray [N]`: Layer indices (0-3)

---

### `core.theta_swr_switching`

#### `class NetworkStateController`

Controls theta ↔ SWR state transitions.

**Constructor:**
```python
NetworkStateController(
    params: StateTransitionParams,
    dt: float = 0.1
)
```

**Methods:**

##### `step() -> Tuple[NetworkState, bool]`

One timestep of state machine.

**Returns:**
- `NetworkState`: Current state (THETA/SWR/TRANSITION)
- `bool`: Whether state changed

##### `get_inhibition_factor() -> float`

Returns inhibition scaling factor.

**Returns:**
- `float`: 1.0 (theta) or 0.5 (SWR)

##### `get_recurrence_factor() -> float`

Returns recurrence scaling factor.

**Returns:**
- `float`: 1.0 (theta) or 2.0 (SWR)

---

## Data Structures

### `CellDataHier`

```python
@dataclass
class CellDataHier:
    cell_id: int
    animal_id: int
    x: float
    y: float
    z: float  # Depth [0,1]
    s: float  # Longitudinal [0,1]
    transcripts: np.ndarray  # [4] marker counts
    neighbors: List[int]  # k-NN indices
```

### `InputSource`

```python
class InputSource(Enum):
    CA3 = "CA3"      # Recurrent, normal plasticity
    EC = "EC"        # Feedforward, 10x reduced
    LOCAL = "LOCAL"  # Intra-CA1, normal
```

### `NetworkState`

```python
class NetworkState(Enum):
    THETA = "theta"
    SWR = "swr"
    TRANSITION = "transition"
```

---

## Parameter Reference

### Plasticity Parameters

```python
params.plasticity.tau_Ca = 20.0        # ms (Graupner 2012)
params.plasticity.theta_d = 1.0        # μM (LTD threshold)
params.plasticity.theta_p = 2.0        # μM (LTP threshold)
params.plasticity.eta_p = 0.001        # LTP rate
params.plasticity.eta_d = 0.0005       # LTD rate
params.plasticity.nu_target = 5.0      # Hz (homeostasis)
```

### Compartment Parameters

```python
params.compartment.g_h = [0.5, 1.5, 3.0, 5.0]  # mS/cm² (Magee 1998)
params.compartment.V_half_h = [-82, -85, -88, -90]  # mV
params.compartment.C_soma = [1.0, 1.0, 1.0, 1.0]  # μF/cm²
```

### SWR Parameters

```python
params.swr.SWR_duration_mean = 50.0    # ms (curated dataset)
params.swr.SWR_duration_std = 20.0     # ms
params.swr.inhibition_reduction = 0.5  # 50% reduction
params.swr.recurrence_boost = 2.0      # 2x increase
```

---

## Error Handling

All functions raise appropriate exceptions:

- `ValueError`: Invalid parameter values
- `AssertionError`: Failed validation checks
- `RuntimeError`: Convergence failures

**Example:**
```python
try:
    W = UnifiedWeightMatrix(connectivity, weights, sources, params)
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

---

## Performance Tips

1. **Vectorization**: All core loops use NumPy
2. **Sparse matrices**: Use `scipy.sparse` for large networks
3. **Batch size**: Process spikes in batches of 100ms
4. **Seed for reproducibility**: Always set `np.random.seed(42)`

---

**Last updated**: December 14, 2025
