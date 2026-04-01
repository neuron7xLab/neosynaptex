# MFN Code Structure — MyceliumFractalNet v4.1

This document describes the code structure of MyceliumFractalNet, mapping
conceptual modules from the architecture documentation to actual Python
packages, modules, and public functions.

---

## 1. Layer Model Overview

MyceliumFractalNet follows a three-layer architecture:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL (api.py, CLI, Docker)                     │
├──────────────────────────────────────────────────────────────────────┤
│                    INTEGRATION (schemas, adapters)                    │
├──────────────────────────────────────────────────────────────────────┤
│                    CORE (pure math/dynamics)                          │
└──────────────────────────────────────────────────────────────────────┘
```

**Layer Boundaries:**
- **core/** — Pure mathematical/dynamical implementations. NO HTTP, FastAPI, uvicorn, or infrastructure dependencies.
- **integration/** — Schemas, adapters, service context. Bridges core to external world.
- **External** — API endpoints (api.py), CLI (mycelium_fractal_net_v4_1.py), Docker, k8s.

---

## 2. Conceptual Module → Code Mapping

| Conceptual Module | Description | Layer | Python Package/Module | Key Public Functions/Classes |
|-------------------|-------------|-------|----------------------|------------------------------|
| **Nernst-Planck** | Ion electrochemistry | core | `core/nernst.py` | `compute_nernst_potential()`, `MembraneEngine` |
| **Turing Morphogenesis** | Reaction-diffusion patterns | core | `core/turing.py` | `simulate_mycelium_field()`, `ReactionDiffusionEngine` |
| **Fractal Analysis** | Box-counting dimension, IFS | core | `core/fractal.py` | `estimate_fractal_dimension()`, `generate_fractal_ifs()`, `FractalGrowthEngine` |
| **STDP Plasticity** | Spike-timing dependent learning | core | `core/stdp.py` | `STDPPlasticity` |
| **Federated/Krum** | Byzantine-robust aggregation | core | `core/federated.py` | `HierarchicalKrumAggregator`, `aggregate_gradients_krum()` |
| **Stability/Lyapunov** | Dynamical stability metrics | core | `core/stability.py` | `compute_lyapunov_exponent()`, `compute_stability_metrics()` |
| **Neural Network** | MFN with fractal dynamics | model | `model.py` | `MyceliumFractalNet`, `SparseAttention` |
| **Validation** | Validation pipeline | model | `model.py` | `run_validation()`, `ValidationConfig` |
| **Feature Extraction** | 18 fractal features | analytics | `analytics/` | `compute_fractal_features()`, `FeatureVector` |
| **Data Pipelines** | Scenario-based data generation | pipelines | `pipelines/` | `run_scenario()`, `get_preset_config()`, `list_presets()` |
| **Request/Response Schemas** | API contracts | integration | `integration/schemas.py` | `ValidateRequest`, `SimulateResponse`, etc. |
| **Service Context** | Execution context | integration | `integration/service_context.py` | `ServiceContext`, `ExecutionMode` |
| **Adapters** | Core ↔ Integration bridge | integration | `integration/adapters.py` | `run_validation_adapter()`, etc. |
| **Authentication** | API key middleware | integration | `integration/auth.py` | `APIKeyMiddleware`, `require_api_key()` |
| **Rate Limiting** | Request rate control | integration | `integration/rate_limiter.py` | `RateLimitMiddleware`, `RateLimiter` |
| **Metrics** | Prometheus metrics | integration | `integration/metrics.py` | `MetricsMiddleware`, `metrics_endpoint()` |
| **Logging** | Structured JSON logging | integration | `integration/logging_config.py` | `setup_logging()`, `RequestLoggingMiddleware` |

---

## 3. Directory Structure

```
src/mycelium_fractal_net/
├── __init__.py              # Public package API
├── model.py                 # Neural network, validation, legacy functions
├── config.py                # Centralized configuration
│
├── core/                    # Pure mathematical engines (Layer 1)
│   ├── __init__.py          # Core API exports
│   ├── nernst.py            # Nernst-Planck electrochemistry
│   ├── turing.py            # Turing morphogenesis
│   ├── fractal.py           # Fractal dimension analysis
│   ├── stdp.py              # STDP plasticity
│   ├── federated.py         # Byzantine-robust aggregation
│   ├── stability.py         # Lyapunov stability metrics
│   ├── membrane_engine.py   # Membrane potential engine (impl)
│   ├── reaction_diffusion_engine.py  # R-D engine (impl)
│   ├── fractal_growth_engine.py      # Fractal engine (impl)
│   ├── engine.py            # Simulation orchestration
│   ├── field.py             # Field types
│   ├── types.py             # Type definitions
│   └── exceptions.py        # Domain exceptions
│
├── integration/             # Integration layer (Layer 2)
│   ├── __init__.py          # Integration API exports
│   ├── schemas.py           # Pydantic request/response models
│   ├── service_context.py   # Service context and execution modes
│   ├── adapters.py          # Core ↔ Integration adapters
│   ├── api_config.py        # API configuration management
│   ├── auth.py              # API key authentication middleware
│   ├── rate_limiter.py      # Rate limiting middleware
│   ├── metrics.py           # Prometheus metrics collection
│   └── logging_config.py    # Structured JSON logging
│
├── analytics/               # Feature extraction
│   ├── __init__.py
│   └── fractal_features.py  # 18 fractal features
│
├── experiments/             # Experiment utilities
├── numerics/                # Additional numerical utilities
└── pipelines/               # Data pipeline utilities
```

---

## 4. Public API Summary

### 4.1 Package-Level Imports (mycelium_fractal_net)

These are the primary imports shown in README:

```python
from mycelium_fractal_net import (
    # Core computation functions
    compute_nernst_potential,
    simulate_mycelium_field,
    estimate_fractal_dimension,
    generate_fractal_ifs,
    compute_lyapunov_exponent,
    
    # Federated learning
    aggregate_gradients_krum,
    HierarchicalKrumAggregator,
    
    # Neural network
    MyceliumFractalNet,
    STDPPlasticity,
    SparseAttention,
    
    # Validation
    run_validation,
    ValidationConfig,
    
    # Analytics
    FeatureVector,
    compute_fractal_features,
    
    # Pipelines (data generation)
    run_scenario,
    get_preset_config,
    list_presets,
    
    # Core engines (advanced use)
    MembraneEngine,
    ReactionDiffusionEngine,
    FractalGrowthEngine,
)
```

### 4.2 Domain-Specific Imports (core/*)

For more targeted imports:

```python
# Nernst electrochemistry
from mycelium_fractal_net.core.nernst import (
    compute_nernst_potential,
    MembraneConfig,
    MembraneEngine,
)

# Turing morphogenesis
from mycelium_fractal_net.core.turing import (
    simulate_mycelium_field,
    ReactionDiffusionConfig,
    ReactionDiffusionEngine,
    TURING_THRESHOLD,
)

# Fractal analysis
from mycelium_fractal_net.core.fractal import (
    estimate_fractal_dimension,
    generate_fractal_ifs,
    FractalConfig,
    FractalGrowthEngine,
)

# STDP plasticity
from mycelium_fractal_net.core.stdp import (
    STDPPlasticity,
    STDP_TAU_PLUS,
    STDP_A_PLUS,
)

# Federated learning
from mycelium_fractal_net.core.federated import (
    HierarchicalKrumAggregator,
    aggregate_gradients_krum,
)

# Stability analysis
from mycelium_fractal_net.core.stability import (
    compute_lyapunov_exponent,
    compute_stability_metrics,
    is_stable,
)
```

---

## 5. Layer Boundary Guarantees

### 5.1 What core/ Does NOT Import

The following packages are **prohibited** in `core/` modules:

- `fastapi`, `starlette`, `uvicorn` (web frameworks)
- `requests`, `httpx`, `aiohttp` (HTTP clients)
- `kafka`, `redis`, `celery` (message queues)
- `sqlalchemy`, `pymongo` (databases)
- Any infrastructure-specific packages

### 5.2 What core/ CAN Import

- `numpy`, `torch`, `sympy`, `scipy` (numerical computing)
- Python standard library (`math`, `dataclasses`, `typing`, etc.)
- Other `mycelium_fractal_net.core.*` modules
- `mycelium_fractal_net.model` (for backward compatibility re-exports)

### 5.3 Dependency Direction

```
core/ ← integration/ ← api.py/CLI
       (depends on)    (depends on)
```

- `core/` does NOT depend on `integration/`
- `integration/` CAN depend on `core/`
- `api.py` uses `integration/` for all request handling

---

## 6. Backward Compatibility

### 6.1 Re-Export Strategy

For backward compatibility, domain modules re-export original implementations:

```python
# core/nernst.py re-exports from model.py
from ..model import compute_nernst_potential

# core/turing.py re-exports from model.py
from ..model import simulate_mycelium_field
```

This ensures existing code continues to work:

```python
# Both work identically:
from mycelium_fractal_net import compute_nernst_potential
from mycelium_fractal_net.core.nernst import compute_nernst_potential
```

### 6.2 API Contract Stability

The following function signatures are **stable contracts**:

| Function | Signature (required params) |
|----------|----------------------------|
| `compute_nernst_potential` | `(z_valence, concentration_out_molar, concentration_in_molar)` |
| `simulate_mycelium_field` | `(rng, grid_size=64, steps=64, turing_enabled=True)` |
| `estimate_fractal_dimension` | `(binary_field)` |
| `aggregate_gradients_krum` | `(gradients)` |

---

## 7. Adding New Functionality

### 7.1 Adding to Core

1. Create module in `src/mycelium_fractal_net/core/`
2. Add exports to `core/__init__.py`
3. (Optional) Add package-level export in `__init__.py`
4. Add tests in `tests/`
5. Update this document

### 7.2 Adding New Integration

1. Add schemas to `integration/schemas.py`
2. Add adapter in `integration/adapters.py`
3. Update `integration/__init__.py` exports
4. Add endpoint in `api.py`
5. Add tests

### 7.3 Layer Boundary Tests

New modules are automatically tested for layer boundary compliance:
- `tests/test_layer_boundaries.py` — Verifies no infrastructure imports in core/
- `tests/test_public_api_structure.py` — Verifies public API consistency

---

## 8. References

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture (conceptual) |
| [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) | Mathematical formalization |
| [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md) | System role and boundaries |
| [NUMERICAL_CORE.md](NUMERICAL_CORE.md) | Core engine implementation guide |
| [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) | Feature extraction schema |

---

*Document Version: 1.0*  
*Last Updated: 2025*  
*Applies to: MyceliumFractalNet v4.1.0*
