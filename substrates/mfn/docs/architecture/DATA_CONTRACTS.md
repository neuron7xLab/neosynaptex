# Data Contracts — MFN v0.1.0

## Canonical Types (single source of truth)

| Contract | Location | Frozen | Purpose |
|----------|----------|--------|---------|
| FieldSequence | types/field.py | Yes | Complete simulation snapshot |
| SimulationSpec | types/field.py | Yes | Simulation parameters |
| MorphologyDescriptor | types/features.py | Yes | 57-dim feature vector |
| AnomalyEvent | types/detection.py | Yes | Anomaly detection result |
| DiagnosisReport | types/diagnosis.py | Yes | Full diagnostic output |
| CausalValidationResult | types/causal.py | Yes | 46-rule validation |
| ForecastResult | types/forecast.py | Yes | Next-step prediction |
| ThermodynamicStabilityReport | types/thermodynamics.py | Yes | F, lambda1, gate |
| FractalScaleReport | types/scale.py | Yes | D_box preservation |
| GNCState | neurochem/gnc.py | No | Neuromodulatory state |
| NormSpace | tau_control/types.py | Yes | Identity norm ellipsoid |
| MetaRuleSpace | tau_control/types.py | Yes | Meta-rules for adaptation |
| TauState | tau_control/types.py | Yes | tau-control snapshot |
| DiscriminantResult | tau_control/discriminant.py | Yes | Structured pressure result |
| FeatureVector (interp) | interpretability/feature_extractor.py | No | 4-group feature dict |
| SelfModelSnapshot | self_reading/self_model.py | Yes | Per-step self-model |
| CoherenceReport | self_reading/coherence_monitor.py | Yes | System integrity |
| PhaseReport | self_reading/phase_validator.py | Yes | Phase classification |

## Signal Lineage

```
F (free energy)     ← FreeEnergyTracker.total_energy() → ThermodynamicStabilityReport
lambda1 (Lyapunov)  ← LyapunovAnalyzer.leading_lyapunov_exponent() → Report
D_box (fractal)     ← compute_box_counting_dimension() → MorphologyDescriptor
betti (topology)    ← PersistenceTransformer.transform() → persistence diagram
gamma (scaling)     ← gamma_diagnostic() OR _compute_gamma() → diagnostic string/dict
phase               ← PhaseValidator.validate() → PhaseReport
coherence           ← CoherenceMonitor.measure() → CoherenceReport
Phi_t (collapse)    ← CollapseTracker.record() → float
tau(t)              ← TauController.update() → float
V_total             ← LyapunovMonitor.compute() → LyapunovState
```

## Known Duplications

| Name | Count | Status |
|------|-------|--------|
| FeatureVector | 3 | Different semantics — legacy/fractal/interpretability |
| BoundaryCondition | 3 | types/field.py is canonical; others are legacy |
| ScenarioConfig | 2 | Different schemas — experiments vs pipelines |
