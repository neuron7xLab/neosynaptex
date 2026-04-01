# Public API Contract

## Surface Classification

Every exported symbol has exactly one status:

| Status | Meaning | Compatibility guarantee |
|--------|---------|------------------------|
| **stable** | Supported, tested, documented | Semantic versioning — breaking changes require major version bump |
| **deprecated** | Scheduled for removal | Warning emitted on use, removed in next major version |
| **frozen** | No further development | Available but not enhanced, may be removed in v5.0 |
| **internal** | Implementation detail | No compatibility guarantee, may change without notice |

## Stable SDK Surface

The canonical Python API exported from `import mycelium_fractal_net as mfn`:

### Core Operations

| Symbol | Type | Since |
|--------|------|-------|
| `mfn.simulate(spec)` | Function | v4.0.0 |
| `mfn.SimulationSpec` | Dataclass | v4.0.0 |
| `mfn.FieldSequence` | Dataclass | v4.0.0 |

### Fluent API (from FieldSequence)

| Method | Returns | Since |
|--------|---------|-------|
| `seq.extract()` | `MorphologyDescriptor` | v4.1.0 |
| `seq.detect()` | `AnomalyEvent` | v4.1.0 |
| `seq.forecast(horizon)` | `ForecastResult` | v4.1.0 |
| `seq.compare(other)` | `ComparisonResult` | v4.1.0 |
| `seq.explain()` | `Explanation` | v4.1.0 |

### Neuromodulation Types

| Symbol | Type | Since |
|--------|------|-------|
| `mfn.NeuromodulationSpec` | Dataclass | v4.1.0 |
| `mfn.GABAATonicSpec` | Dataclass | v4.1.0 |
| `mfn.SerotonergicPlasticitySpec` | Dataclass | v4.1.0 |
| `mfn.ObservationNoiseSpec` | Dataclass | v4.1.0 |

### Result Types

| Symbol | Module | Since |
|--------|--------|-------|
| `MorphologyDescriptor` | `types.features` | v4.0.0 |
| `AnomalyEvent` | `types.detection` | v4.0.0 |
| `ForecastResult` | `types.forecast` | v4.0.0 |
| `ComparisonResult` | `types.forecast` | v4.0.0 |
| `CausalValidationResult` | `types.causal` | v4.1.0 |

### Legacy Exports (stable, historical)

| Symbol | Type | Since |
|--------|------|-------|
| `mfn.simulate_mycelium_field` | Function | v1.0.0 |
| `mfn.estimate_fractal_dimension` | Function | v1.0.0 |
| `mfn.compute_nernst_potential` | Function | v1.0.0 |

## Stable CLI Surface

| Command | Since |
|---------|-------|
| `mfn simulate` | v4.0.0 |
| `mfn detect` | v4.1.0 |
| `mfn extract` | v4.1.0 |
| `mfn forecast` | v4.1.0 |
| `mfn compare` | v4.1.0 |
| `mfn report` | v4.1.0 |
| `mfn api` | v4.0.0 |
| `mfn doctor` | v4.1.0 |
| `mfn info` | v4.1.0 |
| `mfn verify-bundle` | v4.1.0 |

## Stable REST API Surface

| Endpoint | Method | Since |
|----------|--------|-------|
| `/health` | GET | v4.0.0 |
| `/metrics` | GET | v4.0.0 |
| `/v1/simulate` | POST | v4.0.0 |
| `/v1/extract` | POST | v4.1.0 |
| `/v1/detect` | POST | v4.1.0 |
| `/v1/forecast` | POST | v4.1.0 |
| `/v1/compare` | POST | v4.1.0 |
| `/v1/report` | POST | v4.1.0 |

Contract source of truth: `docs/contracts/openapi.v2.json`

## Deprecated Surfaces

| Symbol/Module | Deprecated in | Removal in | Alternative |
|--------------|---------------|------------|-------------|
| `from api import app` | v4.1.0 | v5.0.0 | `from mycelium_fractal_net.api import app` |
| `from analytics import ...` | v4.1.0 | v5.0.0 | `from mycelium_fractal_net.analytics.legacy_features import ...` |
| `from experiments import ...` | v4.1.0 | v5.0.0 | `from mycelium_fractal_net.experiments.generate_dataset import ...` |

## Frozen Surfaces

| Module | Frozen in | Notes |
|--------|-----------|-------|
| `crypto/` | v4.1.0 | Signing via `artifact_bundle.py`. Removal in v5.0. |
| `core/federated.py` | v4.0.0 | No active development. |
| `core/stdp.py` | v4.0.0 | STDP plasticity model frozen. |
| `core/turing.py` | v4.0.0 | Turing analysis frozen. |
| `integration/ws_*` | v4.0.0 | WebSocket adapters not in v1 scope. |
| `model.MyceliumFractalNet` | v4.1.0 | ML model surface, requires `[ml]`. |

## Internal (No Guarantee)

Everything not listed above is internal. Key examples:
- `core.detection_config` — config loader internals
- `core.reaction_diffusion_config` — engine parameter types
- `core.reaction_diffusion_compat` — legacy numerics shims
- `analytics.insight_architect` — explanation generation internals
- `numerics.*` — low-level numerical operations
- `security.*` — input validation internals

## Versioning Policy

- **Patch** (4.1.x): Bug fixes, documentation, performance improvements. No public API changes.
- **Minor** (4.x.0): New features, new stable exports. Backward-compatible.
- **Major** (x.0.0): Breaking changes to stable API. Deprecated symbols removed.
