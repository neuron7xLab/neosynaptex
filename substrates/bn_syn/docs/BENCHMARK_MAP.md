# Benchmark ↔ SPEC Map

This document maps benchmark metrics to SPEC components so every metric has a SPEC-anchored validation target.

| SPEC Component | Benchmark Metrics | Validation Intent |
| --- | --- | --- |
| P0-1 AdEx neuron dynamics | `stability_nan_rate`, `stability_divergence_rate` | Numerical stability and bounded membrane dynamics. |
| P0-2 Conductance synapses + NMDA Mg block | `physics_spike_rate_hz` | Synaptic drive produces bounded, measurable activity. |
| P0-3 Three-factor learning | `learning_weight_entropy`, `learning_convergence_error` | Weight distribution behavior and convergence to target. |
| P0-4 Criticality σ and gain control | `physics_sigma`, `physics_sigma_std` | σ tracking and stability around target. |
| P1-5 Temperature schedule + gating | `thermostat_temperature_mean`, `thermostat_temperature_exploration_corr` | Temperature dynamics and exploration coupling. |
| P2-8 Numerical methods (dt invariance) | `stability_nan_rate`, `stability_divergence_rate`, `physics_sigma` | Δt stability and invariance checks. |
| P2-9 Determinism protocol | `reproducibility_bitwise_delta` | Bitwise determinism of core state metrics. |
| P2-11 Reference network simulator | `performance_wall_time_sec`, `performance_peak_rss_mb`, `performance_neuron_steps_per_sec` | Scale viability and runtime footprint. |
| P2-12 Benchmark harness contract | `performance_wall_time_sec` (reporting), `reproducibility_bitwise_delta` | Benchmark harness integrity and deterministic outputs. |
