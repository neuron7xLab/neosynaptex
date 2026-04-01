# Data Model

## Core Types

All domain types are frozen dataclasses in `src/mycelium_fractal_net/types/`.

### Pipeline Types

| Type | Module | Description |
|------|--------|-------------|
| `SimulationSpec` | `types.field` | Simulation parameters: grid size, steps, seed, alpha, neuromodulation |
| `FieldSequence` | `types.field` | Simulation result: 2D field array, metadata, fluent API methods |
| `MorphologyDescriptor` | `types.features` | 57-dimensional embedding across 6 active feature groups |
| `AnomalyEvent` | `types.detection` | Detection result: label, score, confidence, regime, evidence |
| `ForecastResult` | `types.forecast` | Predicted states, uncertainty envelope, accuracy metrics |
| `ComparisonResult` | `types.analytics` | Distance, cosine similarity, topology drift label |
| `AnalysisReport` | `types.analytics` | Full pipeline report with artifact manifest |

### Causal Types

| Type | Module | Description |
|------|--------|-------------|
| `CausalRuleSpec` | `types.causal` | Rule metadata: claim, math, reference, falsifiability |
| `CausalRuleResult` | `types.causal` | Individual rule evaluation: passed, observed, expected |
| `CausalValidationResult` | `types.causal` | Gate decision: pass/degraded/fail, all rule results |
| `CausalSeverity` | `types.causal` | Enum: FATAL, ERROR, WARN, INFO |

### Neuromodulation Types

| Type | Module | Description |
|------|--------|-------------|
| `NeuromodulationSpec` | `types.field` | Neuromodulation configuration: profile_id, evidence_version, profile, GABA-A, serotonergic |
| `GABAATonicSpec` | `types.field` | GABA-A tonic inhibition parameters |
| `SerotonergicPlasticitySpec` | `types.field` | Serotonergic plasticity parameters |
| `ObservationNoiseSpec` | `types.field` | Observation noise model parameters |
| `NeuromodulationStateSnapshot` | `types.field` | Runtime state: occupancy, inhibition, gain, plasticity |

### Engine Types

| Type | Module | Description |
|------|--------|-------------|
| `ReactionDiffusionConfig` | `core.reaction_diffusion_config` | Engine parameters: diffusion coefficients, boundaries |
| `ReactionDiffusionMetrics` | `core.reaction_diffusion_config` | Engine metrics: field statistics, stability events |
| `SimulationMetrics` | `types.field` | Typed simulation metadata for pipeline consumption |

## Contract Guarantees

- **Schema versioning:** All serializable types carry an explicit `schema_version` field.
- **Deterministic normalization:** Field arrays are always `float64`. No implicit dtype promotion.
- **Round-trip serialization:** All types support `to_dict()` / `from_dict()` with full fidelity.
- **JSON safety:** Summary representations are JSON-serializable (no numpy arrays in public surfaces).
- **Binary persistence:** Large arrays stored as `.npy` artifacts, referenced by SHA256 hash.
- **Provenance fields:** Report manifests include `engine_version`, `schema_version`, `seed`, `config_hash`, `git_sha`, `lock_hash`.

## Feature Groups

The `MorphologyDescriptor` produces a 57-dimensional embedding from 6 active feature groups (42 scalar keys, expanded to 57 via derived dimensions):

| Group | Features | Examples |
|-------|----------|---------|
| Fractal | 3 | `D_box`, `lacunarity`, `multifractal_width` |
| Stability | 5 | `instability_index`, `near_transition_score`, `stability_margin` |
| Complexity | 6 | `entropy`, `spatial_complexity`, `gradient_energy` |
| Connectivity | 8 | `connectivity_divergence`, `hierarchy_flattening`, `modularity_proxy` |
| Temporal | 6 | `temporal_drift`, `autocorrelation_decay`, `spectral_centroid` |
| Cluster | 5 | `N_clusters`, `max_cluster_size`, `cluster_size_std` |
| Spatial | 4 | `V_mean`, `V_std`, `f_active`, `spatial_coherence` |

## Validation

Type contracts are verified by:
- `tests/test_schema_roundtrip_completion.py` — serialization round-trip
- `tests/test_public_api_structure.py` — public API surface stability
- `docs/contracts/openapi.v2.json` — REST API schema
