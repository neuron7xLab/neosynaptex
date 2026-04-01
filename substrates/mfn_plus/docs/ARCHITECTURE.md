# Architecture

## System Overview

MyceliumFractalNet is a deterministic morphology-aware analytics engine. It simulates reaction-diffusion systems on a 2D lattice, extracts structural features, detects anomalies, forecasts evolution, compares states, and verifies causal consistency of every conclusion.

The architecture follows a strict layered design where each layer may only depend on layers below it.

## Layer Model

```
┌─────────────────────────────────────────────────────────┐
│  Interfaces                                             │
│  cli.py · api.py                                        │
│  User-facing surfaces. No domain logic.                 │
├─────────────────────────────────────────────────────────┤
│  Integration                                            │
│  integration/api_server.py · adapters · schemas · auth  │
│  HTTP serving, request validation, rate limiting.        │
├─────────────────────────────────────────────────────────┤
│  Pipelines                                              │
│  pipelines/report.py · scenarios/                       │
│  Orchestration of multi-stage workflows.                │
├─────────────────────────────────────────────────────────┤
│  Core                                                   │
│  core/simulate · extract · detect · forecast · compare  │
│  core/causal_validation · rule_registry                 │
│  Domain operations. Pure functions over typed data.      │
├─────────────────────────────────────────────────────────┤
│  Analytics                                              │
│  analytics/morphology · connectivity · temporal          │
│  Feature computation. Stateless transformations.         │
├─────────────────────────────────────────────────────────┤
│  Bio Extension                                          │
│  bio/physarum · anastomosis · fhn · chemotaxis ·        │
│  dispersal · morphospace · memory_anonymization ·       │
│  persuasion · levin_pipeline · compute_reserve          │
│  8 peer-reviewed mechanisms + Levin cognitive framework │
│  + adaptive compute reserve. 15 public symbols.         │
├─────────────────────────────────────────────────────────┤
│  Neurochem                                              │
│  neurochem/kinetics · mwc · state · profiles            │
│  Biophysical kinetics. No simulation ownership.          │
├─────────────────────────────────────────────────────────┤
│  Numerics                                               │
│  numerics/grid_ops · update_rules (compat only)         │
│  Low-level numerical operations. Laplacian, CFL, JIT.    │
├─────────────────────────────────────────────────────────┤
│  Security                                               │
│  security/input_validation · encryption · audit          │
│  Domain-independent. No core imports.                    │
├─────────────────────────────────────────────────────────┤
│  Types                                                  │
│  types/field · detection · forecast · features · causal │
│  Pure frozen dataclasses. Zero domain logic.             │
└─────────────────────────────────────────────────────────┘
```

## Boundary Policies

Eight import contracts are enforced by `import-linter` in CI and pre-commit:

| # | Contract | Policy |
|---|----------|--------|
| 1 | Core isolation | `core.simulate`, `core.detect`, etc. must not import `integration`, `api`, or `cli` |
| 2 | Pipeline transport | `pipelines` must not import `api` or `cli` |
| 3 | Interface crypto | `cli` and `api_server` must not import `crypto` directly |
| 4 | Numerics delegation | `numerics.update_rules` must not import `core.engine`, `core.simulate`, or `model` |
| 5 | Types purity | `types.*` (except `field.py`) must not import core operations or pipelines |
| 6 | Analytics isolation | `analytics` must not depend on `integration`, `api`, `cli`, or `pipelines` |
| 7 | Security isolation | `security` must not depend on `core`, `analytics`, `neurochem`, or `pipelines` |

Contract definitions: [`.importlinter`](../.importlinter)

## Canonical V1 Surface

The public API consists of six operations:

| Operation | Module | Input → Output |
|-----------|--------|---------------|
| `simulate` | `core.simulate` | `SimulationSpec → FieldSequence` |
| `extract` | `core.extract` | `FieldSequence → MorphologyDescriptor` |
| `detect` | `core.detect` | `FieldSequence → AnomalyEvent` |
| `forecast` | `core.forecast` | `FieldSequence × horizon → ForecastResult` |
| `compare` | `core.compare` | `FieldSequence × FieldSequence → ComparisonResult` |
| `report` | `core.report` | `FieldSequence × config → ArtifactManifest` |

**Semantic parity rule:** SDK, CLI, and API are orchestration layers over the same engine functions. The SDK is the semantic source of truth.

## Data Flow

```
SimulationSpec ──→ ReactionDiffusionEngine ──→ FieldSequence
                        │
                   NeuromodulationState
                   (optional, via neurochem/)
                        │
FieldSequence ──→ extract() ──→ MorphologyDescriptor
              ├──→ detect()  ──→ AnomalyEvent
              ├──→ forecast() ──→ ForecastResult
              ├──→ compare()  ──→ ComparisonResult
              │
              ▼
         CausalValidationGate
              │
         46 rules evaluated
              │
              ▼
         CausalValidationResult(decision, rules[], fingerprint)
              │
              ▼
         ArtifactManifest (JSON, HTML, signatures)
```

## Neuromodulation Contour

Neuromodulation is an opt-in extension that does not alter the baseline simulation path:

- **Owner:** `neurochem/` package (kinetics, MWC transforms, profile registry, calibration).
- **Integration:** `core/reaction_diffusion_engine.py` is the single canonical owner of the simulation step and calls into `neurochem/kinetics.py` during execution.
- **State machine order:** bind → unbind → desensitize → recover → local excitability offset.
- **Numerics boundary:** `numerics/update_rules.py` is compatibility-only numerical support and must not become a second equation-of-motion owner.
- **Baseline parity:** `SimulationSpec(neuromodulation=None)` produces identical results to v4.0.0.
- **Constraint:** No global resting-potential shift. Offset application is local and excitability-driven.

**Canonical profiles:**

| Profile | Description |
|---------|-------------|
| `baseline_nominal` | No modulation (control) |
| `gabaa_tonic_muscimol_alpha1beta3` | GABA-A tonic inhibition via muscimol |
| `gabaa_tonic_extrasynaptic_delta_high_affinity` | Extrasynaptic delta-subunit GABA-A |
| `serotonergic_reorganization_candidate` | 5-HT-driven plasticity reorganization |
| `balanced_criticality_candidate` | Near-critical dynamics with balanced modulation |
| `observation_noise_gaussian_temporal` | Gaussian temporal smoothing observation noise model |

## Frozen Surfaces

The following modules are frozen and not part of the v1 release contract:

| Module | Status | Migration |
|--------|--------|-----------|
| `crypto/` | Frozen, deprecated | Signing via `artifact_bundle.py`; removal in v5.0 |
| `core/federated.py` | Frozen | No active development |
| `integration/ws_*` | Frozen | WebSocket adapters not in v1 scope |
| `infra/` | Frozen | Deployment material, not library code |
| `docs/project-history/` | Archive | Historical documentation, not maintained |

## Configuration

| File | Purpose |
|------|---------|
| `configs/detection_thresholds_v1.json` | 62 named detection thresholds |
| `configs/causal_validation_v1.json` | Causal rule parameters and severity levels |
| `configs/crypto.yaml` | Ed25519 signing seed and key derivation |
| `configs/{small,medium,large,prod,staging,dev}.json` | Environment-specific simulation presets |
| `benchmarks/bio_baseline.json` | Performance baseline for regression detection |

## Decision Records

Significant architectural decisions are documented as ADRs in `docs/adr/`:

| ADR | Decision |
|-----|----------|
| [0001](adr/0001-dependency-model.md) | Dependency model: core has zero optional deps |
| [0002](adr/0002-architecture-boundaries.md) | Architecture boundaries enforced by import-linter |
| [0003](adr/0003-public-api-policy.md) | Public API policy: 6 canonical operations, frozen surface |
| [0004](adr/0004-reproducibility-policy.md) | Reproducibility: deterministic seeds, SHA256 fingerprints |
| [0005](adr/0005-release-policy.md) | Release policy: semver, signed artifacts, evidence packs |
| [0006](adr/0006-causal-validation-gate.md) | Causal validation gate design and failure semantics |
