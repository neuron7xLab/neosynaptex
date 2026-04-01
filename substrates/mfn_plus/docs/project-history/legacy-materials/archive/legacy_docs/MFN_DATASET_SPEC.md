# Dataset Specification — MyceliumFractalNet v4.1

This document specifies the structure and generation pipeline for experimental datasets
in the MyceliumFractalNet project. All datasets are designed for ML-readiness,
reproducibility, and ease of use.

---

## 1. Overview

### 1.1 Purpose

The dataset generation pipeline transforms simulation configurations into structured
feature vectors suitable for downstream ML tasks. Each row in the dataset represents
one complete simulation run with its extracted features.

### 1.2 Design Principles

1. **Reproducibility**: Fixed seeds yield identical datasets
2. **Machine-readability**: Parquet format with flat schema
3. **Minimal preprocessing**: Ready for ML pipelines
4. **Validation**: Sanity checks prevent invalid data

---

## 2. Dataset Record Schema

### 2.1 Unit of Record

**One row = one simulation run**

Each record contains:
- Simulation configuration parameters
- Extracted features (18 features from MFN_FEATURE_SCHEMA.md)
- Metadata (timestamps, versions, seeds)

### 2.2 Field Definitions

#### Configuration Fields

| Field | Type | Description | Valid Range |
|-------|------|-------------|-------------|
| `sim_id` | int64 | Unique simulation identifier | ≥ 0 |
| `random_seed` | int64 | RNG seed for reproducibility | any int |
| `grid_size` | int64 | Grid dimension N (N×N) | 4–256 |
| `steps` | int64 | Number of simulation steps | 1–10000 |
| `alpha` | float64 | Diffusion coefficient | 0.01–0.24 |
| `turing_enabled` | bool | Turing morphogenesis flag | True/False |
| `spike_probability` | float64 | Probability of spike per step | 0.0–1.0 |
| `turing_threshold` | float64 | Activation threshold | 0.0–1.0 |

#### Feature Fields (18 features)

All features follow the specification in `MFN_FEATURE_SCHEMA.md`:

| Field | Type | Description | Unit |
|-------|------|-------------|------|
| `D_box` | float64 | Box-counting fractal dimension | dimensionless |
| `D_r2` | float64 | R² of dimension regression | dimensionless |
| `V_min` | float64 | Minimum field value | mV |
| `V_max` | float64 | Maximum field value | mV |
| `V_mean` | float64 | Mean field value | mV |
| `V_std` | float64 | Field standard deviation | mV |
| `V_skew` | float64 | Field skewness | dimensionless |
| `V_kurt` | float64 | Field kurtosis (excess) | dimensionless |
| `dV_mean` | float64 | Mean rate of change | mV/step |
| `dV_max` | float64 | Max rate of change | mV/step |
| `T_stable` | int64 | Steps to quasi-stationary | steps |
| `E_trend` | float64 | Energy trend slope | mV²/step |
| `f_active` | float64 | Active cell fraction | dimensionless |
| `N_clusters_low` | int64 | Clusters at -60mV threshold | count |
| `N_clusters_med` | int64 | Clusters at -50mV threshold | count |
| `N_clusters_high` | int64 | Clusters at -40mV threshold | count |
| `max_cluster_size` | int64 | Size of largest cluster | cells |
| `cluster_size_std` | float64 | Cluster size std dev | cells |

#### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `mfn_version` | string | MyceliumFractalNet version |
| `timestamp` | string | ISO 8601 generation timestamp |
| `growth_events` | int64 | Total growth events in simulation |
| `turing_activations` | int64 | Total Turing threshold crossings |
| `clamping_events` | int64 | Total field clamping events |

### 2.3 Column Naming Convention

- All names use `snake_case`
- No spaces or special characters
- Prefixes indicate category:
  - `V_*`: Voltage/field statistics
  - `D_*`: Dimension features
  - `N_*`: Count features
  - `dV_*`: Temporal derivative features

---

## 3. File Format

### 3.1 Primary Format: Parquet

**Default path**: `data/mfn_dataset.parquet`

Parquet is chosen for:
- Efficient columnar storage
- Native support for typed schemas
- Compression and fast reads
- Wide library support (pandas, PyArrow, Polars)

### 3.2 Reading the Dataset

```python
# Option 1: pandas
import pandas as pd
df = pd.read_parquet("data/mfn_dataset.parquet")

# Option 2: PyArrow directly
import pyarrow.parquet as pq
table = pq.read_table("data/mfn_dataset.parquet")
```

### 3.3 Fallback Format: NPZ

If pandas/PyArrow are unavailable, the pipeline falls back to NumPy's `.npz` format:

```python
import numpy as np
data = np.load("data/mfn_dataset.npz")
columns = data["columns"]
values = data["data"]
```

---

## 4. Generation Pipeline

### 4.1 Configuration Sampling

The `SweepConfig` dataclass generates valid simulation configurations within stable parameter ranges:

```python
from experiments import SweepConfig, generate_dataset

# Create sweep configuration
sweep = SweepConfig(
    grid_sizes=[32, 64],
    steps_list=[50, 100],
    alpha_values=[0.10, 0.15, 0.20],
    turing_values=[True, False],
    seeds_per_config=3,
    base_seed=42,
)

# Generate dataset
stats = generate_dataset(sweep, output_path="data/mfn_dataset.parquet")
```

### 4.2 Command Line Interface

```bash
# Generate with defaults
python -m experiments.generate_dataset \
    --output data/mfn_dataset.parquet

# With custom seed and preset
python -m experiments.generate_dataset \
    --sweep extended \
    --seed 123 \
    --output data/mfn_dataset_extended.parquet
```

### 4.3 Error Handling

The pipeline gracefully handles simulation failures:

1. **StabilityError** / **ValueOutOfRangeError**: Logged and skipped
2. **NumericalInstabilityError**: Logged with step number
3. Failed simulations do not appear in the final dataset
4. Summary reports successful vs. failed counts

---

## 5. Dataset Sizes

### 5.1 Base Dataset (this PR)

- **Target**: 100–1000 simulations
- **Grid sizes**: 32, 64
- **Steps**: 50, 100
- **Estimated file size**: 50–500 KB

### 5.2 Extended Dataset (future)

- **Target**: 5000+ simulations
- **Grid sizes**: 32, 64, 128
- **Steps**: 50–500
- **Estimated file size**: 2–5 MB

---

## 6. Validation Invariants

### 6.1 Data Quality Checks

Every generated dataset must satisfy:

1. **No NaN/Inf**: All feature columns contain finite values
2. **Schema compliance**: All expected columns present
3. **Type correctness**: Columns match specified types
4. **Range validity**: Features within expected bounds

### 6.2 Feature Ranges (Sanity Checks)

| Feature | Expected Range | Notes |
|---------|----------------|-------|
| `D_box` | [0.0, 2.5] | Biological: [1.4, 1.9] |
| `D_r2` | [0.0, 1.0] | R² quality metric |
| `V_min` | [-95, -50] mV | Clamped lower bound |
| `V_max` | [-70, 40] mV | Clamped upper bound |
| `f_active` | [0.0, 1.0] | Fraction |

---

## 7. Reproducibility

### 7.1 Seed Control

- **Base seed**: Controls all RNG sequences
- Same `base_seed` → identical configurations
- Same configuration + `random_seed` → identical simulation

### 7.2 Verification

```python
# Generate twice with same settings
dataset1 = generate_dataset(num_samples=10, base_seed=42, output_path=None)
dataset2 = generate_dataset(num_samples=10, base_seed=42, output_path=None)

# Should be identical
assert dataset1 == dataset2
```

---

## 8. Testing

Run dataset generation tests:

```bash
pytest tests/test_mycelium_fractal_net/test_dataset_generation.py -v
```

Tests verify:
1. File creation and schema validity
2. Reproducibility with fixed seeds
3. Graceful handling of failed simulations

---

## 9. References

- `MFN_MATH_MODEL.md`: Mathematical model specification
- `MFN_FEATURE_SCHEMA.md`: Feature extraction specification
- `MFN_INTEGRATION_SPEC.md`: Integration guidelines

---

*Document Version: 1.0*
*Last Updated: 2025*
*Applies to: MyceliumFractalNet v4.1.0*
