# Changelog

All notable changes to the **neuron7x-agents** package.

## [1.0.0] - 2026-03-29

### Added
- **DNCA** (Distributed Neuromodulatory Cognitive Architecture) — full subsystem.
  - 6 neuromodulatory operators: DA, ACh, NE, 5-HT, GABA, Glu.
  - Lotka-Volterra winnerless competition field.
  - Kuramoto phase coupling with MetastabilityEngine.
  - Dominant-Acceptor Cycle (DAC) per operator with forward model learning.
  - SharedPredictiveState (SPS) — typed tensor workspace, INV-1 enforced.
  - RegimeManager with full lifecycle (FORMING -> ACTIVE -> SATURATING -> DISSOLVING).
  - BNSynGammaProbe — TDA-based gamma-scaling measurement (Theil-Sen + bootstrap CI).
  - NFI BN-Syn adapter for integration with NFI architecture.
  - 4 cognitive benchmarks: N-Back (A1), Stroop (A2), WCST (A3), Metastability (A4).
  - RegimeDiagnostics with ASCII plotting and JSON export.
  - Smoke test (`python -m neuron7x_agents.dnca.smoke_test`).
- All biological constants annotated with DOI references.
- Deterministic seeding (`seed` parameter) in `DNCABenchmarkSuite` and `BNSynGammaProbe`.

### Fixed
- WCST (A3) action readout: switched from arbitrary NMO-to-rule mapping to prediction-error-based readout.
  Enables actual rule learning and rule changes during the task.
- NFI bridge gamma probe window_size corrected from 30 to 50 for stable estimates.
- Gamma probe bootstrap reduced from 1000 to 500 for faster computation without CI degradation.

### Architecture
- NCE (Neurosymbolic Cognitive Engine) — predictive coding, abduction, reductio, epistemic foraging.
- SERO (Hormonal Vector Regulation) — Eq.3/4/6/7, Bayesian immune system.
- Kriterion (Epistemic Verification) — fail-closed gates, anti-gaming, evidence tiering.
- HybridAgent — NCE + SERO + Kriterion composed.
