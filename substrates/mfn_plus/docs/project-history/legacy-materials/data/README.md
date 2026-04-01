# Data Directory — MyceliumFractalNet

This directory contains generated datasets from MFN simulations.

## ⚠️ Important Notes

1. **Do NOT commit large files** to this repository
   - Dataset files (`.parquet`, `.csv`, `.npz`) are gitignored
   - Only small synthetic examples (< 1MB) may be committed
   - Large datasets should be stored externally (S3, GCS, etc.)

2. **Local datasets are your responsibility**
   - Clean up old datasets periodically
   - Use `git clean -fd data/scenarios/` to remove all generated data

## Directory Structure

```
data/
├── README.md                          # This file
├── scenarios/                         # Scenario-based outputs (recommended)
│   ├── scientific_small/              # Quick validation datasets
│   │   └── YYYYMMDD_HHMMSS/
│   │       └── dataset.parquet
│   ├── features_medium/               # Standard ML datasets
│   │   └── YYYYMMDD_HHMMSS/
│   │       └── dataset.parquet
│   └── features_large/                # Production ML datasets
│       └── YYYYMMDD_HHMMSS/
│           └── dataset.parquet
└── mycelium_dataset.parquet           # Legacy output location
```

## Generating Datasets

### Quick Start (Recommended)

```bash
# Small dataset for testing (< 10 samples, ~5 seconds)
python -m experiments.generate_dataset --preset small

# Medium dataset for development (100 samples, ~1-2 minutes)
python -m experiments.generate_dataset --preset medium

# Large dataset for production (500 samples, ~10-30 minutes)
python -m experiments.generate_dataset --preset large
```

### List Available Presets

```bash
python -m experiments.generate_dataset --list-presets
```

### Legacy Mode

```bash
python -m experiments.generate_dataset --sweep default --output data/mycelium_dataset.parquet
```

## Dataset Schema

Each dataset contains:

| Category | Columns | Count |
|----------|---------|-------|
| Simulation parameters | `sim_id`, `scenario_name`, `grid_size`, `steps`, `alpha`, `turing_enabled`, `random_seed` | 7 |
| Fractal features | `D_box`, `D_r2`, `V_min`, `V_max`, `V_mean`, `V_std`, `V_skew`, `V_kurt`, `dV_mean`, `dV_max`, `T_stable`, `E_trend`, `f_active`, `N_clusters_low`, `N_clusters_med`, `N_clusters_high`, `max_cluster_size`, `cluster_size_std` | 18 |
| Simulation metadata | `growth_events`, `turing_activations`, `clamping_events` | 3 |

**Total: 28 columns**

See [docs/MFN_DATA_PIPELINES.md](../docs/MFN_DATA_PIPELINES.md) for full schema documentation.

## Loading Datasets

```python
import pandas as pd

# Load a scenario dataset
df = pd.read_parquet("data/scenarios/features_medium/20250530_120000/dataset.parquet")

# Access features
print(df["D_box"].describe())
print(df[["V_mean", "f_active"]].head())
```

## Cleaning Up

```bash
# Remove all generated datasets (keeps README)
git clean -fd data/scenarios/

# Or manually
rm -rf data/scenarios/*/

# Check what's gitignored
git status --ignored data/
```

## .gitignore Settings

The following patterns are ignored:

```
data/*.parquet
data/*.csv
data/*.npz
data/scenarios/
```

To commit a small example dataset, use `git add -f data/example.parquet`.

