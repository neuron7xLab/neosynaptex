# Neuro-AI Functional Contracts

Version: 1.0  
Status: Draft (backwards-compatible)

This document formalizes the functional contracts for biomimetic components in MLSDM. Each contract is explicitly testable and backed by source paths.

## Modules

### MultiLevelSynapticMemory (`src/mlsdm/memory/multi_level_memory.py`)
- **Role (computational)**: Multi-timescale synaptic buffer (L1/L2/L3) with gated consolidation.
- **Inputs**: `event: np.ndarray[dim]`, decay rates `λ1/λ2/λ3`, thresholds `θ1/θ2`, gating `g12/g23`, optional `correlation_id`.
- **Outputs**: Updated L1/L2/L3 traces, consolidation flags (via observability hook), memory usage estimate.
- **Invariants / bounds**: `0<λ<=1`, `θ>0`, `0<=g<=1`, no NaN/inf, dimension must match, bounded update scale ∈ [0.2, 2.0].
- **Time constants**: Per-level decay acts as τ; optional regime modulation shortens τ via `tau_scale>=0.6`.
- **Failure mode**: Reject invalid shapes with `ValueError`; if calibration unavailable, use safe defaults and zeroed traces; safe no-op on empty updates.
- **Hybrid improvement**: Bounded decay and gating, observability metrics (`record_synaptic_update`), deterministic in-place updates for testability.

### PhaseEntangledLatticeMemory (`src/mlsdm/memory/phase_entangled_lattice_memory.py`)
- **Role**: Phase-coded associative memory (bidirectional retrieval).
- **Inputs**: Keys/values embeddings, phase weights, similarity thresholds, capacity bound.
- **Outputs**: Top-k results with phase coherence, eviction decisions.
- **Invariants / bounds**: Capacity hard limit, similarity threshold prevents degenerate matches, no NaN phases, eviction keeps memory bounded.
- **Time constants**: None (stateless per call); retrieval latency tracked via observability.
- **Failure mode**: Empty result set when below threshold; prior state unchanged on invalid phase input or corruption detection.
- **Hybrid improvement**: Deterministic eviction ordering, bounded similarity thresholds for stability.

### CognitiveRhythm (`src/mlsdm/rhythm/cognitive_rhythm.py`)
- **Role**: Wake/sleep pacing for consolidation and replay.
- **Inputs**: `wake_duration`, `sleep_duration`, `step()` ticks, optional risk modulation.
- **Outputs**: `phase` (`wake|sleep`), `counter`, convenience `is_wake/is_sleep`.
- **Invariants / bounds**: Durations > 0; transitions bounded by hysteresis/cooldown when regime control is enabled; phase toggles only after counters expire.
- **Time constants**: Wake/sleep durations act as τ; optional regime control scales τ with floor `>=0.6`.
- **Failure mode**: Stays in last stable phase if durations invalid; counter resets on transition.
- **Hybrid improvement**: Boolean fast-path checks; optional regime-aware tau scaling for defensive mode.

### SynergyExperienceMemory (`src/mlsdm/cognition/synergy_experience.py`)
- **Role**: Prediction-error-driven combo selection with ε-greedy balance.
- **Inputs**: `state_signature`, `combo_id`, `delta_eoi`, `epsilon`, EMA smoothing factor.
- **Outputs**: `ComboStats` (attempts, mean/EMA Δeoi), exploration/exploitation counts.
- **Invariants / bounds**: `epsilon in [0,1]`, sanitized Δeoi (no NaN/inf), bounded EMA α, bounded attempts counter growth via locks.
- **Time constants**: EMA smoothing factor sets effective τ for Δeoi convergence.
- **Failure mode**: Neutral stats before `min_trials_for_confidence`; exploration fallback when stats missing or corrupted stats reset.
- **Hybrid improvement**: Thread-safe updates, bounded EMA for stability, explicit Δ-driven learning (not reward-only).

## Contract Guardrails
- **Prediction-error first**: Adaptation uses Δ = observed − predicted (see `PredictionErrorAdapter`).
- **Risk-driven dynamics**: Threat/risk modulates inhibition gain, exploration rate, and tau scaling via `RegimeController`.
- **Stability**: Bounded updates, hysteresis, cooldown, and clipping prevent oscillations.
- **Observability**: Metrics exposed via adapters (`NeuroAIStepMetrics`) and existing telemetry hooks (`MemoryMetricsExporter`).
- **Fail-safe degrade mode**: When feature flags are off, adapters delegate to legacy modules unchanged and return neutral metrics (regime NORMAL, gain=1.0).
