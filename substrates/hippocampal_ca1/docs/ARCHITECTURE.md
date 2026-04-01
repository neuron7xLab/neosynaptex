# Architecture

System architecture of CA1 Hippocampus Framework v2.0

## High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Application                      │
│              (LLM, Research, Education)                  │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌───────▼────────┐
│  AI Integration │       │ Neuroscience    │
│  (memory_module)│       │ (validators)    │
└───────┬────────┘       └───────┬────────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │    Core CA1 Model       │
        │  - Laminar structure    │
        │  - Neuron dynamics      │
        │  - Unified weights      │
        │  - State switching      │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  Biophysical Parameters │
        │  (all from literature)  │
        └─────────────────────────┘
```

## Module Dependencies

```
data.biophysical_parameters (no dependencies)
    ↓
core.hierarchical_laminar
core.neuron_model
core.theta_swr_switching
    ↓
plasticity.unified_weights
    ↓
ai_integration.memory_module
validation.validators
```

## Data Flow

### Forward Pass (Dynamics)

```
Input Spikes [N]
    ↓
UnifiedWeightMatrix.get_effective_weights()
    → W_eff = W_base × u × R
    ↓
Synaptic Currents [N, 4]  (E_soma, E_dend, I_soma, I_dend)
    ↓
TwoCompartmentNeuron.step()
    → Soma: V_s, AHP
    → Dendrite: V_d, HCN, NMDA
    ↓
Output Spikes [N]
```

### Backward Pass (Learning)

```
Spikes [N] + Voltages [N]
    ↓
UnifiedWeightMatrix.update_calcium()
    → τ_Ca dCa/dt = -Ca + A_pre·S_j + A_post·S_i + A_NMDA·σ(V_d)
    ↓
UnifiedWeightMatrix.update_plasticity_ca_based()
    → dW/dt = η_p·𝟙[Ca>θ_p]·(W_max-W) - η_d·𝟙[θ_d<Ca≤θ_p]·(W-W_min)
    ↓
Updated W_base [N, N]
```

## Component Responsibilities

### `data.biophysical_parameters`

**Purpose**: Single source of truth for all parameters  
**Key Classes**:
- `CA1Parameters`: Master container
- `LaminarMarkers`: smFISH data (58,065 cells)
- `CompartmentParams`: Soma/dendrite biophysics
- `PlasticityParams`: Ca²⁺ thresholds, learning rates

**Invariants**:
- All parameters have DOI source
- Validation on init: `params.validate()`

### `plasticity.unified_weights`

**Purpose**: Unified W+STP+Ca²⁺ matrix  
**Key Classes**:
- `UnifiedWeightMatrix`: Single matrix for dynamics + learning
- `InputSource`: Channel types (CA3/EC/LOCAL)

**Invariants**:
- W_base ∈ [W_min, W_max]
- u ∈ [0, U_max]
- R ∈ [0, 1]
- Ca ≥ 0

**Critical Methods**:
- `get_effective_weights()`: O(N²) but cached
- `update_stp()`: O(E) where E = #synapses
- `update_calcium()`: O(E)
- `update_plasticity_ca_based()`: O(E)

### `core.hierarchical_laminar`

**Purpose**: Infer 4 layers from transcriptomics  
**Algorithm**: Variational EM + MRF

**Complexity**:
- E-step: O(N·K·L) where N=cells, K=markers, L=layers
- M-step: O(N·K·L)
- MRF: O(N·k_neighbors) via sparse matrix

**Vectorization**:
- All loops replaced with NumPy broadcasting
- MRF via `scipy.sparse.csr_matrix @ q`

### `core.theta_swr_switching`

**Purpose**: Control network operational state  
**State Machine**:

```
     P=0.001/ms
THETA ────────────→ TRANSITION
  ↑                      ↓
  │                   (10 ms)
  │                      ↓
  └────────────── SWR (50±20 ms)
     P=0.05/ms
```

**Effects**:
- SWR inhibition: ×0.5
- SWR recurrence: ×2.0
- SWR ACh: 1.0 → 0.1

### `ai_integration.memory_module`

**Purpose**: LLM long-term memory via CA1 mechanisms  
**Architecture**:

```
LLM hidden [d_model]
    ↓ Encoder
CA1 key [key_dim] + theta_phase
    ↓ Store
Memory [10K slots]
    ↑ Retrieve (top-k)
Retrieved [value_dim]
    ↓ Decoder
Fused output [d_model]
```

**Mechanisms**:
- **Online**: Low η, reading mode
- **Offline**: High η, replay consolidation
- **Novelty**: Filters storage by spatial novelty

## Threading Model

**Current**: Single-threaded  
**Future**: Thread-safe via locks on W matrix

## Memory Layout

```
UnifiedWeightMatrix (100x100):
  W_base: 80 KB (float64)
  u: 80 KB
  R: 80 KB
  Ca: 80 KB
  Total: ~320 KB

HierarchicalModel (1000 cells):
  Data: ~2 MB
  MRF matrix: ~1 MB (sparse)
  Total: ~3 MB
```

## Performance Bottlenecks

1. **Laminar EM**: O(N·K·L·iter)
   - **Solution**: Vectorized E/M steps
   - **Speedup**: 2.5x

2. **Weight updates**: O(E) per timestep
   - **Solution**: Batch updates every 10 timesteps
   - **Speedup**: 1.6x

3. **Spectral radius**: O(N³) eigenvalue decomposition
   - **Solution**: Cache, recompute only on large changes
   - **Speedup**: 10x

## Extensibility Points

### Adding New Plasticity Rules

```python
class MyPlasticityRule:
    def update_weight(self, W, spikes, voltages):
        # Your rule here
        return W_new

# Plug into UnifiedWeightMatrix
W.custom_plasticity = MyPlasticityRule()
```

### Adding New Input Channels

```python
class InputSource(Enum):
    CA3 = "CA3"
    EC = "EC"
    LOCAL = "LOCAL"
    MY_CHANNEL = "my_channel"  # Add here

# Define plasticity rate
eta_my_channel = 0.0002
```

### Adding New State Modes

```python
class NetworkState(Enum):
    THETA = "theta"
    SWR = "swr"
    MY_STATE = "my_state"  # Add here

# Define transition probabilities
P_theta_to_my_state = 0.005
```

## Testing Architecture

```
Golden Tests (5)
    ├─ test_network_stability
    ├─ test_calcium_plasticity
    ├─ test_input_specific
    ├─ test_theta_swr
    └─ test_reproducibility

Unit Tests
    ├─ test_unified_weights.py
    ├─ test_hierarchical_laminar.py
    ├─ test_theta_swr.py
    └─ test_memory_module.py

Integration Tests
    └─ test_full_pipeline.py
```

## Future Architecture (v3.0)

```
┌────────────────────────────────┐
│     Multi-Region Model         │
│  CA1 ←→ CA3 ←→ DG ←→ EC        │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│     JAX/PyTorch Backend        │
│     (GPU acceleration)         │
└────────────────────────────────┘
         ↓
┌────────────────────────────────┐
│  Behavioral Integration        │
│  (position, head direction)    │
└────────────────────────────────┘
```

---

**Last updated**: December 14, 2025
