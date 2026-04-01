# MFN Data Pipelines — MyceliumFractalNet v4.1

This document defines the canonical data contract for MyceliumFractalNet data pipelines,
including scenario types, file layouts, and feature schemas.

---

## 1. Overview

The MFN data pipeline provides a unified interface for generating datasets from simulations.
It is designed to be:

- **Domain-agnostic**: Scenarios are not tied to specific applications (finance, biology, etc.)
- **Extensible**: New scenarios can be added without modifying core pipeline code
- **Reproducible**: All datasets are generated with controlled random seeds
- **Validated**: Output conforms to the feature schema in `FEATURE_SCHEMA.md`

---

## 2. Scenario Types

### 2.1 Scientific Scenarios

**Purpose**: Validate core physics and mathematical models (Nernst, Turing, STDP).

| Scenario | Description | Default Grid | Steps | Samples |
|----------|-------------|--------------|-------|---------|
| `scientific_small` | Quick validation of core models | 32×32 | 50 | 10 |

**Use case**: CI/CD testing, quick sanity checks, physics validation.

### 2.2 Feature Generation Scenarios

**Purpose**: Generate feature vectors for ML training and analysis.

| Scenario | Description | Default Grid | Steps | Samples |
|----------|-------------|--------------|-------|---------|
| `features_medium` | Standard ML training dataset | 64×64 | 100 | 100 |
| `features_large` | Production ML dataset | 128×128 | 200 | 500 |

**Use case**: Training ML models, feature analysis, statistical studies.

### 2.3 Benchmark Scenarios

**Purpose**: Performance testing and regression detection.

| Scenario | Description | Default Grid | Steps | Samples |
|----------|-------------|--------------|-------|---------|
| `benchmark_small` | Quick performance test | 32×32 | 32 | 5 |

**Use case**: CI performance gates, optimization testing.

---

## 3. CLI Usage

### Quick Start with Presets

```bash
# List available presets
python -m experiments.generate_dataset --list-presets

# Run with a preset
python -m experiments.generate_dataset --preset small
python -m experiments.generate_dataset --preset medium
python -m experiments.generate_dataset --preset large

# With custom seed
python -m experiments.generate_dataset --preset small --seed 123

# Verbose output
python -m experiments.generate_dataset --preset small -v
```

### Legacy Sweep Mode

For backward compatibility, the legacy sweep mode is still supported:

```bash
python -m experiments.generate_dataset --sweep default --output data/my_dataset.parquet
```

---

## 4. File Layout

### Directory Structure

```
data/
├── README.md                          # Data directory documentation
├── scenarios/
│   ├── scientific_small/
│   │   └── 20250530_120000/           # Timestamped run
│   │       └── dataset.parquet
│   ├── features_medium/
│   │   └── 20250530_130000/
│   │       └── dataset.parquet
│   └── features_large/
│       └── 20250530_140000/
│           └── dataset.parquet
└── mycelium_dataset.parquet           # Legacy output location
```

### Naming Convention

- **Scenario directories**: `data/scenarios/<scenario_name>/<timestamp>/`
- **Dataset files**: `dataset.parquet` (or `.csv` if specified)
- **Timestamp format**: `YYYYMMDD_HHMMSS`

---

## 5. Dataset Schema (Columns)

### 5.1 Simulation Parameters

| Column | Type | Description | Units |
|--------|------|-------------|-------|
| `sim_id` | int64 | Unique simulation identifier | — |
| `scenario_name` | string | Name of the scenario | — |
| `grid_size` | int64 | Grid dimension N (N×N) | cells |
| `steps` | int64 | Number of simulation steps | steps |
| `alpha` | float64 | Diffusion coefficient | grid²/step |
| `turing_enabled` | bool | Turing morphogenesis enabled | — |
| `random_seed` | int64 | Random seed for reproducibility | — |

### 5.2 Fractal Features (18 total)

| Column | Type | Description | Units | Expected Range |
|--------|------|-------------|-------|----------------|
| `D_box` | float64 | Box-counting fractal dimension | — | [1.0, 2.5] |
| `D_r2` | float64 | R² of dimension regression | — | [0.0, 1.0] |
| `V_min` | float64 | Minimum field value | mV | [-95, -60] |
| `V_max` | float64 | Maximum field value | mV | [-50, 40] |
| `V_mean` | float64 | Mean field value | mV | [-80, -50] |
| `V_std` | float64 | Field standard deviation | mV | [1, 20] |
| `V_skew` | float64 | Field skewness | — | [-2, 2] |
| `V_kurt` | float64 | Field kurtosis (excess) | — | [-2, 5] |
| `dV_mean` | float64 | Mean rate of change | mV/step | [0, ∞) |
| `dV_max` | float64 | Max rate of change | mV/step | [0, ∞) |
| `T_stable` | int64 | Steps to quasi-stationary | steps | [0, T] |
| `E_trend` | float64 | Energy trend slope | mV²/step | (-∞, +∞) |
| `f_active` | float64 | Active cell fraction | — | [0.0, 1.0] |
| `N_clusters_low` | int64 | Clusters at -60mV | count | [0, N²] |
| `N_clusters_med` | int64 | Clusters at -50mV | count | [0, N²] |
| `N_clusters_high` | int64 | Clusters at -40mV | count | [0, N²] |
| `max_cluster_size` | int64 | Largest cluster size | cells | [0, N²] |
| `cluster_size_std` | float64 | Cluster size std dev | cells | [0, N²] |

### 5.3 Simulation Metadata

| Column | Type | Description | Units |
|--------|------|-------------|-------|
| `growth_events` | int64 | Number of growth events | count |
| `turing_activations` | int64 | Turing activation events | count |
| `clamping_events` | int64 | Field clamping events | count |

---

## 6. Python API

### Basic Usage

```python
from mycelium_fractal_net.pipelines import (
    ScenarioConfig,
    ScenarioType,
    run_scenario,
    get_preset_config,
    list_presets,
)

# List available presets
print(list_presets())  # ['small', 'medium', 'large', 'benchmark']

# Run a preset scenario
config = get_preset_config("small")
meta = run_scenario(config)
print(f"Dataset saved to: {meta.output_path}")

# Custom scenario
custom_config = ScenarioConfig(
    name="my_experiment",
    scenario_type=ScenarioType.FEATURES,
    grid_size=64,
    steps=100,
    num_samples=50,
    alpha_values=[0.12, 0.18],
    output_dir="scenarios/my_experiment",
)
meta = run_scenario(custom_config)
```

### Loading Generated Datasets

```python
import pandas as pd

# Load a generated dataset
df = pd.read_parquet("data/scenarios/features_medium/20250530_130000/dataset.parquet")

# Access features
print(df["D_box"].describe())
print(df[["V_mean", "V_std", "f_active"]].head())
```

---

## 7. Data Contract Guarantees

### 7.1 Column Presence

Every dataset contains:
1. All 7 simulation parameter columns
2. All 18 fractal feature columns (as per `FEATURE_SCHEMA.md`)
3. All 3 simulation metadata columns

### 7.2 Value Constraints

| Constraint | Description |
|------------|-------------|
| No NaN features | All 18 features are computed for every row |
| Bounded potentials | V_min ∈ [-95, -60], V_max ∈ [-50, 40] mV |
| Valid fractions | f_active ∈ [0, 1] |
| Non-negative counts | All cluster counts ≥ 0 |
| Dimension range | D_box ∈ [0, 2.5] |

### 7.3 Atomic Writes

All datasets are written atomically:
1. Data is written to a temporary file
2. Temporary file is renamed to final destination
3. On failure, partial files are cleaned up

This prevents corrupt datasets from interrupted writes.

---

## 8. Adding New Scenarios

### Step 1: Define the Configuration

```python
# In your code or a config file
from mycelium_fractal_net.pipelines import ScenarioConfig, ScenarioType

my_scenario = ScenarioConfig(
    name="financial_baseline",
    scenario_type=ScenarioType.FEATURES,
    grid_size=64,
    steps=150,
    num_samples=200,
    seeds_per_config=3,
    base_seed=42,
    alpha_values=[0.10, 0.15, 0.20],
    turing_enabled=True,
    output_format="parquet",
    output_dir="scenarios/financial_baseline",
    description="Baseline scenario for financial time series features.",
)
```

### Step 2: Run the Scenario

```python
from mycelium_fractal_net.pipelines import run_scenario

meta = run_scenario(my_scenario)
print(f"Generated {meta.num_rows} samples")
```

### Step 3: Validate Output

```python
import pandas as pd
from analytics import FeatureVector

df = pd.read_parquet(meta.output_path)

# Check all features present
expected_features = FeatureVector.feature_names()
missing = set(expected_features) - set(df.columns)
assert not missing, f"Missing features: {missing}"

# Check value ranges
assert df["f_active"].between(0, 1).all()
assert df["D_box"].between(0, 2.5).all()
```

---

## 9. Best Practices

### For Development/Testing
- Use `--preset small` for quick iterations
- Run with `--verbose` to see progress

### For Production
- Use `--preset medium` or `--preset large`
- Always specify `--seed` for reproducibility
- Monitor `elapsed_seconds` for performance regression

### For CI/CD
- Use `--preset small` or `--preset benchmark`
- Verify output files exist and have expected row counts
- Check that all 18 features are present

---

## 10. References

| Document | Description |
|----------|-------------|
| [FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) | Complete feature definitions |
| [MFN_MATH_MODEL.md](MFN_MATH_MODEL.md) | Mathematical foundations |
| [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md) | System capabilities and boundaries |

---

*Document Version: 1.0*
*Last Updated: 2025*
*Applies to: MyceliumFractalNet v4.1.0*
