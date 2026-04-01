# Emergence Tracking

## Overview

Emergence tracking provides real-time monitoring of attractor formation and phase transitions in neural network dynamics. This enables study of how stable states emerge from chaotic or random initial conditions.

## Attractor Crystallization

### Concept

Attractor crystallization describes the process by which network dynamics transition from:
- **Fluid**: Random, uncorrelated activity
- **Nucleation**: First stable patterns appear
- **Growth**: Multiple attractors form
- **Crystallized**: High-stability basins dominate

### AttractorCrystallizer

Online detector for attractor basins using lightweight clustering.

**Architecture:**
- Ring buffer: Bounded memory (default 1000 states)
- Incremental PCA: Periodic dimensionality reduction
- DBSCAN-lite: Deterministic clustering via scipy cKDTree
- No sklearn dependency

**Parameters:**
```python
crystallizer = AttractorCrystallizer(
    state_dim=200,           # Full state dimensionality
    max_buffer_size=1000,    # Ring buffer size
    snapshot_dim=100,        # Subsampled dimension
    pca_update_interval=100, # PCA recomputation frequency
    cluster_eps=0.1,         # DBSCAN epsilon
    cluster_min_samples=5,   # Minimum cluster size
)
```

**Usage:**
```python
from bnsyn.emergence import AttractorCrystallizer, Phase

crystallizer = AttractorCrystallizer(state_dim=100, snapshot_dim=50)

# Observe network states
for step in range(1000):
    state = network.state.V_mV  # or any state vector
    temperature = temp_schedule.T or 1.0
    crystallizer.observe(state, temperature)

# Get results
attractors = crystallizer.get_attractors()
cryst_state = crystallizer.get_crystallization_state()

print(f"Phase: {cryst_state.phase.name}")
print(f"Progress: {cryst_state.progress:.2f}")
print(f"Attractors: {len(attractors)}")

for i, attr in enumerate(attractors):
    print(f"  Attractor {i}:")
    print(f"    Stability: {attr.stability:.3f}")
    print(f"    Basin radius: {attr.basin_radius:.3f}")
    print(f"    Crystallization: {attr.crystallization:.3f}")
```

`get_attractors()` returns the **currently active** attractor basins supported by the crystallizer ring buffer. It is an online view of the present emergent structure, not an append-only historical ledger of every attractor ever seen.

**Attractor Properties:**
- `center`: Attractor center in state space (subsampled)
- `basin_radius`: Approximate basin of attraction radius
- `stability`: Fraction of observations in basin (∈ [0, 1])
- `formation_step`: When attractor was first detected
- `crystallization`: Local crystallization progress (∈ [0, 1])

## Integration Map: 7 Connection Points

1. **State intake → ring buffer**: `observe()` subsamples full network state into the bounded attractor buffer.
2. **Ring buffer → PCA**: buffered state windows periodically update the low-dimensional tracking basis.
3. **PCA space → clustering**: transformed snapshots are clustered into candidate attractor basins.
4. **Detected basins → active attractor refresh**: current detections are reconciled with the active attractor list.
5. **Active attractors → callbacks**: genuinely new basins emit `on_attractor_formed` notifications.
6. **Active attractors → phase state**: refreshed attractor topology updates crystallization phase.
7. **Public state → external consumers**: `get_attractors()` and `get_crystallization_state()` expose the live emergence view to dashboards, CLI, and experiments.

## Integration Tasks: 7 Synchronization / Communication Checks

1. **Buffer coherence**: verify subsampled snapshots preserve shape and deterministic insertion order.
2. **PCA resilience**: keep fail-closed behavior when SVD cannot refresh the basis.
3. **Cluster validity**: ensure DBSCAN-lite only emits clusters with enough support.
4. **Refresh identity**: preserve `formation_step` for matched active basins.
5. **Refresh turnover**: drop stale basins when the buffer shifts to a new attractor regime.
6. **Callback hygiene**: emit formation callbacks only for genuinely new active basins.
7. **Public-path proof**: validate the whole chain through `observe()` so downstream consumers receive the correct live attractor view.

### Callbacks

Register callbacks for real-time event notification:

```python
def on_new_attractor(attractor):
    print(f"New attractor at step {attractor.formation_step}")

def on_phase_change(old_phase, new_phase):
    print(f"Phase transition: {old_phase.name} → {new_phase.name}")

crystallizer.on_attractor_formed(on_new_attractor)
crystallizer.on_phase_transition(on_phase_change)
```

## Phase Transition Detection

### Concept

Phase transitions track changes in critical branching ratio (sigma):
- **Subcritical**: Dying activity (σ < 1)
- **Critical**: Self-organized criticality (σ ≈ 1)
- **Supercritical**: Runaway excitation (σ > 1)

### PhaseTransitionDetector

Tracks sigma history and detects threshold crossings.

**Parameters:**
```python
detector = PhaseTransitionDetector(
    subcritical_threshold=0.95,   # Upper bound for subcritical
    supercritical_threshold=1.05, # Lower bound for supercritical
    history_size=200,              # Max history length
)
```

**Usage:**
```python
from bnsyn.criticality import PhaseTransitionDetector, CriticalPhase

detector = PhaseTransitionDetector()

# Observe sigma values
for step in range(1000):
    metrics = network.step()
    new_phase = detector.observe(metrics["sigma"], step)
    
    if new_phase is not None:
        print(f"Transition at step {step} to {new_phase.name}")

# Get history
transitions = detector.get_transitions()
sigma_history = detector.get_sigma_history()
phase_history = detector.get_phase_history()

# Analyze dynamics
deriv = detector.sigma_derivative()  # d(sigma)/d(step)
time_in_phase = detector.time_in_phase(current_step)
```

**Transition Properties:**
- `step`: When transition occurred
- `from_phase`: Phase before transition
- `to_phase`: Phase after transition
- `sigma_before`: Sigma value before transition
- `sigma_after`: Sigma value after transition
- `sharpness`: |sigma_after - sigma_before|

### Callbacks

```python
def on_transition(transition):
    print(f"Transition: {transition.from_phase.name} → {transition.to_phase.name}")
    print(f"  Sharpness: {transition.sharpness:.4f}")

detector.on_transition(on_transition)
```

## Combined Usage

Track both attractors and phase transitions together:

```python
from bnsyn.criticality import PhaseTransitionDetector
from bnsyn.emergence import AttractorCrystallizer
from bnsyn.temperature.schedule import TemperatureSchedule, TemperatureParams

# Setup trackers
detector = PhaseTransitionDetector()
crystallizer = AttractorCrystallizer(state_dim=N, snapshot_dim=min(100, N))
temp_schedule = TemperatureSchedule(TemperatureParams())

# Run simulation with tracking
for step in range(5000):
    m = network.step()
    
    # Track phase transitions
    detector.observe(m["sigma"], step)
    
    # Track attractor crystallization
    crystallizer.observe(network.state.V_mV, temp_schedule.T or 1.0)
    
    # Update temperature
    temp_schedule.step_geometric()

# Analyze results
transitions = detector.get_transitions()
attractors = crystallizer.get_attractors()
cryst_state = crystallizer.get_crystallization_state()

print(f"Total transitions: {len(transitions)}")
print(f"Final phase: {detector.current_phase().name}")
print(f"Crystallization: {cryst_state.phase.name} ({cryst_state.progress:.2%})")
print(f"Attractors detected: {len(attractors)}")
```

## Determinism

Both components are deterministic:

**AttractorCrystallizer:**
- Clustering is deterministic (cKDTree query order)
- PCA uses numpy SVD (deterministic)
- Ring buffer updates are deterministic
- Given same input sequence → same attractors

**PhaseTransitionDetector:**
- Pure threshold logic (no randomness)
- History tracking is deterministic
- Given same sigma sequence → same transitions

**Validation:**
```python
# Run 1
crystallizer1 = AttractorCrystallizer(state_dim=N, snapshot_dim=50)
for state in states:
    crystallizer1.observe(state, temperature=1.0)
progress1 = crystallizer1.crystallization_progress()

# Run 2
crystallizer2 = AttractorCrystallizer(state_dim=N, snapshot_dim=50)
for state in states:
    crystallizer2.observe(state, temperature=1.0)
progress2 = crystallizer2.crystallization_progress()

assert progress1 == progress2  # Exact equality
```

## Visualization

Use EmergenceDashboard for real-time visualization (requires matplotlib):

```python
from bnsyn.viz import EmergenceDashboard

# Setup dashboard
dashboard = EmergenceDashboard()
dashboard.attach(network, crystallizer, sleep_cycle=None, consolidator=None)

# During simulation
for step in range(1000):
    network.step()
    crystallizer.observe(network.state.V_mV, temperature)
    
    if step % 100 == 0:
        dashboard.update()

# Save final visualization
dashboard.save_figure("emergence_tracking.png")
```

## Performance Notes

- **Memory:** Ring buffers bound memory usage
- **Compute:** PCA only every N steps (configurable)
- **Clustering:** cKDTree is O(N log N) for N points
- **Overhead:** Typically <5% of network step time

For large networks (N > 1000), use `snapshot_dim` to subsample:
```python
crystallizer = AttractorCrystallizer(
    state_dim=2000,
    snapshot_dim=200,  # 10x reduction
)
```

## References

- `src/bnsyn/emergence/crystallizer.py`: AttractorCrystallizer implementation
- `src/bnsyn/criticality/phase_transition.py`: PhaseTransitionDetector implementation
- `tests/test_attractor_crystallizer.py`: Smoke tests
- `tests/test_phase_transition_detector.py`: Smoke tests
- `tests/validation/test_crystallizer_real.py`: Validation tests
