# Feature Schema — MyceliumFractalNet v4.1

This document defines the fractal analytics feature extraction schema for MyceliumFractalNet.
All features are designed for ML-readiness, reproducibility, and interpretability.

---

## 1. Overview

The feature extraction module transforms raw simulation outputs (2D potential fields and their
time series) into a structured feature vector suitable for downstream ML tasks.

### Design Principles

1. **Mathematical meaning**: Every feature has a clear physical or geometric interpretation.
2. **Stability**: Features are numerically stable and robust to noise.
3. **Scale invariance**: Core features are designed to be relatively invariant to grid size.
4. **Reproducibility**: Deterministic given the same input and configuration.

---

## 2. Feature Categories

### 2.1 Fractal Features (Geometry/Pattern Complexity)

| Feature | Symbol | Description | Range | Units |
|---------|--------|-------------|-------|-------|
| Box-counting dimension | `D_box` | Fractal dimension via box-counting method | [0, 2] | dimensionless |
| Dimension R² | `D_r2` | R² of box-counting regression (quality metric) | [0, 1] | dimensionless |

**Implementation Notes:**
- Box-counting uses geometric scale spacing (np.geomspace)
- Minimum 2 scales required for valid regression
- D ∈ [1.4, 1.9] expected for biological mycelium patterns
- D = 2 for filled plane, D ≈ 1 for lines

### 2.2 Basic Field Statistics

| Feature | Symbol | Description | Range | Units |
|---------|--------|-------------|-------|-------|
| Minimum | `V_min` | Minimum field value | [-95, 40] | mV |
| Maximum | `V_max` | Maximum field value | [-95, 40] | mV |
| Mean | `V_mean` | Mean field value | [-95, 40] | mV |
| Standard deviation | `V_std` | Field variance measure | [0, ∞) | mV |
| Skewness | `V_skew` | Asymmetry of distribution | (-∞, +∞) | dimensionless |
| Kurtosis | `V_kurt` | Tailedness of distribution | (-∞, +∞) | dimensionless |

**Implementation Notes:**
- All statistics computed with `np.float64` precision
- Skewness and kurtosis use Fisher's definition (excess kurtosis)
- Values normalized to mV for interpretability

### 2.3 Temporal Features

These features require field history (multiple time steps).

| Feature | Symbol | Description | Range | Units |
|---------|--------|-------------|-------|-------|
| Mean rate of change | `dV_mean` | Average |V(t) - V(t-1)| per step | [0, ∞) | mV/step |
| Max rate of change | `dV_max` | Maximum instantaneous change | [0, ∞) | mV/step |
| Steps to quasi-stationary | `T_stable` | Steps until std(dV) < threshold | [0, T] | steps |
| Field energy trend | `E_trend` | Linear slope of sum(V²) over time | (-∞, +∞) | mV²/step |

**Implementation Notes:**
- Quasi-stationary threshold: `std(dV) < 0.001 mV/step` for 10 consecutive steps
- Energy trend computed via linear regression on field L2 norm
- Returns `T` (max steps) if stability not reached

### 2.4 Structural Features

| Feature | Symbol | Description | Range | Units |
|---------|--------|-------------|-------|-------|
| Active fraction | `f_active` | Fraction of cells above threshold | [0, 1] | dimensionless |
| Cluster count (low) | `N_clusters_low` | Connected components at -60mV threshold | [0, N²] | count |
| Cluster count (med) | `N_clusters_med` | Connected components at -50mV threshold | [0, N²] | count |
| Cluster count (high) | `N_clusters_high` | Connected components at -40mV threshold | [0, N²] | count |
| Max cluster size | `max_cluster_size` | Size of largest connected component | [0, N²] | cells |
| Cluster size std | `cluster_size_std` | Standard deviation of cluster sizes | [0, N²] | cells |

**Implementation Notes:**
- Connectivity uses 4-connectivity (von Neumann neighborhood)
- Thresholds chosen to span physiological range: -60mV (subthreshold), -50mV (active), -40mV (highly active)
- Cluster detection uses efficient union-find algorithm

---

## 3. Feature Vector Format

### 3.1 Data Structure

```python
from dataclasses import dataclass
from typing import Dict
import numpy as np

@dataclass
class FeatureVector:
    """Complete feature vector from a simulation."""
    
    # Fractal features
    D_box: float           # Box-counting dimension
    D_r2: float            # R² of dimension fit
    
    # Basic statistics (in mV)
    V_min: float
    V_max: float
    V_mean: float
    V_std: float
    V_skew: float
    V_kurt: float
    
    # Temporal features (require history)
    dV_mean: float         # Mean rate of change
    dV_max: float          # Max rate of change
    T_stable: int          # Steps to quasi-stationary
    E_trend: float         # Energy trend
    
    # Structural features
    f_active: float        # Active fraction at -60mV
    N_clusters_low: int    # Clusters at -60mV
    N_clusters_med: int    # Clusters at -50mV
    N_clusters_high: int   # Clusters at -40mV
    max_cluster_size: int
    cluster_size_std: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'D_box': self.D_box,
            'D_r2': self.D_r2,
            'V_min': self.V_min,
            'V_max': self.V_max,
            'V_mean': self.V_mean,
            'V_std': self.V_std,
            'V_skew': self.V_skew,
            'V_kurt': self.V_kurt,
            'dV_mean': self.dV_mean,
            'dV_max': self.dV_max,
            'T_stable': float(self.T_stable),
            'E_trend': self.E_trend,
            'f_active': self.f_active,
            'N_clusters_low': float(self.N_clusters_low),
            'N_clusters_med': float(self.N_clusters_med),
            'N_clusters_high': float(self.N_clusters_high),
            'max_cluster_size': float(self.max_cluster_size),
            'cluster_size_std': self.cluster_size_std,
        }
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array (fixed order)."""
        return np.array([
            self.D_box,
            self.D_r2,
            self.V_min,
            self.V_max,
            self.V_mean,
            self.V_std,
            self.V_skew,
            self.V_kurt,
            self.dV_mean,
            self.dV_max,
            float(self.T_stable),
            self.E_trend,
            self.f_active,
            float(self.N_clusters_low),
            float(self.N_clusters_med),
            float(self.N_clusters_high),
            float(self.max_cluster_size),
            self.cluster_size_std,
        ], dtype=np.float64)
```

### 3.2 Feature Ordering (Fixed)

Features are always output in this exact order:

1. `D_box`
2. `D_r2`
3. `V_min`
4. `V_max`
5. `V_mean`
6. `V_std`
7. `V_skew`
8. `V_kurt`
9. `dV_mean`
10. `dV_max`
11. `T_stable`
12. `E_trend`
13. `f_active`
14. `N_clusters_low`
15. `N_clusters_med`
16. `N_clusters_high`
17. `max_cluster_size`
18. `cluster_size_std`

**Total: 18 features**

---

## 4. Stability Requirements

### 4.1 Numerical Stability

| Feature | NaN Handling | Inf Handling |
|---------|--------------|--------------|
| `D_box` | Returns 0.0 if < 2 valid points | Never Inf |
| `D_r2` | Returns 0.0 if undefined | Clamped to [0, 1] |
| `V_skew`, `V_kurt` | Returns 0.0 if std = 0 | Never Inf |
| `dV_*` | Returns 0.0 if history length < 2 | Never Inf |
| Cluster counts | Returns 0 for empty field | N/A |

### 4.2 Scale Invariance

The following features are designed to be approximately invariant to grid size:

- `D_box` — Fractal dimension (by definition)
- `V_mean`, `V_std`, `V_skew`, `V_kurt` — Statistical moments
- `f_active` — Normalized fraction
- `dV_mean` — Per-cell average

Features that scale with grid size:

- `N_clusters_*` — Count increases with grid area
- `max_cluster_size` — Size depends on grid area
- `cluster_size_std` — Depends on cluster sizes

---

## 5. Configuration

```python
from dataclasses import dataclass

@dataclass
class FeatureConfig:
    """Configuration for feature extraction."""
    
    # Box-counting parameters
    min_box_size: int = 2
    max_box_size: int | None = None  # Auto: grid_size // 2
    num_scales: int = 5
    
    # Thresholds for structural features (in mV)
    threshold_low_mv: float = -60.0
    threshold_med_mv: float = -50.0
    threshold_high_mv: float = -40.0
    
    # Temporal feature parameters
    stability_threshold_mv: float = 0.001  # mV/step
    stability_window: int = 10  # consecutive steps required
    
    # Connectivity for cluster detection
    connectivity: int = 4  # 4 or 8
```

---

## 6. Expected Ranges (Validation)

Based on MFN_MATH_MODEL.md and empirical validation:

| Feature | Expected Range | Notes |
|---------|----------------|-------|
| `D_box` | [1.0, 2.5] | For MFN simulations (biological: [1.4, 1.9]) |
| `D_r2` | [0.9, 1.0] | Good fit expected |
| `V_min` | [-95, -60] | Clamped lower bound |
| `V_max` | [-50, 40] | Clamped upper bound |
| `V_mean` | [-80, -50] | Near resting potential |
| `V_std` | [1, 20] | Moderate variability |
| `V_skew` | [-2, 2] | Moderate asymmetry |
| `V_kurt` | [-2, 5] | Near normal to heavy-tailed |
| `T_stable` | [10, steps] | Depends on simulation length |
| `f_active` | [0.01, 0.5] | Sparse activation expected |

---

## 7. API Reference

### Main Function

```python
def compute_features(
    field_snapshots: np.ndarray,
    config: FeatureConfig | None = None,
) -> FeatureVector:
    """
    Compute all features from field snapshots.
    
    Parameters
    ----------
    field_snapshots : np.ndarray
        Field data. Shape (N, N) for single snapshot or (T, N, N) for history.
        Values in Volts.
    config : FeatureConfig | None
        Feature extraction configuration.
        
    Returns
    -------
    FeatureVector
        Complete feature vector with all 18 features.
        
    Raises
    ------
    ValueError
        If field_snapshots has invalid shape.
    """
```

### Utility Functions

```python
def compute_fractal_features(field: np.ndarray, config: FeatureConfig) -> tuple[float, float]:
    """Compute D_box and D_r2."""

def compute_basic_stats(field: np.ndarray) -> tuple[float, ...]:
    """Compute V_min, V_max, V_mean, V_std, V_skew, V_kurt."""

def compute_temporal_features(history: np.ndarray, config: FeatureConfig) -> tuple[float, ...]:
    """Compute dV_mean, dV_max, T_stable, E_trend."""

def compute_structural_features(field: np.ndarray, config: FeatureConfig) -> tuple[float, ...]:
    """Compute f_active, N_clusters_*, max_cluster_size, cluster_size_std."""
```

---

## 8. Experimental Features (Optional)

The following features are marked as **experimental** and may be included in future versions:

| Feature | Description | Status |
|---------|-------------|--------|
| `D_correlation` | Correlation dimension | Experimental |
| `D_information` | Information dimension | Experimental |
| `H_entropy` | Shannon entropy of field | Experimental |
| `L_perimeter` | Total perimeter of active regions | Experimental |
| `compactness` | Isoperimetric quotient | Experimental |

These features require additional validation and may be resource-intensive.

---

## 9. Dataset Format

Generated datasets are stored in Parquet format with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `sim_id` | int64 | Unique simulation identifier |
| `random_seed` | int64 | Seed used for reproducibility |
| `grid_size` | int64 | Grid dimension N |
| `steps` | int64 | Simulation steps |
| `alpha` | float64 | Diffusion coefficient |
| `turing_enabled` | bool | Turing morphogenesis flag |
| `D_box` | float64 | Feature value |
| ... | float64 | All 18 features |

---

*Document Version: 1.0*
*Last Updated: 2025*
*Applies to: MyceliumFractalNet v4.1.0*
