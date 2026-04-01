# MFN Integration Specification

**Document Version**: 1.1  
**Target Version**: MyceliumFractalNet v4.1.0  
**Status**: PR-1 (Integration Specification & Package Scaffold)  
**Last Updated**: 2025-11-29

---

## 1. Current Repository Layout

### 1.1 Code Root

```text
mycelium-fractal-net/                    # Repository root
├── src/
│   └── mycelium_fractal_net/            # Main installable package (src-layout)
│       ├── __init__.py                  # Public API exports (35+ symbols)
│       ├── model.py                     # Core algorithms (~1000 LOC)
│       └── core/                        # Numerical engine subpackage
│           ├── __init__.py
│           ├── exceptions.py
│           ├── membrane_engine.py
│           ├── reaction_diffusion_engine.py
│           └── fractal_growth_engine.py
├── analytics/                           # Feature extraction package (top-level)
│   ├── __init__.py
│   └── fractal_features.py
├── experiments/                         # Dataset generation package (top-level)
│   ├── __init__.py
│   ├── generate_dataset.py
│   └── inspect_features.py
├── api.py                               # FastAPI REST server
├── mycelium_fractal_net_v4_1.py         # CLI entry point
├── Dockerfile                           # Container build
└── k8s.yaml                             # Kubernetes deployment manifest
```

### 1.2 Test Layout

```text
tests/
├── core/                                # Numerical engine unit tests
│   ├── __init__.py
│   ├── test_membrane_engine.py
│   ├── test_reaction_diffusion_engine.py
│   └── test_fractal_growth_engine.py
├── test_analytics/                      # Analytics module tests
│   ├── __init__.py
│   └── test_fractal_features.py
├── integration/                         # Package-level smoke tests (NEW in PR-1)
│   ├── __init__.py
│   └── test_imports.py
├── test_biophysics_core.py              # Biophysics validation tests
├── test_determinism.py                  # Reproducibility tests
├── test_federated.py                    # Federated learning tests
├── test_fractal_dimension.py            # Box-counting tests
├── test_lyapunov.py                     # Stability analysis tests
├── test_math_model_validation.py        # Mathematical model verification
├── test_model.py                        # Neural network tests
├── test_morphogenesis.py                # Turing pattern tests
├── test_nernst.py                       # Nernst equation tests
├── test_physics.py                      # Physical constants validation
├── test_sparse_attention.py             # Attention mechanism tests
├── test_stdp.py                         # STDP plasticity tests
├── test_training_integration.py         # End-to-end training tests
└── test_validation_cycle.py             # Validation pipeline tests
```

### 1.3 Docs Layout

```text
docs/
├── ARCHITECTURE.md                      # System architecture overview
├── FEATURE_SCHEMA.md                    # 18-feature extraction schema
├── MFN_MATH_MODEL.md                        # Mathematical formalization (PDEs, Nernst)
├── MFN_INTEGRATION_SPEC.md              # This document (NEW in PR-1)
├── NUMERICAL_CORE.md                    # Numerical stability and discretization
├── ROADMAP.md                           # Development roadmap
└── VALIDATION_NOTES.md                  # Validation methodology
```

### 1.4 Tooling

| Tool | Config Location | Purpose | Settings |
|------|-----------------|---------|----------|
| **ruff** | `pyproject.toml [tool.ruff]` | Linting | rules: E, F, I; line-length: 100 |
| **mypy** | `pyproject.toml [tool.mypy]` | Type checking | strict=true, python_version=3.10 |
| **black** | `pyproject.toml [tool.ruff]` | Formatting | line-length: 100 |
| **isort** | via ruff | Import sorting | I rule enabled |
| **pytest** | `pyproject.toml [tool.pytest]` | Testing | testpaths=["tests"], pythonpath=["."] |
| **CI** | `.github/workflows/ci.yml` | GitHub Actions | lint, test (3.10-3.12), validate, benchmark, scientific-validation |

---

## 2. MyceliumFractalNet Source Layout (PRODUCTION)

### 2.1 Complete File Tree

```text
mycelium-fractal-net/
│
├── src/mycelium_fractal_net/            # [CORE] Main package
│   ├── __init__.py                      # Public API: 35+ exports
│   ├── model.py                         # Core implementation
│   │   ├── compute_nernst_potential()   # Nernst equation solver
│   │   ├── simulate_mycelium_field()    # Field simulation with Turing morphogenesis
│   │   ├── estimate_fractal_dimension() # Box-counting dimension
│   │   ├── generate_fractal_ifs()       # IFS fractal generation
│   │   ├── compute_lyapunov_exponent()  # Stability analysis
│   │   ├── STDPPlasticity               # Spike-timing dependent plasticity
│   │   ├── SparseAttention              # Top-k sparse attention
│   │   ├── HierarchicalKrumAggregator   # Byzantine-robust aggregation
│   │   ├── MyceliumFractalNet           # Neural network model
│   │   ├── ValidationConfig             # Configuration dataclass
│   │   └── run_validation()             # Validation pipeline
│   └── core/                            # [NUMERICS] Numerical engines
│       ├── __init__.py                  # Engine exports
│       ├── exceptions.py                # StabilityError, ValueOutOfRangeError, NumericalInstabilityError
│       ├── membrane_engine.py           # MembraneEngine: Nernst/GHK ODE integration
│       ├── reaction_diffusion_engine.py # ReactionDiffusionEngine: Turing PDE solver
│       └── fractal_growth_engine.py     # FractalGrowthEngine: IFS/DLA with Lyapunov
│
├── analytics/                           # [ANALYTICS] Feature extraction
│   ├── __init__.py                      # Exports: FeatureConfig, FeatureVector, compute_features, etc.
│   └── fractal_features.py              # 18 fractal/statistical features
│       ├── FeatureConfig                # Configuration for feature extraction
│       ├── FeatureVector                # Dataclass with D_box, V_mean, etc.
│       ├── compute_features()           # Main entry point
│       ├── compute_fractal_features()   # Box-counting dimension
│       ├── compute_basic_stats()        # V_min, V_max, V_mean, V_std, skew, kurt
│       ├── compute_temporal_features()  # dV_mean, dV_max, T_stable, E_trend
│       └── compute_structural_features()# f_active, N_clusters, cluster stats
│
├── experiments/                         # [EXPERIMENTS] Dataset generation
│   ├── __init__.py                      # Exports: generate_dataset, SweepConfig, etc.
│   ├── generate_dataset.py              # Parameter sweep pipeline → parquet output
│   └── inspect_features.py              # Exploratory analysis utilities
│
├── configs/                             # [CONFIG] Simulation configurations
│   ├── small.json                       # Dev: grid=32, steps=32
│   ├── medium.json                      # Test: grid=64, steps=64
│   └── large.json                       # Prod: grid=128, steps=128
│
├── benchmarks/                          # [BENCHMARK] Performance testing
│   └── benchmark_core.py                # Core engine benchmarks
│
├── validation/                          # [VALIDATION] Scientific validation
│   └── scientific_validation.py         # Physics/math validation script
│
├── examples/                            # [EXAMPLES] Application demos
│   ├── finance_regime_detection.py      # Financial regime detection
│   └── rl_exploration.py                # Reinforcement learning exploration
│
├── assets/                              # [ASSETS] Visual assets
│   ├── header.svg                       # README header
│   ├── morphogenesis.gif                # Turing pattern animation
│   ├── node_dynamics.png                # Node dynamics visualization
│   └── fractal_topology.png             # Fractal topology diagram
│
├── data/                                # [DATA] Generated datasets (gitignored)
│
├── tests/                               # [TESTS] Test suite (see Section 1.2)
│
├── docs/                                # [DOCS] Documentation (see Section 1.3)
│
├── .github/workflows/ci.yml             # [CI] GitHub Actions pipeline
├── pyproject.toml                       # [BUILD] Package configuration
├── requirements.txt                     # [DEPS] Runtime + API dependencies
├── Dockerfile                           # [DEPLOY] Container build
├── k8s.yaml                             # [DEPLOY] Kubernetes manifest
├── api.py                               # [API] FastAPI server
├── mycelium_fractal_net_v4_1.py         # [CLI] Command-line interface
└── README.md                            # Project documentation
```

### 2.2 Module Responsibilities

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Core Package** | `src/mycelium_fractal_net/` | Public API, main algorithms, numerical engines |
| **Numerics** | `src/mycelium_fractal_net/core/` | Stable PDE/ODE solvers, stability-guaranteed engines |
| **Analytics** | `analytics/` | Feature extraction (18 features), statistical analysis |
| **Experiments** | `experiments/` | Dataset generation, parameter sweeps, reproducible pipelines |
| **Configs** | `configs/` | Predefined simulation configurations (small/medium/large) |
| **Benchmarks** | `benchmarks/` | Performance measurement and profiling |
| **Validation** | `validation/` | Scientific validation against known physics |
| **Examples** | `examples/` | Application demonstrations (finance, RL) |

---

## 3. Target Integration Layout (inside main repo)

The repository structure is already production-ready. No major restructuring is required.
The target integration maintains the existing layout with additions for integration testing.

```text
src/mycelium_fractal_net/                # Main package (EXISTING)
├── __init__.py                          # Public API exports
│   └── Purpose: Single entry point for all public symbols (35+)
├── model.py                             # Core implementation
│   └── Purpose: Simulation, Nernst, fractal analysis, NN, federated learning
└── core/                                # Numerical engines
    ├── __init__.py                      # Engine exports
    ├── exceptions.py                    # Custom exceptions for stability/range errors
    ├── membrane_engine.py               # Nernst/GHK membrane potential solver
    ├── reaction_diffusion_engine.py     # Turing morphogenesis PDE solver
    └── fractal_growth_engine.py         # IFS fractal generation with Lyapunov

analytics/                               # Feature extraction (EXISTING)
├── __init__.py                          # Module exports
│   └── Purpose: Expose FeatureConfig, FeatureVector, compute_features()
└── fractal_features.py                  # 18-feature extraction pipeline
    └── Purpose: Extract D_box, V_stats, temporal features, structural features

experiments/                             # Dataset generation (EXISTING)
├── __init__.py                          # Module exports
│   └── Purpose: Expose generate_dataset(), SweepConfig
├── generate_dataset.py                  # Sweep pipeline
│   └── Purpose: Parallel parameter sweeps → parquet datasets
└── inspect_features.py                  # Analysis utilities
    └── Purpose: Dataset inspection and descriptive statistics

tests/integration/                       # Integration tests (NEW in PR-1)
├── __init__.py                          # Test package marker
└── test_imports.py                      # Smoke tests for package imports
    └── Purpose: Verify all public API symbols are importable

docs/                                    # Documentation
├── MFN_INTEGRATION_SPEC.md              # This specification (NEW in PR-1)
│   └── Purpose: Integration plan, API spec, 7-PR roadmap
└── (existing docs)                      # ARCHITECTURE, MATH_MODEL, NUMERICAL_CORE, etc.
```

---

## 4. Public API (v0, minimal)

### 4.1 Primary Entry Points

#### `simulate_mycelium_field`

```python
def simulate_mycelium_field(
    rng: np.random.Generator,
    grid_size: int = 64,
    steps: int = 64,
    alpha: float = 0.18,
    spike_probability: float = 0.25,
    turing_enabled: bool = True,
    turing_threshold: float = 0.75,
    quantum_jitter: bool = False,
    jitter_var: float = 0.0005,
) -> tuple[NDArray[np.float64], int]:
```

**Purpose**: Simulate 2D mycelium-like potential field with reaction-diffusion dynamics.

**Returns**: `(field, growth_events)` — Final field in Volts (N×N), count of growth events.

---

#### `compute_nernst_potential`

```python
def compute_nernst_potential(
    z_valence: int,
    concentration_out_molar: float,
    concentration_in_molar: float,
    temperature_k: float = 310.0,
) -> float:
```

**Purpose**: Compute membrane equilibrium potential using Nernst equation.

**Returns**: Membrane potential in Volts. For K⁺ (z=1, out=5mM, in=140mM): ≈ -0.089 V.

---

#### `estimate_fractal_dimension`

```python
def estimate_fractal_dimension(
    binary_field: NDArray[np.bool_],
    min_box_size: int = 2,
    max_box_size: int | None = None,
    num_scales: int = 5,
) -> float:
```

**Purpose**: Estimate box-counting fractal dimension of binary pattern.

**Returns**: Dimension D ∈ [0, 2]. Biological mycelium patterns: D ∈ [1.4, 1.9].

---

#### `compute_features` (from analytics)

```python
def compute_features(
    field_snapshots: NDArray[np.floating],
    config: FeatureConfig | None = None,
) -> FeatureVector:
```

**Purpose**: Extract all 18 features from field history.

**Returns**: `FeatureVector` dataclass with D_box, V_mean, dV_max, f_active, etc.

---

### 4.2 Core Classes

#### `MyceliumFractalNet`

```python
class MyceliumFractalNet(nn.Module):
    def __init__(
        self,
        input_dim: int = 4,
        hidden_dim: int = 32,
        use_sparse_attention: bool = True,
        use_stdp: bool = True,
    ) -> None: ...

    def forward(self, x: torch.Tensor) -> torch.Tensor: ...
    def train_step(self, x, y, optimizer, loss_fn) -> float: ...
```

**Purpose**: Neural network with fractal dynamics, STDP plasticity, sparse attention.

**Architecture**: Input(4) → Linear → ReLU → SparseAttention(topk=4) → Linear → ReLU → Linear → Output(1)

---

#### `HierarchicalKrumAggregator`

```python
class HierarchicalKrumAggregator:
    def __init__(
        self,
        num_clusters: int = 100,
        byzantine_fraction: float = 0.2,
        sample_fraction: float = 0.1,
    ) -> None: ...

    def aggregate(
        self,
        client_gradients: list[torch.Tensor],
        rng: np.random.Generator | None = None,
    ) -> torch.Tensor: ...
```

**Purpose**: Byzantine-robust federated learning aggregator (Krum + median).

**Scale**: Validated at 1M simulated clients, 20% Byzantine tolerance.

---

#### `FeatureVector` (from analytics)

```python
@dataclass
class FeatureVector:
    D_box: float       # Box-counting fractal dimension
    D_r2: float        # Regression R² quality
    V_min: float       # Minimum potential (mV)
    V_max: float       # Maximum potential (mV)
    V_mean: float      # Mean potential (mV)
    V_std: float       # Potential std deviation (mV)
    V_skew: float      # Skewness
    V_kurt: float      # Excess kurtosis
    dV_mean: float     # Mean rate of change (mV/step)
    dV_max: float      # Max rate of change (mV/step)
    T_stable: int      # Steps to quasi-stationary
    E_trend: float     # Energy trend slope
    f_active: float    # Active fraction
    N_clusters_low: int   # Cluster count at -60mV
    N_clusters_med: int   # Cluster count at -50mV
    N_clusters_high: int  # Cluster count at -40mV
    max_cluster_size: int # Largest cluster size
    cluster_size_std: float  # Cluster size std

    def to_array(self) -> NDArray[np.float64]: ...
    def to_dict(self) -> dict[str, float]: ...
```

**Purpose**: Structured container for all 18 extracted features.

---

### 4.3 Numerical Engines

| Engine | Config | Metrics | Purpose |
|--------|--------|---------|---------|
| `MembraneEngine` | `MembraneConfig` | `MembraneMetrics` | Nernst/GHK ODE integration |
| `ReactionDiffusionEngine` | `ReactionDiffusionConfig` | `ReactionDiffusionMetrics` | Turing PDEs with CFL stability |
| `FractalGrowthEngine` | `FractalConfig` | `FractalMetrics` | IFS generation with Lyapunov tracking |

---

## 5. Dependencies and Resource Constraints

### 5.1 Required Dependencies

| Package | Version | In Project | Purpose |
|---------|---------|------------|---------|
| numpy | ≥1.24 | ✓ pyproject.toml | Numerical arrays, Laplacian, statistics |
| torch | ≥2.0.0 | ✓ pyproject.toml | Neural network, STDP, sparse attention |
| sympy | ≥1.12 | ✓ pyproject.toml | Symbolic Nernst verification |

### 5.2 Optional Dependencies

| Package | Version | In Project | Purpose |
|---------|---------|------------|---------|
| fastapi | ≥0.109.0 | ✓ requirements.txt | REST API server |
| uvicorn | ≥0.27.0 | ✓ requirements.txt | ASGI server |
| pydantic | ≥2.0.0 | ✓ requirements.txt | Request/response validation |
| hypothesis | (optional) | CI only | Property-based testing |
| scipy | (optional) | CI only | Scientific utilities |

### 5.3 Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | ≥7.0 | Test runner |
| pytest-cov | ≥4.0 | Coverage reporting |
| ruff | ≥0.5.0 | Linting |
| mypy | ≥1.8.0 | Type checking (strict) |
| black | ≥24.0.0 | Code formatting |
| isort | ≥5.12.0 | Import sorting |

### 5.4 Resource Constraints

#### Memory Complexity

| Operation | Space | Notes |
|-----------|-------|-------|
| Field simulation | O(N²) | N = grid size, stores 2D arrays |
| Turing activator/inhibitor | O(2 × N²) | Two separate fields |
| Feature extraction | O(N² + T) | Field + temporal history |
| IFS generation | O(n_points) | Point cloud storage |
| Krum aggregation | O(n × d) | n clients, d gradient dim |

#### Time Complexity

| Operation | Time | Notes |
|-----------|------|-------|
| Nernst potential | O(1) | Single log computation |
| Field step | O(N²) | Laplacian via np.roll |
| Full simulation | O(N² × T) | T steps, each O(N²) |
| Box-counting | O(N² × k) | k scales |
| Krum selection | O(n² × d) | Pairwise distances |

#### Demo Configuration Estimates

| Config | Grid | Steps | Time | RAM |
|--------|------|-------|------|-----|
| small.json | 32×32 | 32 | ~0.1s | ~10 MB |
| medium.json | 64×64 | 64 | ~0.5s | ~50 MB |
| large.json | 128×128 | 128 | ~2s | ~200 MB |

---

## 6. Integration Roadmap (7 PRs)

### PR-1: Integration Specification & Package Scaffold

**Technical Result**:
- `docs/MFN_INTEGRATION_SPEC.md` created with complete structure analysis, API specification, and 7-PR roadmap.
- `tests/integration/test_imports.py` validates all 35+ public exports are importable.
- No code migration; documentation and smoke tests only.

**Verification**: `pytest tests/integration/test_imports.py -v`

---

### PR-2: Core Simulation Transfer

**Technical Result**:
- Integration tests for `simulate_mycelium_field()` covering grid sizes 32-128, Turing on/off, quantum jitter variants.
- Integration tests for `compute_nernst_potential()` validating K⁺, Na⁺, Ca²⁺, Cl⁻ at physiological concentrations.
- Type annotations verified via `mypy --strict` on all public functions.

**Acceptance Criteria**: E_K ≈ -89 mV ± 2 mV, deterministic output with fixed seed.

---

### PR-3: Numerical Schemes Formalization

**Technical Result**:
- Stability tests proving CFL condition (α ≤ 0.25) prevents divergence.
- Boundary condition tests confirming periodic wrapping via `np.roll`.
- Benchmarks measuring time complexity O(N² × T) for grid sizes 32-256.
- No NaN/Inf after 1000+ steps verified.

**Acceptance Criteria**: Turing patterns form reproducibly (bit-identical with fixed seed).

---

### PR-4: Fractal Analytics & Feature Engineering

**Technical Result**:
- Integration tests for all 18 features in `FeatureVector`.
- Box-counting dimension validated: D ∈ [1.4, 1.9] for biological patterns, R² > 0.9.
- Edge case handling: uniform fields → D = 0, no NaN.

**Acceptance Criteria**: `compute_features()` completes without error for all grid sizes.

---

### PR-5: Experimental Dataset Generation

**Technical Result**:
- `experiments/generate_dataset.py` produces valid parquet files with schema matching `FeatureVector`.
- Parameter sweep tests covering α ∈ [0.1, 0.2], grid ∈ [32, 64, 128].
- Reproducibility test: identical output with fixed seed across runs.

**Acceptance Criteria**: Parquet contains all 18 features, no missing values.

---

### PR-6: System Integration

**Technical Result**:
- API tests for `/health`, `/validate`, `/simulate`, `/nernst`, `/federated/aggregate` endpoints.
- CLI test: `python mycelium_fractal_net_v4_1.py --mode validate --seed 42 --epochs 1` passes.
- Docker build test: `docker build -t mfn:test .` succeeds, container runs validation.

**Acceptance Criteria**: All endpoints return HTTP 200 with valid JSON.

---

### PR-7: Optimization, Profiling & Finalization

**Technical Result**:
- Performance profile identifying hotspots (expected: Laplacian computation).
- Memory profiling confirming no leaks in 100-iteration loop.
- Load test: federated aggregation handles 10K simulated clients.
- Final documentation review ensuring all PRs reflected in docs.

**Acceptance Criteria**: Medium config completes in <1s; all CI checks pass.

---

## 7. Verification Commands

```bash
# Smoke test (PR-1)
pytest tests/integration/test_imports.py -v

# Full test suite
pytest -q

# Linting
ruff check .
mypy src/mycelium_fractal_net

# CLI validation
python mycelium_fractal_net_v4_1.py --mode validate --seed 42 --epochs 1

# Benchmarks
python benchmarks/benchmark_core.py

# Scientific validation
python validation/scientific_validation.py
```

---

## 8. References

| Document | Path | Description |
|----------|------|-------------|
| Architecture | [docs/ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, module interactions |
| Math Model | [docs/MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) | PDEs, Nernst equation, stability analysis |
| Numerical Core | [docs/NUMERICAL_CORE.md](NUMERICAL_CORE.md) | Discretization, CFL conditions |
| Feature Schema | [docs/FEATURE_SCHEMA.md](FEATURE_SCHEMA.md) | 18-feature extraction specification |
| Roadmap | [docs/ROADMAP.md](ROADMAP.md) | v4.1 → v4.2+ development plan |

---

*Document maintained by: Integration Team*  
*Last updated: 2025-11-29*
