# Hybrid Truth Map

## Biological grounding (what is modeled)
- **Prediction-error learning**: Δ = observed − predicted with EMA smoothing (`PredictionErrorAdapter`, `prediction_error.compute_delta`).
- **Threat-driven inhibition**: Regime switching (NORMAL/CAUTION/DEFENSIVE) increases inhibition gain and shortens τ under risk (`RegimeController`).
- **Synaptic consolidation**: Multi-level decay and gated transfers between L1/L2/L3 (`MultiLevelSynapticMemory`).
- **Pacing rhythms**: Wake/sleep counters act as oscillatory control for consolidation windows (`CognitiveRhythm`).
- **Action selection**: ε-greedy selection and Δ-driven stats in synergy memory (`SynergyExperienceMemory`).

## Engineering abstraction (why it differs from biology)
- Bounded updates (clip Δ, clamp bias, limit inhibition gain) to avoid numerical runaway in CI.
- Hysteresis + cooldown to prevent regime flip-flop under jittery risk signals.
- Deterministic EMA predictors and neutral defaults so tests are reproducible.
- Feature flags (`MLSDM_NEURO_HYBRID_ENABLE`, `MLSDM_NEURO_LEARNING_ENABLE`, `MLSDM_NEURO_REGIME_ENABLE`) keep behavior OFF by default.
- Contract API (`NeuroSignalPack`, `NeuroOutputPack`, `NeuroContractMetadata`, `NeuroModuleAdapter`) standardizes inputs/outputs without altering public APIs.

## Why the hybrid is better (measurable)
- **M1 Stability**: Regime flip rate bounded under stationary risk (test `test_neuro_hybrid_metrics.py::test_regime_flip_rate_stable`).
- **M2 Responsiveness**: Step change in risk reaches DEFENSIVE within a bounded number of ticks (same test module).
- **M3 Risk sensitivity**: Inhibition gain increases monotonically with threat spikes.
- **M4 Learning convergence**: Mean |Δ| decreases over repeated episodes when learning is enabled while default OFF path remains bit-for-bit compatible (`test_neuro_hybrid_contracts.py::test_default_off_matches_legacy`).

Default behavior remains the legacy pipeline; hybrid dynamics are opt-in and rollbackable via a single global flag plus per-module overrides.
