# Hybrid Neuro-AI Rationale

Version: 1.0  
Status: Draft (compatible with existing APIs)

## What is biologically grounded
- **Action selection & inhibition**: Regime switching (NORMAL/CAUTION/DEFENSIVE) mirrors basal-ganglia-like gating—risk raises inhibition and suppresses exploration.
- **Prediction-error learning**: Updates are driven by Δ = observed − predicted with clipping and EMA smoothing, mirroring dopaminergic prediction-error signals.
- **Regime-dependent time constants**: Threat accelerates adaptation by shortening effective τ (via `tau_scale`) and increasing inhibition gain.
- **Replay/consolidation rhythm**: CognitiveRhythm keeps wake/sleep pacing for consolidation phases.

## What is an engineering abstraction
- Bounded numerical updates, deterministic hysteresis/cooldown, and clipping for CI repeatability.
- Metrics-first design (`NeuroAIStepMetrics`) for stability/oscillation monitoring.
- Opt-in adapters (`SynapticMemoryAdapter`, `PredictionErrorAdapter`, `RegimeController`) that delegate to legacy implementations by default.
- Feature flags (`enable_adaptation`, `enable_regime_switching`) allow instant rollback.

## Why hybrid is better (measurable)
- **Stability**: Bounded bias (`max_bias`), inhibition gain, and hysteresis cap oscillations; tests assert low flip-rate under jittery risk.
- **Responsiveness**: Δ-driven bias reduces residual error over repeated exposures; defensive regime shortens τ for faster adaptation.
- **Safety**: Risk increases inhibition and reduces exploration deterministically; cooldown prevents flip-flop.
- **Compatibility**: Default path equals prior behavior (golden compatibility test), keeping public APIs unchanged.
