"""
Fractal Growth Engine — IFS and Box-Counting Analysis.

Implements stable numerical methods for fractal generation and analysis:
- Iterated Function System (IFS) with contractive mappings
- Box-counting dimension estimation
- Lyapunov exponent computation for stability analysis

Reference: MFN_MATH_MODEL.md Section 3 (Fractal Growth and Dimension Analysis)

Equations Implemented:
    IFS transformation: [x', y'] = [[a,b],[c,d]] * [x,y] + [e,f]

    Contraction requirement: |ad - bc| < 1

    Lyapunov exponent: λ = (1/n) * Σ ln|det(J_k)|

    Box-counting dimension: D = lim(ε→0) ln(N(ε)) / ln(1/ε)

Parameters (from MFN_MATH_MODEL.md Section 3.5):
    Scale factor s ∈ [0.2, 0.5]    - Contraction strength
    Rotation θ ∈ [0, 2π]          - Transformation angle
    Translation e,f ∈ [-1, 1]     - Pattern offset
    Number of transforms: 4       - IFS complexity
    Number of points: 10000       - Resolution
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .exceptions import NumericalInstabilityError, StabilityError, ValueOutOfRangeError

if TYPE_CHECKING:
    from numpy.typing import NDArray

# === Default Parameters (from MFN_MATH_MODEL.md Section 3.5) ===
DEFAULT_NUM_POINTS: int = 10000
DEFAULT_NUM_TRANSFORMS: int = 4
DEFAULT_SCALE_MIN: float = 0.2
DEFAULT_SCALE_MAX: float = 0.5
DEFAULT_TRANSLATION_RANGE: float = 1.0

# === Box-counting defaults ===
DEFAULT_MIN_BOX_SIZE: int = 2
DEFAULT_NUM_SCALES: int = 5

# === Biophysical Parameter Bounds (from MFN_MATH_MODEL.md Section 3.5) ===
# IFS point count bounds
NUM_POINTS_MIN: int = 1000  # Minimum for meaningful fractal structure
NUM_POINTS_MAX: int = 100000  # Upper limit for computational feasibility

# Number of transforms bounds
NUM_TRANSFORMS_MIN: int = 2  # Minimum for interesting patterns
NUM_TRANSFORMS_MAX: int = 8  # Upper limit for complexity

# Scale factor bounds (contraction requirement)
SCALE_MIN_BOUND: float = 0.0  # Must be > 0 (exclusive)
SCALE_MAX_BOUND: float = 1.0  # Must be < 1 for contraction (exclusive)

# Translation bounds
TRANSLATION_RANGE_MAX: float = 2.0  # e, f ∈ [-2, 2] per MFN_MATH_MODEL.md

# Box-counting bounds
MIN_BOX_SIZE_BOUND: int = 1  # Minimum sensible box size
NUM_SCALES_MIN: int = 3  # Minimum for reliable regression
NUM_SCALES_MAX: int = 10  # Upper limit for log-regression points

# === Expected ranges (from MFN_MATH_MODEL.md) ===
# Lyapunov should be negative for stable (contractive) IFS
LYAPUNOV_STABLE_MAX: float = 0.0
EXPECTED_LYAPUNOV_MEAN: float = -2.1  # Approximate expected value

# Fractal dimension bounds
FRACTAL_DIM_MIN: float = 0.0
FRACTAL_DIM_MAX: float = 2.0
BIOLOGICAL_DIM_MIN: float = 1.4  # Mycelium networks (empirical)
BIOLOGICAL_DIM_MAX: float = 1.9  # Mycelium networks (empirical)


@dataclass
class FractalConfig:
    """
    Configuration for fractal growth engine.

    All parameters have defaults from MFN_MATH_MODEL.md.

    Attributes
    ----------
    num_points : int
        Number of IFS points to generate. Default 10000.
        Valid range: 1000-100000.
    num_transforms : int
        Number of affine transformations in IFS. Default 4.
        Valid range: 2-8.
    scale_min : float
        Minimum contraction scale factor. Default 0.2.
        Must be > 0 and < 1 for contraction.
    scale_max : float
        Maximum contraction scale factor. Default 0.5.
        Must be < 1 for contraction.
    translation_range : float
        Range for translation parameters e, f ∈ [-range, +range].
        Default 1.0.
    min_box_size : int
        Minimum box size for box-counting. Default 2.
    max_box_size : int | None
        Maximum box size. Default None (auto: grid_size/2).
    num_scales : int
        Number of scales for dimension estimation. Default 5.
        Valid range: 3-10.
    check_stability : bool
        Check for NaN/Inf and stability. Default True.
    random_seed : int | None
        Seed for reproducibility. Default None.
    """

    num_points: int = DEFAULT_NUM_POINTS
    num_transforms: int = DEFAULT_NUM_TRANSFORMS
    scale_min: float = DEFAULT_SCALE_MIN
    scale_max: float = DEFAULT_SCALE_MAX
    translation_range: float = DEFAULT_TRANSLATION_RANGE
    min_box_size: int = DEFAULT_MIN_BOX_SIZE
    max_box_size: int | None = None
    num_scales: int = DEFAULT_NUM_SCALES
    check_stability: bool = True
    random_seed: int | None = None

    def __post_init__(self) -> None:
        """Validate configuration parameters against biophysical constraints.

        Invariants enforced:
        - num_points: [1000, 100000] for meaningful fractal structure
        - num_transforms: [2, 8] for interesting patterns
        - scale factors: (0, 1) for contraction (IFS stability)
        - translation_range: <= 2.0
        - num_scales: [3, 10] for reliable dimension estimation
        """
        # Point count validation with biophysical bounds
        if not (NUM_POINTS_MIN <= self.num_points <= NUM_POINTS_MAX):
            raise ValueOutOfRangeError(
                f"num_points must be in [{NUM_POINTS_MIN}, {NUM_POINTS_MAX}] "
                "for meaningful fractal structure",
                value=float(self.num_points),
                min_bound=float(NUM_POINTS_MIN),
                max_bound=float(NUM_POINTS_MAX),
                parameter_name="num_points",
            )

        # Transform count validation with biophysical bounds
        if not (NUM_TRANSFORMS_MIN <= self.num_transforms <= NUM_TRANSFORMS_MAX):
            raise ValueOutOfRangeError(
                f"num_transforms must be in [{NUM_TRANSFORMS_MIN}, {NUM_TRANSFORMS_MAX}] "
                "for interesting patterns",
                value=float(self.num_transforms),
                min_bound=float(NUM_TRANSFORMS_MIN),
                max_bound=float(NUM_TRANSFORMS_MAX),
                parameter_name="num_transforms",
            )

        # Scale factor validation (contraction requirement)
        if self.scale_min <= SCALE_MIN_BOUND:
            raise ValueOutOfRangeError(
                "Minimum scale must be positive (> 0)",
                value=self.scale_min,
                min_bound=SCALE_MIN_BOUND,
                parameter_name="scale_min",
            )
        if self.scale_max >= SCALE_MAX_BOUND:
            raise StabilityError(
                "Maximum scale must be < 1 for contractive IFS. "
                f"scale_max={self.scale_max} would cause divergence."
            )
        if self.scale_min > self.scale_max:
            raise ValueOutOfRangeError(
                "scale_min must be <= scale_max",
                parameter_name="scale_min",
            )

        # Translation range validation
        if self.translation_range < 0:
            raise ValueOutOfRangeError(
                "translation_range must be non-negative",
                value=self.translation_range,
                min_bound=0.0,
                parameter_name="translation_range",
            )
        if self.translation_range > TRANSLATION_RANGE_MAX:
            raise ValueOutOfRangeError(
                f"translation_range must be <= {TRANSLATION_RANGE_MAX}",
                value=self.translation_range,
                max_bound=TRANSLATION_RANGE_MAX,
                parameter_name="translation_range",
            )

        # Box-counting validation with biophysical bounds
        if self.min_box_size < MIN_BOX_SIZE_BOUND:
            raise ValueOutOfRangeError(
                f"min_box_size must be >= {MIN_BOX_SIZE_BOUND}",
                value=float(self.min_box_size),
                min_bound=float(MIN_BOX_SIZE_BOUND),
                parameter_name="min_box_size",
            )
        if not (NUM_SCALES_MIN <= self.num_scales <= NUM_SCALES_MAX):
            raise ValueOutOfRangeError(
                f"num_scales must be in [{NUM_SCALES_MIN}, {NUM_SCALES_MAX}] "
                "for reliable dimension estimation",
                value=float(self.num_scales),
                min_bound=float(NUM_SCALES_MIN),
                max_bound=float(NUM_SCALES_MAX),
                parameter_name="num_scales",
            )


@dataclass
class FractalMetrics:
    """
    Metrics collected during fractal generation and analysis.

    Attributes
    ----------
    lyapunov_exponent : float
        Lyapunov exponent (negative = stable).
    fractal_dimension : float
        Box-counting dimension estimate.
    points_generated : int
        Number of IFS points generated.
    points_bounded : bool
        Whether all points are within reasonable bounds.
    max_point_distance : float
        Maximum distance from origin in point cloud.
    nan_detected : bool
        Whether NaN was detected.
    inf_detected : bool
        Whether Inf was detected.
    is_contractive : bool
        Whether IFS is confirmed contractive (λ < 0).
    dimension_r_squared : float
        R² of box-counting regression.
    """

    lyapunov_exponent: float = 0.0
    fractal_dimension: float = 0.0
    points_generated: int = 0
    points_bounded: bool = True
    max_point_distance: float = 0.0
    nan_detected: bool = False
    inf_detected: bool = False
    is_contractive: bool = False
    dimension_r_squared: float = 0.0


class FractalGrowthEngine:
    """
    Engine for fractal generation and analysis with stability guarantees.

    Implements IFS fractals with contractive mappings and
    box-counting dimension estimation.

    Reference: MFN_MATH_MODEL.md Section 3

    Example
    -------
    >>> config = FractalConfig(num_points=10000, random_seed=42)
    >>> engine = FractalGrowthEngine(config)
    >>> points, lyap = engine.generate_ifs()
    >>> print(f"Lyapunov = {lyap:.3f}")  # Expected: ~-2.1 (stable)

    >>> # Estimate fractal dimension from binary field
    >>> binary = np.random.random((64, 64)) > 0.5
    >>> dim = engine.estimate_dimension(binary)
    >>> print(f"Dimension = {dim:.3f}")
    """

    def __init__(self, config: FractalConfig | None = None) -> None:
        """
        Initialize fractal growth engine.

        Parameters
        ----------
        config : FractalConfig | None
            Engine configuration. If None, uses defaults.
        """
        self.config = config or FractalConfig()
        self._metrics = FractalMetrics()
        self._rng = np.random.default_rng(self.config.random_seed)

        # Store generated transforms for reproducibility
        self._transforms: list[tuple[float, ...]] | None = None

    @property
    def metrics(self) -> FractalMetrics:
        """Get current metrics."""
        return self._metrics

    @property
    def transforms(self) -> list[tuple[float, ...]] | None:
        """Get stored IFS transforms."""
        return self._transforms

    def reset(self) -> None:
        """Reset engine state and metrics."""
        self._metrics = FractalMetrics()
        self._transforms = None
        self._rng = np.random.default_rng(self.config.random_seed)

    def generate_ifs(
        self,
        num_points: int | None = None,
        num_transforms: int | None = None,
    ) -> tuple[NDArray[np.floating], float]:
        """
        Generate fractal pattern using Iterated Function System.

        Uses affine transformations with random contractive mappings.
        Computes Lyapunov exponent to verify stability.

        Reference: MFN_MATH_MODEL.md Section 3.2

        Parameters
        ----------
        num_points : int | None
            Override config num_points.
        num_transforms : int | None
            Override config num_transforms.

        Returns
        -------
        tuple[NDArray, float]
            Points array of shape (num_points, 2) and Lyapunov exponent.

        Raises
        ------
        NumericalInstabilityError
            If NaN/Inf values are generated.
        StabilityError
            If Lyapunov exponent indicates instability.
        """
        self.reset()

        n_points = self.config.num_points if num_points is None else num_points
        n_transforms = self.config.num_transforms if num_transforms is None else num_transforms

        if not (NUM_POINTS_MIN <= n_points <= NUM_POINTS_MAX):
            raise ValueOutOfRangeError(
                (
                    "num_points must be in "
                    f"[{NUM_POINTS_MIN}, {NUM_POINTS_MAX}] for meaningful fractal structure"
                ),
                value=float(n_points),
                min_bound=float(NUM_POINTS_MIN),
                max_bound=float(NUM_POINTS_MAX),
                parameter_name="num_points",
            )
        if not (NUM_TRANSFORMS_MIN <= n_transforms <= NUM_TRANSFORMS_MAX):
            raise ValueOutOfRangeError(
                (
                    "num_transforms must be in "
                    f"[{NUM_TRANSFORMS_MIN}, {NUM_TRANSFORMS_MAX}] for interesting patterns"
                ),
                value=float(n_transforms),
                min_bound=float(NUM_TRANSFORMS_MIN),
                max_bound=float(NUM_TRANSFORMS_MAX),
                parameter_name="num_transforms",
            )

        # Generate random contractive affine transformations
        scales = self._rng.uniform(self.config.scale_min, self.config.scale_max, size=n_transforms)
        angles = self._rng.uniform(0, 2 * np.pi, size=n_transforms)
        translations = self._rng.uniform(
            -self.config.translation_range,
            self.config.translation_range,
            size=(n_transforms, 2),
        )

        cos_angles = np.cos(angles)
        sin_angles = np.sin(angles)

        # Vectorize RNG draws and determinant accumulation to reduce Python overhead
        transforms_arr = np.column_stack(
            (
                scales * cos_angles,
                -scales * sin_angles,
                scales * sin_angles,
                scales * cos_angles,
                translations[:, 0],
                translations[:, 1],
            )
        )

        self._transforms = [tuple(map(float, row)) for row in transforms_arr]
        a, b, c, d, e, f = transforms_arr.T

        indices = self._rng.integers(0, n_transforms, size=n_points)
        points = np.empty((n_points, 2), dtype=np.float64)
        x, y = 0.0, 0.0

        det_values = np.abs(a * d - b * c)
        log_det = np.where(det_values > 1e-10, np.log(det_values), 0.0)
        log_jacobian_sum = float(np.sum(log_det[indices]))

        # Convert tiny transform arrays to Python lists for faster scalar
        # arithmetic under tracemalloc instrumentation.
        a_list = a.tolist()
        b_list = b.tolist()
        c_list = c.tolist()
        d_list = d.tolist()
        e_list = e.tolist()
        f_list = f.tolist()
        indices_list = indices.tolist()

        x_out = points[:, 0]
        y_out = points[:, 1]

        for i, idx in enumerate(indices_list):
            x_new = a_list[idx] * x + b_list[idx] * y + e_list[idx]
            y_new = c_list[idx] * x + d_list[idx] * y + f_list[idx]
            x, y = x_new, y_new
            x_out[i] = x
            y_out[i] = y

        # Lyapunov exponent (average log contraction)
        lyapunov = log_jacobian_sum / n_points

        # Update metrics
        self._metrics.lyapunov_exponent = float(lyapunov)
        self._metrics.points_generated = n_points
        self._metrics.is_contractive = lyapunov < LYAPUNOV_STABLE_MAX

        # Check for NaN/Inf
        if self.config.check_stability:
            nan_count = int(np.sum(np.isnan(points)))
            inf_count = int(np.sum(np.isinf(points)))

            if nan_count > 0:
                self._metrics.nan_detected = True
                raise NumericalInstabilityError(
                    "NaN values in IFS points",
                    field_name="points",
                    nan_count=nan_count,
                )
            if inf_count > 0:
                self._metrics.inf_detected = True
                raise NumericalInstabilityError(
                    "Inf values in IFS points",
                    field_name="points",
                    inf_count=inf_count,
                )

        # Check boundedness
        max_dist = float(np.max(np.abs(points)))
        self._metrics.max_point_distance = max_dist
        self._metrics.points_bounded = max_dist < 100  # Reasonable bound for attractor

        if not self._metrics.points_bounded and self.config.check_stability:
            raise StabilityError(
                f"IFS points unbounded (max distance = {max_dist:.2f}). "
                "This indicates non-contractive dynamics.",
                value=max_dist,
            )

        return points, float(lyapunov)

    def estimate_dimension(
        self,
        binary_field: NDArray[np.bool_],
        min_box_size: int | None = None,
        max_box_size: int | None = None,
        num_scales: int | None = None,
    ) -> float:
        """
        Estimate fractal dimension using box-counting method.

        Reference: MFN_MATH_MODEL.md Section 3.4

        D = lim(ε→0) ln(N(ε)) / ln(1/ε)

        Parameters
        ----------
        binary_field : NDArray[bool]
            Binary pattern of shape (N, N).
        min_box_size : int | None
            Override config min_box_size.
        max_box_size : int | None
            Override config max_box_size.
        num_scales : int | None
            Override config num_scales.

        Returns
        -------
        float
            Estimated fractal dimension.

        Raises
        ------
        ValueError
            If binary_field is not a square 2D array.
        """
        if binary_field.ndim != 2:
            raise ValueError(f"binary_field must be 2D, got {binary_field.ndim}D")
        if binary_field.shape[0] != binary_field.shape[1]:
            raise ValueError(f"binary_field must be square, got {binary_field.shape}")

        n = binary_field.shape[0]

        if min_box_size is None:
            min_box = self.config.min_box_size
        else:
            min_box = int(min_box_size)
            if min_box < MIN_BOX_SIZE_BOUND:
                raise ValueOutOfRangeError(
                    f"min_box_size must be >= {MIN_BOX_SIZE_BOUND}",
                    value=float(min_box),
                    min_bound=float(MIN_BOX_SIZE_BOUND),
                    parameter_name="min_box_size",
                )

        if num_scales is None:
            scales = self.config.num_scales
        else:
            scales = int(num_scales)
            if not (NUM_SCALES_MIN <= scales <= NUM_SCALES_MAX):
                raise ValueOutOfRangeError(
                    f"num_scales must be in [{NUM_SCALES_MIN}, {NUM_SCALES_MAX}]",
                    value=float(scales),
                    min_bound=float(NUM_SCALES_MIN),
                    max_bound=float(NUM_SCALES_MAX),
                    parameter_name="num_scales",
                )

        # Determine max box size
        if max_box_size is not None:
            max_box = max_box_size
        elif self.config.max_box_size is not None:
            max_box = self.config.max_box_size
        else:
            max_box = min_box * (2 ** (scales - 1))
            max_box = min(max_box, n // 2 if n >= 4 else n)

        if max_box < min_box:
            max_box = min_box

        # Generate scale sizes (geometric spacing)
        sizes = np.geomspace(min_box, max_box, scales).astype(int)
        sizes = np.unique(sizes)

        counts: list[int] = []
        valid_sizes: list[int] = []

        for size in sizes:
            if size <= 0:
                continue
            n_boxes = n // size
            if n_boxes == 0:
                continue

            # Reshape field into boxes and count occupied
            truncated = binary_field[: n_boxes * size, : n_boxes * size]
            reshaped = truncated.reshape(n_boxes, size, n_boxes, size)
            occupied = reshaped.any(axis=(1, 3))
            count = int(occupied.sum())

            if count > 0:
                counts.append(count)
                valid_sizes.append(size)

        # Need at least 2 points for regression
        if len(counts) < 2:
            self._metrics.fractal_dimension = 0.0
            self._metrics.dimension_r_squared = 0.0
            return 0.0

        # Linear regression: ln(N) = D * ln(1/ε) + c
        sizes_arr = np.array(valid_sizes, dtype=float)
        counts_arr = np.array(counts, dtype=float)

        inv_eps = 1.0 / sizes_arr
        log_inv_eps = np.log(inv_eps)
        log_counts = np.log(counts_arr)

        # Fit line and compute R²
        coeffs = np.polyfit(log_inv_eps, log_counts, 1)
        fractal_dim = float(coeffs[0])

        # Compute R² for quality metric
        predicted = np.polyval(coeffs, log_inv_eps)
        ss_res = np.sum((log_counts - predicted) ** 2)
        ss_tot = np.sum((log_counts - np.mean(log_counts)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        self._metrics.fractal_dimension = fractal_dim
        self._metrics.dimension_r_squared = float(r_squared)

        return fractal_dim

    def compute_lyapunov_from_history(
        self,
        field_history: NDArray[np.floating],
        dt: float = 1.0,
    ) -> float:
        """
        Compute Lyapunov exponent from field evolution history.

        Measures exponential divergence/convergence of trajectories.

        Reference: MFN_MATH_MODEL.md Section 3.3

        Parameters
        ----------
        field_history : NDArray
            Array of shape (T, N, N) with field states over time.
        dt : float
            Time step between states.

        Returns
        -------
        float
            Estimated Lyapunov exponent.
        """
        if len(field_history) < 2:
            return 0.0

        T = len(field_history)
        log_divergence = 0.0
        count = 0

        for t in range(1, T):
            diff = np.abs(field_history[t] - field_history[t - 1])
            norm_diff = np.sqrt(np.sum(diff**2))
            if norm_diff > 1e-10:
                log_divergence += np.log(norm_diff)
                count += 1

        if count == 0:
            return 0.0

        lyapunov = log_divergence / (count * dt)
        self._metrics.lyapunov_exponent = float(lyapunov)

        return float(lyapunov)

    def validate_contraction(self) -> bool:
        """
        Validate that stored transforms satisfy contraction requirement.

        Reference: MFN_MATH_MODEL.md Section 3.2
        Contraction requirement: |ad - bc| < 1

        Returns
        -------
        bool
            True if all transforms are contractive.
        """
        if self._transforms is None:
            return False

        for a, b, c, d, _e, _f in self._transforms:
            det = abs(a * d - b * c)
            if det >= 1.0:
                return False

        return True

    def validate_dimension_range(
        self,
        dimension: float,
        biological: bool = False,
    ) -> bool:
        """
        Validate that dimension is within expected range.

        Reference: MFN_MATH_MODEL.md Section 3.6

        Parameters
        ----------
        dimension : float
            Fractal dimension to validate.
        biological : bool
            If True, use biological mycelium range [1.4, 1.9].
            If False, use general 2D bounds [0, 2].

        Returns
        -------
        bool
            True if dimension is within range.
        """
        if biological:
            return BIOLOGICAL_DIM_MIN <= dimension <= BIOLOGICAL_DIM_MAX
        else:
            return FRACTAL_DIM_MIN <= dimension <= FRACTAL_DIM_MAX
