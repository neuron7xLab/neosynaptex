# MFN Data Model — Canonical Data Structures

**Document Version**: 1.1  
**Target Version**: MyceliumFractalNet v4.1.0  
**Status**: Final  
**Last Updated**: 2025-12-01

---

## 1. Overview

This document defines the canonical data structures for MyceliumFractalNet (MFN).
All types are located in the `src/mycelium_fractal_net/types/` module and serve as
the single source of truth for data flowing through the system.

### Design Principles

1. **Single Source of Truth**: Each domain concept is defined once in the types module
2. **Documentation Alignment**: Field names match MFN_FEATURE_SCHEMA.md and MFN_DATA_PIPELINES.md
3. **Validation on Construction**: All types validate their invariants when created
4. **Interoperability**: Types support conversion to/from dict, numpy array, and DataFrame

### Module Structure

```
src/mycelium_fractal_net/types/
├── __init__.py      # Package exports
├── config.py        # Configuration types (SimulationConfig, SimulationResult, FeatureConfig, DatasetConfig)
├── field.py         # Field types (FieldState, FieldHistory, GridShape, BoundaryCondition)
├── features.py      # Feature types (FeatureVector, FEATURE_NAMES, FEATURE_COUNT)
├── scenario.py      # Scenario types (ScenarioConfig, ScenarioType)
└── dataset.py       # Dataset types (DatasetRow, DatasetMeta, DatasetStats)
```

---

## 2. Core Data Entities

### 2.1 Entity Summary

| Entity | Python Type | Location | Purpose |
|--------|-------------|----------|---------|
| SimulationConfig | dataclass | `types/config.py` | Simulation parameters |
| SimulationResult | dataclass | `types/config.py` | Simulation output data |
| FeatureConfig | dataclass | `types/config.py` | Feature extraction settings |
| DatasetConfig | dataclass | `types/config.py` | Dataset generation settings |
| FieldState | dataclass | `types/field.py` | Single field snapshot |
| FieldHistory | dataclass | `types/field.py` | Field time series |
| GridShape | dataclass | `types/field.py` | Grid dimensions |
| BoundaryCondition | Enum | `types/field.py` | Boundary condition type |
| FeatureVector | dataclass | `types/features.py` | 18 fractal features |
| ScenarioConfig | dataclass | `types/scenario.py` | Data generation scenario |
| ScenarioType | Enum | `types/scenario.py` | Scenario category |
| DatasetRow | dataclass | `types/dataset.py` | Single dataset record |
| DatasetMeta | dataclass | `types/dataset.py` | Dataset metadata |
| DatasetStats | dataclass | `types/dataset.py` | Dataset statistics |

---

## 3. Configuration Types

### 3.1 SimulationConfig

Configuration for mycelium field simulation.

```python
from mycelium_fractal_net.types import SimulationConfig

config = SimulationConfig(
    grid_size=64,           # Grid dimension N (N×N)
    steps=100,              # Simulation steps
    alpha=0.18,             # Diffusion coefficient (≤ 0.25 for CFL)
    spike_probability=0.25, # Growth event probability
    turing_enabled=True,    # Enable Turing patterns
    turing_threshold=0.75,  # Activation threshold
    quantum_jitter=False,   # Enable stochastic noise
    jitter_var=0.0005,      # Noise variance
    seed=42,                # Random seed
)
```

**Invariants:**
- `grid_size` ∈ [4, 512]
- `steps` ∈ [1, 10000]
- `alpha` ∈ (0, 0.25] (CFL stability)
- `spike_probability` ∈ [0, 1]
- `turing_threshold` ∈ [0, 1]

**Serialization:**
```python
# Convert to dictionary
config_dict = config.to_dict()

# Create from dictionary
config = SimulationConfig.from_dict(config_dict)
```

**Reference:** [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) Section 2

### 3.2 SimulationResult

Container for simulation output data.

```python
from mycelium_fractal_net.types import SimulationResult
import numpy as np

# Create result from simulation output
result = SimulationResult(
    field=np.zeros((64, 64)) - 0.070,  # Final field in Volts
    history=np.zeros((100, 64, 64)),    # Optional: time series
    growth_events=25,                    # Growth events count
    turing_activations=150,              # Turing activation events
    clamping_events=10,                  # Field clamping events
    metadata={"seed": 42, "elapsed_s": 1.5},
)

# Access properties
print(f"Grid size: {result.grid_size}")
print(f"Has history: {result.has_history}")
print(f"Time steps: {result.num_steps}")
```

**Invariants:**
- `field` must be 2D square array (N × N)
- `history` if present must be 3D array (T, N, N) with spatial dimensions matching field
- No NaN or Inf values in field

**Serialization:**
```python
# Convert to dictionary (without arrays for metadata only)
meta_dict = result.to_dict(include_arrays=False)

# Convert to dictionary (with arrays for full serialization)
full_dict = result.to_dict(include_arrays=True)

# Create from dictionary
result = SimulationResult.from_dict(full_dict)
```

**Reference:** [MFN_DATA_PIPELINES.md](MFN_DATA_PIPELINES.md) Section 5.3

### 3.3 FeatureConfig

Configuration for feature extraction.

```python
from mycelium_fractal_net.types import FeatureConfig

config = FeatureConfig(
    min_box_size=2,          # Minimum box size for box-counting
    max_box_size=None,       # None = grid_size // 2
    num_scales=5,            # Scales for dimension estimation
    threshold_low_mv=-60.0,  # Low threshold (mV)
    threshold_med_mv=-50.0,  # Medium threshold (mV)
    threshold_high_mv=-40.0, # High threshold (mV)
    stability_threshold_mv=0.001,
    stability_window=10,     # Steps for stability detection
    connectivity=4,          # 4-connectivity or 8-connectivity
)
```

**Invariants:**
- `num_scales` ∈ [2, 20]
- `threshold_low_mv` < `threshold_med_mv` < `threshold_high_mv`
- `connectivity` ∈ {4, 8}

**Reference:** [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) Section 5

### 3.4 DatasetConfig

Configuration for dataset generation.

```python
from mycelium_fractal_net.types import DatasetConfig

config = DatasetConfig(
    num_samples=200,
    grid_sizes=[32, 64],
    steps_range=(50, 200),
    alpha_range=(0.10, 0.20),
    turing_values=[True, False],
    base_seed=42,
    output_path=Path("data/mfn_dataset.parquet"),
)
```

**Reference:** [MFN_DATA_PIPELINES.md](MFN_DATA_PIPELINES.md) Section 2

---

## 4. Field Types

### 4.1 FieldState

Represents a 2D potential field at a single time point.

```python
from mycelium_fractal_net.types import FieldState, BoundaryCondition
import numpy as np

data = np.random.randn(64, 64) * 0.01 - 0.070  # mV → V
field = FieldState(data=data, boundary=BoundaryCondition.PERIODIC)

# Access statistics
print(f"Mean: {field.mean_mV:.1f} mV")
print(f"Range: [{field.min_mV:.1f}, {field.max_mV:.1f}] mV")

# Convert to binary
binary = field.to_binary(threshold_v=-0.060)
```

**Invariants:**
- `data` must be 2D with shape (N, M) where N, M ≥ 2
- No NaN or Inf values

**Reference:** [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) Section 2.6

### 4.2 FieldHistory

Time series of field snapshots for temporal analysis.

```python
from mycelium_fractal_net.types import FieldHistory
import numpy as np

# Shape: (time_steps, rows, cols)
data = np.random.randn(100, 64, 64) * 0.01 - 0.070
history = FieldHistory(data=data)

print(f"Steps: {history.num_steps}")
print(f"Grid: {history.grid_size}×{history.grid_size}")

# Access individual frames
initial = history.initial_state  # FieldState at t=0
final = history.final_state      # FieldState at t=T-1
frame_50 = history.get_frame(50) # FieldState at t=50
```

**Invariants:**
- `data` must be 3D with shape (T, N, M) where T ≥ 1, N, M ≥ 2
- No NaN or Inf values

**Reference:** [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) Section 2.3

### 4.3 GridShape

Immutable grid shape specification.

```python
from mycelium_fractal_net.types import GridShape

# Square grid
shape = GridShape.square(64)
print(f"Size: {shape.size}")
print(f"Total cells: {shape.total_cells}")

# Rectangular grid
rect = GridShape(rows=32, cols=64)
print(f"Is square: {rect.is_square}")
```

### 4.4 BoundaryCondition

Enum for boundary condition types.

```python
from mycelium_fractal_net.types import BoundaryCondition

bc = BoundaryCondition.PERIODIC   # Wrap-around (default)
bc = BoundaryCondition.NEUMANN    # Zero-flux
bc = BoundaryCondition.DIRICHLET  # Fixed-value
```

---

## 5. Feature Types

### 5.1 FeatureVector

The canonical 18-feature vector as defined in [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md).

```python
from mycelium_fractal_net.types import FeatureVector

# Create with specific values
fv = FeatureVector(
    D_box=1.5,        # Fractal dimension
    D_r2=0.95,        # Regression quality
    V_min=-90.0,      # mV
    V_max=-40.0,      # mV
    V_mean=-65.0,     # mV
    V_std=10.0,       # mV
    V_skew=0.1,
    V_kurt=-0.5,
    dV_mean=0.5,      # mV/step
    dV_max=5.0,       # mV/step
    T_stable=50,      # steps
    E_trend=-0.1,     # mV²/step
    f_active=0.3,
    N_clusters_low=10,
    N_clusters_med=5,
    N_clusters_high=2,
    max_cluster_size=100,
    cluster_size_std=20.0,
)

# Convert to dictionary
d = fv.to_dict()

# Convert to numpy array (fixed order)
arr = fv.to_array()  # shape: (18,)

# Create from array
fv2 = FeatureVector.from_array(arr)
```

### 5.2 Feature Names (Canonical Order)

```python
from mycelium_fractal_net.types import FEATURE_NAMES, FEATURE_COUNT

print(f"Total features: {FEATURE_COUNT}")  # 18
for i, name in enumerate(FEATURE_NAMES, 1):
    print(f"{i:2d}. {name}")
```

**Feature List:**

| # | Name | Category | Description | Units | Range |
|---|------|----------|-------------|-------|-------|
| 1 | `D_box` | Fractal | Box-counting dimension | — | [0, 2.5] |
| 2 | `D_r2` | Fractal | Regression R² quality | — | [0, 1] |
| 3 | `V_min` | Statistics | Minimum potential | mV | [-95, 40] |
| 4 | `V_max` | Statistics | Maximum potential | mV | [-95, 40] |
| 5 | `V_mean` | Statistics | Mean potential | mV | [-95, 40] |
| 6 | `V_std` | Statistics | Standard deviation | mV | [0, ∞) |
| 7 | `V_skew` | Statistics | Skewness | — | (−∞, +∞) |
| 8 | `V_kurt` | Statistics | Excess kurtosis | — | (−∞, +∞) |
| 9 | `dV_mean` | Temporal | Mean rate of change | mV/step | [0, ∞) |
| 10 | `dV_max` | Temporal | Max rate of change | mV/step | [0, ∞) |
| 11 | `T_stable` | Temporal | Steps to quasi-stationary | steps | [0, T] |
| 12 | `E_trend` | Temporal | Energy trend slope | mV²/step | (−∞, +∞) |
| 13 | `f_active` | Structural | Active cell fraction | — | [0, 1] |
| 14 | `N_clusters_low` | Structural | Clusters at -60mV | count | [0, N²] |
| 15 | `N_clusters_med` | Structural | Clusters at -50mV | count | [0, N²] |
| 16 | `N_clusters_high` | Structural | Clusters at -40mV | count | [0, N²] |
| 17 | `max_cluster_size` | Structural | Largest cluster | cells | [0, N²] |
| 18 | `cluster_size_std` | Structural | Cluster size std | cells | [0, ∞) |

**Reference:** [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) Section 3

---

## 6. Scenario & Dataset Types

### 6.1 ScenarioConfig

Configuration for data generation scenarios.

```python
from mycelium_fractal_net.types import ScenarioConfig, ScenarioType

config = ScenarioConfig(
    name="features_medium",
    scenario_type=ScenarioType.FEATURES,
    grid_size=64,
    steps=100,
    num_samples=100,
    seeds_per_config=3,
    base_seed=42,
    alpha_values=[0.10, 0.15, 0.20],
    turing_enabled=True,
    output_format="parquet",
    output_dir="scenarios/features_medium",
    description="Medium feature-generation scenario for ML training.",
)
```

### 6.2 ScenarioType

```python
from mycelium_fractal_net.types import ScenarioType

ScenarioType.SCIENTIFIC   # Validation, physics testing
ScenarioType.FEATURES     # ML feature generation
ScenarioType.BENCHMARK    # Performance testing
```

### 6.3 DatasetRow

Single row in an MFN dataset.

```python
from mycelium_fractal_net.types import DatasetRow

row = DatasetRow(
    sim_id=0,
    scenario_name="test_scenario",
    grid_size=64,
    steps=100,
    alpha=0.18,
    turing_enabled=True,
    random_seed=42,
    features={"D_box": 1.5, "V_mean": -65.0},
    growth_events=15,
    turing_activations=100,
    clamping_events=5,
)

# Convert to flat dict for DataFrame
d = row.to_dict()

# Create from dict
row2 = DatasetRow.from_dict(d)

# Get feature array
arr = row.feature_array()  # shape: (18,)
```

### 6.4 DatasetMeta

Metadata about a generated dataset.

```python
from mycelium_fractal_net.types import DatasetMeta
from pathlib import Path

meta = DatasetMeta(
    scenario_name="features_medium",
    output_path=Path("data/dataset.parquet"),
    num_rows=100,
    num_columns=28,
    elapsed_seconds=45.2,
    timestamp="20250530_120000",
    feature_names=FEATURE_NAMES,
)
```

### 6.5 DatasetStats

Statistical summary of a dataset.

```python
from mycelium_fractal_net.types import DatasetStats
import pandas as pd

# From DataFrame
df = pd.read_parquet("data/dataset.parquet")
stats = DatasetStats.from_dataframe(df)

print(f"Rows: {stats.num_rows}")
print(f"Features: {stats.num_features}")
print(f"Has all features: {stats.has_expected_features()}")
```

---

## 7. Dataset Schema

### 7.1 Column Order

Datasets follow a canonical column order:

1. **Simulation Parameters** (7 columns):
   - `sim_id`, `scenario_name`, `grid_size`, `steps`, `alpha`, `turing_enabled`, `random_seed`

2. **Features** (18 columns):
   - `D_box`, `D_r2`, `V_min`, `V_max`, `V_mean`, `V_std`, `V_skew`, `V_kurt`
   - `dV_mean`, `dV_max`, `T_stable`, `E_trend`
   - `f_active`, `N_clusters_low`, `N_clusters_med`, `N_clusters_high`, `max_cluster_size`, `cluster_size_std`

3. **Simulation Metadata** (3 columns):
   - `growth_events`, `turing_activations`, `clamping_events`

### 7.2 Data Contract

| Constraint | Description |
|------------|-------------|
| No NaN features | All 18 features computed for every row |
| Bounded potentials | V_min ∈ [-95, -60], V_max ∈ [-50, 40] mV |
| Valid fractions | f_active ∈ [0, 1] |
| Non-negative counts | All cluster counts ≥ 0 |
| Dimension range | D_box ∈ [0, 2.5] |

**Reference:** [MFN_DATA_PIPELINES.md](MFN_DATA_PIPELINES.md) Section 7

---

## 8. Usage in MFN Layers

| Layer | Types Used |
|-------|-----------|
| **core/** | SimulationConfig, SimulationResult |
| **analytics/** | FeatureVector, FeatureConfig |
| **pipelines/** | ScenarioConfig, DatasetMeta, DatasetRow |
| **integration/** | API request/response models |
| **examples/** | All configuration and result types |

---

## 9. References

| Document | Description |
|----------|-------------|
| [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md) | System capabilities and I/O contracts |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) | Mathematical formalization |
| [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) | Feature definitions |
| [MFN_DATA_PIPELINES.md](MFN_DATA_PIPELINES.md) | Dataset schema and scenarios |
| [MFN_CODE_STRUCTURE.md](MFN_CODE_STRUCTURE.md) | Code organization |

---

*Document maintained by: MFN Development Team*  
*Last updated: 2025-11-30*
