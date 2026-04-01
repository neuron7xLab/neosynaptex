# Sleep–Emergence Stack

## Overview

The Sleep–Emergence Stack integrates sleep-wake cycles with memory consolidation, attractor crystallization, and phase transition tracking. This provides a cohesive framework for studying emergent dynamics in bio-inspired neural networks.

## Components

### SleepCycle

Orchestrates sleep-wake transitions with stage-specific temperature control and optional replay.

**Stages:**
- `WAKE`: Normal network operation with memory recording
- `LIGHT_SLEEP`: Temperature modulation begins
- `DEEP_SLEEP`: Low-temperature stage
- `REM`: Replay active, elevated temperature

**Key Features:**
- Memory recording during wake (periodic voltage snapshots)
- Pattern replay with noise during REM
- Configurable stage durations, temperature ranges, and replay settings

### MemoryConsolidator

High-level API for memory tagging, consolidation, and recall.

**Operations:**
- `tag(pattern, importance)`: Store a new memory pattern
- `consolidate(protein_level, temperature)`: Apply consolidation dynamics
- `recall(cue, threshold)`: Retrieve similar patterns

**Features:**
- Capacity-limited storage with eviction policy
- Protein-dependent consolidation strength
- Cosine similarity-based recall
- Deterministic tie-breaking for eviction

### PhaseTransitionDetector

Tracks critical phase transitions based on branching ratio (sigma).

**Phases:**
- `SUBCRITICAL`: σ < 0.95
- `CRITICAL`: 0.95 ≤ σ ≤ 1.05
- `SUPERCRITICAL`: σ > 1.05

**Features:**
- Real-time phase classification
- Transition event logging
- Sigma derivative estimation
- Configurable thresholds

### AttractorCrystallizer

Online attractor detection and crystallization tracking.

**Phases:**
- `FLUID`: No stable attractors
- `NUCLEATION`: First attractor detected
- `GROWTH`: Multiple attractors forming
- `CRYSTALLIZED`: High-stability attractors

**Features:**
- Dependency-free clustering (no sklearn)
- Incremental PCA for dimensionality reduction
- Ring buffer for bounded memory
- Deterministic attractor detection

## Minimal Usage

```python
from bnsyn.config import AdExParams, CriticalityParams, SynapseParams, TemperatureParams
from bnsyn.criticality import PhaseTransitionDetector
from bnsyn.emergence import AttractorCrystallizer
from bnsyn.memory import MemoryConsolidator
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.sleep import SleepCycle, default_human_sleep_cycle
from bnsyn.temperature.schedule import TemperatureSchedule

# Setup
pack = seed_all(42)
net = Network(
    NetworkParams(N=64),
    AdExParams(),
    SynapseParams(),
    CriticalityParams(),
    dt_ms=0.5,
    rng=pack.np_rng,
)
temp_schedule = TemperatureSchedule(TemperatureParams())
sleep_cycle = SleepCycle(net, temp_schedule, max_memories=100, rng=pack.np_rng)
consolidator = MemoryConsolidator(capacity=100)
phase_detector = PhaseTransitionDetector()
crystallizer = AttractorCrystallizer(state_dim=64, snapshot_dim=50)

# Wake phase
for _ in range(500):
    m = net.step()
    if _ % 20 == 0:
        importance = min(1.0, m["spike_rate_hz"] / 10.0)
        consolidator.tag(net.state.V_mV, importance)
        sleep_cycle.record_memory(importance)
    phase_detector.observe(m["sigma"], _)
    crystallizer.observe(net.state.V_mV, temp_schedule.T or 1.0)

# Sleep phase
sleep_stages = default_human_sleep_cycle()
sleep_cycle.sleep(sleep_stages)
consolidator.consolidate(protein_level=0.9, temperature=0.8)

# Check results
print(f"Memories: {sleep_cycle.get_memory_count()}")
print(f"Transitions: {len(phase_detector.get_transitions())}")
print(f"Attractors: {len(crystallizer.get_attractors())}")
print(f"Consolidation: {consolidator.stats()}")
```

## Demo Command

Run the end-to-end demo:

```bash
bnsyn sleep-stack --seed 123 --steps-wake 800 --steps-sleep 600 --out results/demo1
```

Outputs:
- `results/demo1/manifest.json`: Reproducibility metadata (seed, params, git SHA)
- `results/demo1/metrics.json`: Metrics (transitions, attractors, consolidation)
- `figures/demo1/summary.png`: Summary figure (if matplotlib installed)

Expected runtime: ~5-10 seconds with default parameters.

## Determinism Guarantees

All components are fully deterministic when using explicit RNG seeding:

```python
pack = seed_all(123)
# All subsequent operations with pack.np_rng produce identical results
```

**What is deterministic:**
- Memory tagging and eviction order
- Consolidation strength updates
- Phase transition detection
- Attractor clustering (with fixed input seed)
- Sleep stage progression
- Replay pattern selection

**What is hashed/compared in tests:**
- Sigma traces (float equality)
- Transition event lists (exact match)
- Consolidation stats (float approx)
- Memory counts (exact)

## Integration Notes

### With Existing DualWeights

SleepCycle does not replace DualWeights consolidation. Instead:
- SleepCycle controls wake/sleep staging and replay timing
- DualWeights/MemoryConsolidator implements *how* consolidation happens
- Temperature schedule gates plasticity via existing `gate_sigmoid`

### With Criticality Controller

PhaseTransitionDetector observes sigma from `BranchingEstimator` output:
- No interference with SigmaController gain updates
- Pure observation and logging
- Provides additional phase classification layer

## References

- `src/bnsyn/sleep/`: Sleep cycle implementation
- `src/bnsyn/memory/`: Memory consolidation and trace
- `src/bnsyn/criticality/`: Phase transition detection
- `src/bnsyn/emergence/`: Attractor crystallization
- `tests/validation/test_sleep_stack_effectiveness.py`: Validation tests
