# Usage Guide

Practical examples and usage patterns for CA1 Hippocampus Framework.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Advanced Examples](#advanced-examples)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)

## Basic Usage

### 1. Load Parameters

```python
from data.biophysical_parameters import get_default_parameters

# Get all parameters (from 13 DOI sources)
params = get_default_parameters()

# Inspect parameters
print(f"LTP threshold: {params.plasticity.theta_p} μM")  # 2.0 μM
print(f"HCN gradient: {params.compartment.g_h}")  # [0.5, 1.5, 3.0, 5.0]
```

### 2. Create Unified Weight Matrix

```python
import numpy as np
from plasticity.unified_weights import UnifiedWeightMatrix, create_source_type_matrix

# Set seed for reproducibility
np.random.seed(42)

# Network size
N = 100

# Create connectivity (10% sparse)
connectivity = np.random.rand(N, N) < 0.1
np.fill_diagonal(connectivity, False)

# Layer assignments (4 layers)
layer_assignments = np.random.randint(0, 4, N)

# Initial weights (log-normal distribution)
initial_weights = np.random.lognormal(0, 0.5, (N, N))
initial_weights = np.clip(initial_weights, 0.01, 10.0)

# Input source types (CA3/EC/LOCAL)
source_types = create_source_type_matrix(N, layer_assignments)

# Create unified matrix
W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)
```

### 3. Simulation Loop

```python
# Simulation parameters
T = 1000.0  # ms
dt = 0.1
n_steps = int(T / dt)

# Run simulation
for step in range(n_steps):
    t = step * dt
    
    # Generate random spikes (example)
    spikes_pre = np.random.rand(N) < 0.01
    spikes_post = np.random.rand(N) < 0.01
    V_dendrite = np.random.randn(N) * 10 - 60  # mV
    
    # Update STP (every timestep)
    W.update_stp(spikes_pre, spikes_post)
    
    # Update Ca²⁺ (every timestep)
    W.update_calcium(spikes_pre, spikes_post, V_dendrite)
    
    # Update plasticity (every 10 timesteps = 1 ms)
    if step % 10 == 0:
        M = 1.0  # Modulatory signal (learning mode)
        G = np.zeros(N)  # No OLM gating
        W.update_plasticity_ca_based(M, G)
    
    # Optional: enforce stability every 100 ms
    if step % 1000 == 0:
        W.enforce_spectral_constraint(rho_target=0.95)

# Get final weights
W_eff = W.get_effective_weights()
stats = W.get_statistics()

print(f"Final ρ(W) = {stats['spectral_radius']:.3f}")
print(f"Mean Ca²⁺ = {stats['Ca_mean']:.2f} μM")
```

## Advanced Examples

### 1. Laminar Structure Inference

```python
from core.hierarchical_laminar import HierarchicalLaminarModel, CellDataHier, build_knn_neighbors

# Generate or load cell data
cells = []
for i in range(1000):
    z = np.random.rand()  # Depth [0, 1]
    s = np.random.rand()  # Longitudinal [0, 1]
    
    # Transcripts (example: layer-dependent)
    layer = min(int(z * 4), 3)
    transcripts = np.zeros(4)
    transcripts[layer] = np.random.poisson(5)
    
    cells.append(CellDataHier(
        cell_id=i,
        animal_id=0,
        x=np.random.rand(),
        y=np.random.rand(),
        z=z,
        s=s,
        transcripts=transcripts,
        neighbors=None
    ))

# Build k-NN spatial neighbors
cells = build_knn_neighbors(cells, k=10)

# Fit hierarchical model
model = HierarchicalLaminarModel(lambda_mrf=0.5)
q = model.fit_em_vectorized(cells, max_iter=30)

# Assign layers
assignments = model.assign_layers(cells, q)

print(f"Layer distribution: {np.bincount(assignments)}")

# Get animal effects
animal_effects = model.get_animal_effects()
```

### 2. Theta-SWR State Switching

```python
from core.theta_swr_switching import NetworkStateController, StateTransitionParams, ReplayDetector

# Create state controller
params_transition = StateTransitionParams(
    P_theta_to_SWR=0.001,  # 0.1% chance per ms
    P_SWR_to_theta=0.05,   # 5% chance per ms
    SWR_duration_mean=50.0,
    SWR_duration_std=20.0
)

controller = NetworkStateController(params_transition, dt=0.1)

# Create replay detector
detector = ReplayDetector()

# Simulation
for step in range(10000):
    t = step * 0.1
    
    # Step state machine
    state, state_changed = controller.step()
    
    # Get modulation factors
    inh_factor = controller.get_inhibition_factor()  # 0.5 during SWR
    rec_factor = controller.get_recurrence_factor()  # 2.0 during SWR
    theta_drive = controller.get_theta_drive(t, f_theta=8.0)
    
    # Apply to network
    # (integrate with your simulation)
    
    # Detect replay during SWR
    if state == NetworkState.SWR:
        replay_event = detector.detect(t, spikes, state)
        if replay_event:
            print(f"Replay detected at t={t:.1f}ms, duration={replay_event.duration():.1f}ms")
```

### 3. AI Memory Integration

```python
from ai_integration.memory_module import LLMWithCA1Memory

# Create memory module
ai_memory = LLMWithCA1Memory(params.ai)

# Encoding phase (online learning)
events = [...]  # Your LLM hidden states
for event in events:
    # Encode event (example)
    h_t = np.random.randn(params.ai.d_model)  # Your LLM encoding
    v_t = np.random.randn(params.ai.value_dim)  # Value to store
    position = np.random.rand(2)  # Spatial position (for novelty)
    
    # Process with CA1 memory
    ai_memory.process_step(h_t, v_t, position)

# Retrieval phase
query_h = np.random.randn(params.ai.d_model)
enhanced_h = ai_memory.retrieve_and_fuse(query_h)

# Consolidation (offline replay)
replayed_indices = ai_memory.consolidate(n_episodes=100)
print(f"Replayed {len(replayed_indices)} episodes")
```

## Common Patterns

### Pattern 1: Input-Specific Plasticity

```python
# Different learning rates for CA3 vs EC
from plasticity.unified_weights import InputSource

# Create source types
source_types = np.full((N, N), InputSource.LOCAL.value, dtype=object)

# Mark CA3 synapses (recurrent)
for i in range(N):
    if layer_assignments[i] >= 2:  # Deep layers
        ca3_sources = np.where(layer_assignments >= 2)[0]
        for j in ca3_sources:
            if connectivity[i, j]:
                source_types[i, j] = InputSource.CA3.value

# Mark EC synapses (feedforward)
for i in range(N):
    if layer_assignments[i] <= 1:  # Superficial layers
        ec_sources = np.random.choice(N, size=10, replace=False)
        for j in ec_sources:
            if connectivity[i, j]:
                source_types[i, j] = InputSource.EC.value

# Now CA3 will have normal plasticity, EC will have 10x lower
W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)
```

### Pattern 2: OLM Gating Control

```python
# Control learning via OLM gating
G = np.ones(N) * 0.5  # 50% gating (partial learning)

# Different gating per layer
for i in range(N):
    layer = layer_assignments[i]
    if layer <= 1:
        G[i] = 0.2  # Strong gating (superficial layers)
    else:
        G[i] = 0.8  # Weak gating (deep layers)

# Apply during plasticity
W.update_plasticity_ca_based(M=1.0, G=G)
```

### Pattern 3: Homeostatic Regulation

```python
# Compute firing rates
spike_counts = np.array([...])  # From simulation
firing_rates = spike_counts / (T / 1000.0)  # Hz

# Apply homeostatic scaling
W.apply_homeostatic_scaling(firing_rates)

# Result: neurons with high rate → weights decreased
#         neurons with low rate → weights increased
```

## Best Practices

### 1. Always Set Seed

```python
import numpy as np
np.random.seed(42)  # For reproducibility
```

### 2. Validate Stability

```python
# After long simulations
W.enforce_spectral_constraint(rho_target=0.95)
stats = W.get_statistics()

if stats['spectral_radius'] >= 1.0:
    print("WARNING: Network unstable!")
```

### 3. Batch Plasticity Updates

```python
# Don't update every timestep (expensive)
if step % 10 == 0:  # Every 1 ms
    W.update_plasticity_ca_based(M, G)
```

### 4. Monitor Ca²⁺ Levels

```python
stats = W.get_statistics()
if stats['Ca_max'] > 10.0:
    print("WARNING: Excessive Ca²⁺!")
```

### 5. Save/Load State

```python
# Save
np.savez('simulation_state.npz',
         W_base=W.W_base,
         u=W.u,
         R=W.R,
         Ca=W.Ca)

# Load
data = np.load('simulation_state.npz')
W.W_base = data['W_base']
W.u = data['u']
W.R = data['R']
W.Ca = data['Ca']
```

## Performance Optimization

### 1. Use Sparse Matrices

```python
from scipy.sparse import csr_matrix

# For large networks
connectivity_sparse = csr_matrix(connectivity)
```

### 2. Vectorize Custom Operations

```python
# Bad (slow)
for i in range(N):
    for j in range(N):
        if connectivity[i, j]:
            result[i, j] = compute(i, j)

# Good (fast)
mask = connectivity
result[mask] = vectorized_compute(np.where(mask))
```

### 3. Profile Code

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

## Troubleshooting

### Issue: Weights Explode

```python
# Solution 1: Enforce spectral constraint more frequently
if step % 100 == 0:
    W.enforce_spectral_constraint()

# Solution 2: Reduce learning rates
params.plasticity.eta_p *= 0.5
params.plasticity.eta_d *= 0.5
```

### Issue: No Plasticity

```python
# Check Ca²⁺ levels
stats = W.get_statistics()
print(f"Ca mean: {stats['Ca_mean']}")
print(f"Ca max: {stats['Ca_max']}")

# Should be in range [θ_d, θ_p] = [1.0, 2.0] μM for plasticity
```

### Issue: Reproducibility Fails

```python
# Set ALL random seeds
import numpy as np
import random

np.random.seed(42)
random.seed(42)

# Use consistent dtype
connectivity = connectivity.astype(bool)
weights = weights.astype(np.float64)
```

---

**Last updated**: December 14, 2025
