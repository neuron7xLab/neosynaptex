"""
Fractal Feature Extraction Module.

Implements the feature extraction pipeline as defined in MFN_FEATURE_SCHEMA.md.

Features extracted:
1. Fractal: D_box (box-counting dimension), D_r2 (regression quality)
2. Basic stats: V_min, V_max, V_mean, V_std, V_skew, V_kurt
3. Temporal: dV_mean, dV_max, T_stable, E_trend
4. Structural: f_active, N_clusters_*, max_cluster_size, cluster_size_std

Reference: docs/MFN_FEATURE_SCHEMA.md

Usage:
    >>> from analytics import compute_features, FeatureConfig
    >>> features = compute_features(field_history, config=FeatureConfig())
    >>> print(features.D_box, features.V_mean)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# === Constants ===
FEATURE_COUNT: int = 18
DEFAULT_MIN_BOX_SIZE: int = 2
DEFAULT_NUM_SCALES: int = 5
DEFAULT_THRESHOLD_LOW_MV: float = -60.0
DEFAULT_THRESHOLD_MED_MV: float = -50.0
DEFAULT_THRESHOLD_HIGH_MV: float = -40.0
DEFAULT_STABILITY_THRESHOLD_MV: float = 0.001
DEFAULT_STABILITY_WINDOW: int = 10

# Expected dimension ranges (from MATH_MODEL.md)
DIMENSION_MIN: float = 0.0
DIMENSION_MAX: float = 2.5
BIOLOGICAL_DIMENSION_MIN: float = 1.4
BIOLOGICAL_DIMENSION_MAX: float = 1.9

# Fractal confidence thresholds
FRACTAL_MIN_GRID_SIZE: int = 8  # Grids below this lack scale range
FRACTAL_MIN_R2: float = 0.8  # R² below this = unstable regression
FRACTAL_MIN_NUM_SCALES: int = 3  # Fewer scales = insufficient for fit


def assess_fractal_confidence(grid_size: int, num_scales: int, d_r2: float) -> str:
    """Assess confidence in fractal dimension estimate.

    Returns "high" or "low_confidence".
    """
    if grid_size < FRACTAL_MIN_GRID_SIZE:
        return "low_confidence"
    if num_scales < FRACTAL_MIN_NUM_SCALES:
        return "low_confidence"
    if d_r2 < FRACTAL_MIN_R2:
        return "low_confidence"
    return "high"


def is_fractal_strong_signal(num_scales: int, d_r2: float) -> bool:
    """Return True if fractal estimate is reliable enough for detection scoring."""
    return num_scales >= FRACTAL_MIN_NUM_SCALES and d_r2 >= FRACTAL_MIN_R2


@dataclass
class FeatureConfig:
    """
    Configuration for feature extraction.

    Attributes
    ----------
    min_box_size : int
        Minimum box size for box-counting. Default 2.
    max_box_size : int | None
        Maximum box size. None = grid_size // 2.
    num_scales : int
        Number of scales for dimension estimation. Default 5.
    threshold_low_mv : float
        Low threshold for structural features (mV). Default -60.
    threshold_med_mv : float
        Medium threshold (mV). Default -50.
    threshold_high_mv : float
        High threshold (mV). Default -40.
    stability_threshold_mv : float
        Threshold for quasi-stationary detection (mV/step). Default 0.001.
    stability_window : int
        Consecutive steps required for stability. Default 10.
    connectivity : int
        Connectivity for cluster detection (4 or 8). Default 4.
    """

    min_box_size: int = DEFAULT_MIN_BOX_SIZE
    max_box_size: int | None = None
    num_scales: int = DEFAULT_NUM_SCALES
    threshold_low_mv: float = DEFAULT_THRESHOLD_LOW_MV
    threshold_med_mv: float = DEFAULT_THRESHOLD_MED_MV
    threshold_high_mv: float = DEFAULT_THRESHOLD_HIGH_MV
    stability_threshold_mv: float = DEFAULT_STABILITY_THRESHOLD_MV
    stability_window: int = DEFAULT_STABILITY_WINDOW
    connectivity: int = 4

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.min_box_size < 1:
            raise ValueError("min_box_size must be at least 1")
        if self.num_scales < 2:
            raise ValueError("num_scales must be at least 2")
        if self.connectivity not in (4, 8):
            raise ValueError("connectivity must be 4 or 8")


@dataclass
class FeatureVector:
    """
    Complete feature vector from a simulation.

    All 18 features as defined in FEATURE_SCHEMA.md.
    """

    # Fractal features
    D_box: float = 0.0
    D_r2: float = 0.0
    fractal_confidence: str = "high"  # metadata: "high" or "low_confidence"

    # Basic statistics (in mV)
    V_min: float = 0.0
    V_max: float = 0.0
    V_mean: float = 0.0
    V_std: float = 0.0
    V_skew: float = 0.0
    V_kurt: float = 0.0

    # Temporal features
    dV_mean: float = 0.0
    dV_max: float = 0.0
    T_stable: int = 0
    E_trend: float = 0.0

    # Structural features
    f_active: float = 0.0
    N_clusters_low: int = 0
    N_clusters_med: int = 0
    N_clusters_high: int = 0
    max_cluster_size: int = 0
    cluster_size_std: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary with float values."""
        return {name: float(getattr(self, name)) for name in self.feature_names()}

    def to_array(self) -> NDArray[np.float64]:
        """Convert to numpy array (fixed order as per FEATURE_SCHEMA.md)."""
        return np.array(
            [float(getattr(self, name)) for name in self.feature_names()],
            dtype=np.float64,
        )

    @classmethod
    def feature_names(cls) -> list[str]:
        """Get list of feature names in order."""
        return [
            "D_box",
            "D_r2",
            "V_min",
            "V_max",
            "V_mean",
            "V_std",
            "V_skew",
            "V_kurt",
            "dV_mean",
            "dV_max",
            "T_stable",
            "E_trend",
            "f_active",
            "N_clusters_low",
            "N_clusters_med",
            "N_clusters_high",
            "max_cluster_size",
            "cluster_size_std",
        ]

    @classmethod
    def from_array(cls, arr: NDArray[np.float64]) -> FeatureVector:
        """Create FeatureVector from numpy array."""
        if len(arr) != FEATURE_COUNT:
            raise ValueError(f"Expected {FEATURE_COUNT} features, got {len(arr)}")
        return cls(
            D_box=float(arr[0]),
            D_r2=float(arr[1]),
            V_min=float(arr[2]),
            V_max=float(arr[3]),
            V_mean=float(arr[4]),
            V_std=float(arr[5]),
            V_skew=float(arr[6]),
            V_kurt=float(arr[7]),
            dV_mean=float(arr[8]),
            dV_max=float(arr[9]),
            T_stable=int(arr[10]),
            E_trend=float(arr[11]),
            f_active=float(arr[12]),
            N_clusters_low=int(arr[13]),
            N_clusters_med=int(arr[14]),
            N_clusters_high=int(arr[15]),
            max_cluster_size=int(arr[16]),
            cluster_size_std=float(arr[17]),
        )


def _box_counting_dimension(
    binary_field: NDArray[np.bool_],
    min_box_size: int,
    max_box_size: int | None,
    num_scales: int,
) -> tuple[float, float]:
    """
    Compute box-counting fractal dimension.

    Parameters
    ----------
    binary_field : NDArray[bool]
        Binary 2D field.
    min_box_size : int
        Minimum box size.
    max_box_size : int | None
        Maximum box size (None = N // 2).
    num_scales : int
        Number of scales.

    Returns
    -------
    tuple[float, float]
        (D, R²) - dimension and regression quality.
    """
    if binary_field.ndim != 2 or binary_field.shape[0] != binary_field.shape[1]:
        raise ValueError("binary_field must be a square 2D array")

    n = binary_field.shape[0]

    # Determine max box size
    if max_box_size is None:
        max_box_size = min_box_size * (2 ** (num_scales - 1))
        max_box_size = min(max_box_size, n // 2 if n >= 4 else n)

    if max_box_size < min_box_size:
        max_box_size = min_box_size

    # Generate scale sizes
    sizes = np.geomspace(min_box_size, max_box_size, num_scales).astype(int)
    sizes = np.unique(sizes)

    counts: list[int] = []
    valid_sizes: list[int] = []

    for size in sizes:
        if size <= 0:
            continue
        n_boxes = n // size
        if n_boxes == 0:
            continue

        # Reshape and count occupied boxes
        truncated = binary_field[: n_boxes * size, : n_boxes * size]
        reshaped = truncated.reshape(n_boxes, size, n_boxes, size)
        occupied = reshaped.any(axis=(1, 3))
        count = int(occupied.sum())

        if count > 0:
            counts.append(count)
            valid_sizes.append(size)

    # Need at least 2 points for regression
    if len(counts) < 2:
        return 0.0, 0.0

    # Linear regression: ln(N) = D * ln(1/ε) + c
    sizes_arr = np.array(valid_sizes, dtype=np.float64)
    counts_arr = np.array(counts, dtype=np.float64)

    inv_eps = 1.0 / sizes_arr
    log_inv_eps = np.log(inv_eps)
    log_counts = np.log(counts_arr)

    # Fit line
    coeffs = np.polyfit(log_inv_eps, log_counts, 1)
    fractal_dim = float(coeffs[0])

    # Compute R²
    predicted = np.polyval(coeffs, log_inv_eps)
    ss_res = np.sum((log_counts - predicted) ** 2)
    ss_tot = np.sum((log_counts - np.mean(log_counts)) ** 2)
    r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    # Clamp R² to [0, 1]
    r_squared = max(0.0, min(1.0, r_squared))

    return fractal_dim, r_squared


def compute_fractal_features(
    field: NDArray[np.floating],
    config: FeatureConfig,
) -> tuple[float, float]:
    """
    Compute fractal features (D_box, D_r2).

    Parameters
    ----------
    field : NDArray
        2D field in Volts.
    config : FeatureConfig
        Feature configuration.

    Returns
    -------
    tuple[float, float]
        (D_box, D_r2) - fractal dimension and R² quality.
    """
    # Convert to binary at -60mV threshold
    threshold_v = config.threshold_low_mv / 1000.0
    binary = field > threshold_v

    return _box_counting_dimension(
        binary,
        config.min_box_size,
        config.max_box_size,
        config.num_scales,
    )


def compute_basic_stats(
    field: NDArray[np.floating],
) -> tuple[float, float, float, float, float, float]:
    """
    Compute basic field statistics.

    Parameters
    ----------
    field : NDArray
        2D field in Volts.

    Returns
    -------
    tuple[float, ...]
        (V_min, V_max, V_mean, V_std, V_skew, V_kurt) in mV.
    """
    # Convert to mV
    field_mv = field * 1000.0

    V_min = float(np.min(field_mv))
    V_max = float(np.max(field_mv))
    V_mean = float(np.mean(field_mv))
    V_std = float(np.std(field_mv))

    # Skewness and kurtosis (Fisher's definition)
    if V_std > 1e-10:
        centered = field_mv - V_mean
        m3 = float(np.mean(centered**3))
        m4 = float(np.mean(centered**4))
        V_skew = m3 / (V_std**3)
        V_kurt = (m4 / (V_std**4)) - 3.0  # Excess kurtosis
    else:
        V_skew = 0.0
        V_kurt = 0.0

    return V_min, V_max, V_mean, V_std, V_skew, V_kurt


def compute_temporal_features(
    history: NDArray[np.floating],
    config: FeatureConfig,
) -> tuple[float, float, int, float]:
    """
    Compute temporal dynamics features.

    Parameters
    ----------
    history : NDArray
        Field history of shape (T, N, N) in Volts.
    config : FeatureConfig
        Feature configuration.

    Returns
    -------
    tuple[float, float, int, float]
        (dV_mean, dV_max, T_stable, E_trend).
    """
    T = len(history)
    if T < 2:
        return 0.0, 0.0, 0, 0.0

    # Convert to mV
    history_mv = history * 1000.0

    # Compute differences
    diffs = np.abs(history_mv[1:] - history_mv[:-1])

    # Mean and max rate of change
    dV_mean = float(np.mean(diffs))
    dV_max = float(np.max(diffs))

    # Steps to quasi-stationary
    threshold = config.stability_threshold_mv
    window = config.stability_window
    # Default to 0 to indicate stability was not reached during the windowed scan
    T_stable = 0

    if window <= T:
        # Compute rolling std of diffs
        diff_stds = [float(np.std(d)) for d in diffs]
        consecutive = 0
        for t, std_val in enumerate(diff_stds):
            if std_val < threshold:
                consecutive += 1
                if consecutive >= window:
                    T_stable = t - window + 2  # First stable step
                    break
            else:
                consecutive = 0

        # If no stable window was found in a sufficiently long sequence,
        # report the full duration to signal "not stabilized" rather than 0.
        if T_stable == 0:
            T_stable = T

    # Energy trend (L2 norm over time)
    energies = np.array([float(np.sum(h**2)) for h in history_mv])
    times = np.arange(T, dtype=np.float64)

    if T >= 2:
        coeffs = np.polyfit(times, energies, 1)
        E_trend = float(coeffs[0])  # Slope
    else:
        E_trend = 0.0

    return dV_mean, dV_max, T_stable, E_trend


def _count_clusters_4conn(
    binary: NDArray[np.bool_],
) -> tuple[int, list[int]]:
    """
    Count connected components using 4-connectivity.

    Uses efficient union-find algorithm.

    Parameters
    ----------
    binary : NDArray[bool]
        Binary 2D field.

    Returns
    -------
    tuple[int, list[int]]
        (cluster_count, list of cluster sizes).
    """
    n, m = binary.shape

    # Union-find data structures
    parent = np.arange(n * m, dtype=np.int32)
    rank = np.zeros(n * m, dtype=np.int32)

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        # Path compression
        while parent[x] != root:
            next_x = parent[x]
            parent[x] = root
            x = next_x
        return root

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]:
                rank[rx] += 1

    # Build union-find for active cells
    for i in range(n):
        for j in range(m):
            if not binary[i, j]:
                continue
            idx = i * m + j
            # Check right neighbor
            if j + 1 < m and binary[i, j + 1]:
                union(idx, idx + 1)
            # Check down neighbor
            if i + 1 < n and binary[i + 1, j]:
                union(idx, idx + m)

    # Count unique clusters and their sizes
    cluster_ids: dict[int, int] = {}
    sizes: list[int] = []

    for i in range(n):
        for j in range(m):
            if not binary[i, j]:
                continue
            idx = i * m + j
            root = find(idx)
            if root not in cluster_ids:
                cluster_ids[root] = len(sizes)
                sizes.append(0)
            sizes[cluster_ids[root]] += 1

    return len(sizes), sizes


def _count_clusters_8conn(
    binary: NDArray[np.bool_],
) -> tuple[int, list[int]]:
    """
    Count connected components using 8-connectivity.

    Parameters
    ----------
    binary : NDArray[bool]
        Binary 2D field.

    Returns
    -------
    tuple[int, list[int]]
        (cluster_count, list of cluster sizes).
    """
    n, m = binary.shape

    parent = np.arange(n * m, dtype=np.int32)
    rank = np.zeros(n * m, dtype=np.int32)

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            next_x = parent[x]
            parent[x] = root
            x = next_x
        return root

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            if rank[rx] == rank[ry]:
                rank[rx] += 1

    # 8-connectivity neighbors
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for i in range(n):
        for j in range(m):
            if not binary[i, j]:
                continue
            idx = i * m + j
            for di, dj in neighbors:
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m and binary[ni, nj]:
                    union(idx, ni * m + nj)

    cluster_ids: dict[int, int] = {}
    sizes: list[int] = []

    for i in range(n):
        for j in range(m):
            if not binary[i, j]:
                continue
            idx = i * m + j
            root = find(idx)
            if root not in cluster_ids:
                cluster_ids[root] = len(sizes)
                sizes.append(0)
            sizes[cluster_ids[root]] += 1

    return len(sizes), sizes


def compute_structural_features(
    field: NDArray[np.floating],
    config: FeatureConfig,
) -> tuple[float, int, int, int, int, float]:
    """
    Compute structural features.

    Parameters
    ----------
    field : NDArray
        2D field in Volts.
    config : FeatureConfig
        Feature configuration.

    Returns
    -------
    tuple
        (f_active, N_clusters_low, N_clusters_med, N_clusters_high,
         max_cluster_size, cluster_size_std).
    """
    # Thresholds in Volts
    thresh_low = config.threshold_low_mv / 1000.0
    thresh_med = config.threshold_med_mv / 1000.0
    thresh_high = config.threshold_high_mv / 1000.0

    # Binary masks
    binary_low = field > thresh_low
    binary_med = field > thresh_med
    binary_high = field > thresh_high

    # Active fraction at low threshold
    f_active = float(np.mean(binary_low))

    # Cluster detection function
    count_fn = _count_clusters_4conn if config.connectivity == 4 else _count_clusters_8conn

    # Cluster counts at each threshold
    n_low, sizes_low = count_fn(binary_low)
    n_med, _ = count_fn(binary_med)
    n_high, _ = count_fn(binary_high)

    # Max cluster size and std (from low threshold)
    if sizes_low:
        max_cluster = max(sizes_low)
        cluster_std = float(np.std(sizes_low)) if len(sizes_low) > 1 else 0.0
    else:
        max_cluster = 0
        cluster_std = 0.0

    return f_active, n_low, n_med, n_high, max_cluster, cluster_std


def compute_features(
    field_snapshots: NDArray[np.floating],
    config: FeatureConfig | None = None,
) -> FeatureVector:
    """
    Compute all features from field snapshots.

    Parameters
    ----------
    field_snapshots : NDArray
        Field data in Volts.
        Shape (N, N) for single snapshot or (T, N, N) for history.
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
    if config is None:
        config = FeatureConfig()

    # Handle input shape
    if field_snapshots.ndim == 2:
        # Single snapshot
        field = field_snapshots
        history = field_snapshots.reshape(1, *field_snapshots.shape)
    elif field_snapshots.ndim == 3:
        # History (T, N, N)
        history = field_snapshots
        if history.shape[0] == 0:
            raise ValueError("field_snapshots history must contain at least one snapshot")
        field = history[-1]  # Use final state for static features
    else:
        raise ValueError(
            f"field_snapshots must be 2D (N,N) or 3D (T,N,N), got {field_snapshots.ndim}D"
        )

    # Validate square grid
    if field.shape[0] != field.shape[1]:
        raise ValueError(f"Field must be square, got shape {field.shape}")

    # Compute all feature groups
    D_box, D_r2 = compute_fractal_features(field, config)
    V_min, V_max, V_mean, V_std, V_skew, V_kurt = compute_basic_stats(field)
    dV_mean, dV_max, T_stable, E_trend = compute_temporal_features(history, config)
    f_active, n_low, n_med, n_high, max_cs, cs_std = compute_structural_features(field, config)

    return FeatureVector(
        D_box=D_box,
        D_r2=D_r2,
        V_min=V_min,
        V_max=V_max,
        V_mean=V_mean,
        V_std=V_std,
        V_skew=V_skew,
        V_kurt=V_kurt,
        dV_mean=dV_mean,
        dV_max=dV_max,
        T_stable=T_stable,
        E_trend=E_trend,
        f_active=f_active,
        N_clusters_low=n_low,
        N_clusters_med=n_med,
        N_clusters_high=n_high,
        max_cluster_size=max_cs,
        cluster_size_std=cs_std,
    )


def validate_feature_ranges(
    features: FeatureVector,
    strict: bool = False,
) -> list[str]:
    """
    Validate feature values against expected ranges.

    Parameters
    ----------
    features : FeatureVector
        Features to validate.
    strict : bool
        If True, use biological range for D_box.

    Returns
    -------
    list[str]
        List of warnings (empty if all valid).
    """
    warnings: list[str] = []

    # Dimension check
    dim_min = BIOLOGICAL_DIMENSION_MIN if strict else DIMENSION_MIN
    dim_max = BIOLOGICAL_DIMENSION_MAX if strict else DIMENSION_MAX
    if not (dim_min <= features.D_box <= dim_max):
        warnings.append(f"D_box={features.D_box:.3f} outside [{dim_min}, {dim_max}]")

    # R² check
    if not (0.0 <= features.D_r2 <= 1.0):
        warnings.append(f"D_r2={features.D_r2:.3f} outside [0, 1]")

    # Voltage range check
    if features.V_min < -100 or features.V_max > 50:
        warnings.append(
            f"V range [{features.V_min:.1f}, {features.V_max:.1f}] mV exceeds "
            "physiological bounds [-100, 50]"
        )

    # Active fraction check
    if not (0.0 <= features.f_active <= 1.0):
        warnings.append(f"f_active={features.f_active:.3f} outside [0, 1]")

    # Check for NaN/Inf
    arr = features.to_array()
    if np.any(np.isnan(arr)):
        warnings.append("NaN detected in features")
    if np.any(np.isinf(arr)):
        warnings.append("Inf detected in features")

    return warnings
