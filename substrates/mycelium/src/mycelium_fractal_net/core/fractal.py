"""
Fractal Analysis Module.

This module provides the public API for fractal dimension estimation and
IFS fractal generation, re-exporting validated implementations for
backward compatibility, plus the new FractalGrowthEngine for advanced use.

Conceptual domain: Fractal geometry, box-counting dimension

Reference:
    - docs/MFN_MATH_MODEL.md Section 3 (Fractal Growth and Dimension)
    - docs/ARCHITECTURE.md Section 3 (Fractal Analysis)
    - docs/MFN_FEATURE_SCHEMA.md (D_box feature)

Mathematical Model:
    Box-counting dimension:
        D = lim(ε→0) ln(N(ε)) / ln(1/ε)

    IFS transformation:
        [x', y'] = [[a,b],[c,d]] * [x,y] + [e,f]

    Contraction requirement: |ad - bc| < 1

Expected ranges:
    D ∈ [1.4, 1.9] for biological mycelium patterns
    D ≈ 1.585 for Sierpinski triangle (exact)

Example:
    >>> from mycelium_fractal_net.core.fractal import estimate_fractal_dimension
    >>> import numpy as np
    >>> binary = np.random.default_rng(42).random((64, 64)) > 0.5
    >>> D = estimate_fractal_dimension(binary)
    >>> 1.0 < D < 2.5
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from .fractal_growth_engine import (
    DEFAULT_MIN_BOX_SIZE,
    DEFAULT_NUM_POINTS,
    DEFAULT_NUM_SCALES,
    DEFAULT_NUM_TRANSFORMS,
    DEFAULT_SCALE_MAX,
    DEFAULT_SCALE_MIN,
    DEFAULT_TRANSLATION_RANGE,
    FractalConfig,
    FractalGrowthEngine,
    FractalMetrics,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray


def estimate_fractal_dimension(
    binary_field: NDArray[Any],
    min_box_size: int = 2,
    max_box_size: int | None = None,
    num_scales: int = 5,
) -> float:
    """Box-counting estimation of fractal dimension for binary field.

    Empirically validated: D ~ 1.584 for stable mycelium patterns.
    """
    if binary_field.ndim != 2 or binary_field.shape[0] != binary_field.shape[1]:
        raise ValueError("binary_field must be a square 2D array.")
    if num_scales < 1:
        raise ValueError("num_scales must be >= 1.")

    n = binary_field.shape[0]
    if max_box_size is None:
        max_box_size = min_box_size * (2 ** (num_scales - 1))
        max_box_size = min(max_box_size, n // 2 if n >= 4 else n)

    if max_box_size < min_box_size:
        max_box_size = min_box_size

    sizes = np.geomspace(min_box_size, max_box_size, num_scales).astype(int)
    sizes = np.unique(sizes)
    counts: list[float] = []
    used_sizes: list[int] = []

    for size in sizes:
        if size <= 0:
            continue
        n_boxes = n // size
        if n_boxes == 0:
            continue
        reshaped = binary_field[: n_boxes * size, : n_boxes * size].reshape(
            n_boxes, size, n_boxes, size
        )
        occupied = reshaped.any(axis=(1, 3))
        counts.append(float(occupied.sum()))
        used_sizes.append(int(size))

    if not counts:
        return 0.0

    counts_arr = np.array(counts, dtype=float)
    valid = counts_arr > 0
    if valid.sum() < 2:
        return 0.0

    sizes_v = np.array(used_sizes, dtype=int)[valid]
    counts_arr = counts_arr[valid]

    inv_eps = 1.0 / sizes_v.astype(float)
    log_inv_eps = np.log(inv_eps)
    log_counts = np.log(counts_arr)

    coeffs = np.polyfit(log_inv_eps, log_counts, 1)
    return float(coeffs[0])


def generate_fractal_ifs(
    rng: np.random.Generator,
    num_points: int = 10000,
    num_transforms: int = 4,
) -> tuple[NDArray[Any], float]:
    """Generate fractal pattern using Iterated Function System (IFS)."""
    transforms = []
    for _ in range(num_transforms):
        scale = rng.uniform(0.2, 0.5)
        angle = rng.uniform(0, 2 * np.pi)
        a = scale * np.cos(angle)
        b = -scale * np.sin(angle)
        c = scale * np.sin(angle)
        d = scale * np.cos(angle)
        e = rng.uniform(-1, 1)
        f = rng.uniform(-1, 1)
        transforms.append((a, b, c, d, e, f))

    points = np.zeros((num_points, 2))
    x, y = 0.0, 0.0
    log_jacobian_sum = 0.0
    jacobian_count = 0

    for i in range(num_points):
        idx = rng.integers(0, num_transforms)
        a, b, c, d, e, f = transforms[idx]
        x_new = a * x + b * y + e
        y_new = c * x + d * y + f
        x, y = x_new, y_new
        points[i] = [x, y]

        det = abs(a * d - b * c)
        if det > 1e-10:
            log_jacobian_sum += np.log(det)
            jacobian_count += 1

    if jacobian_count == 0:
        return points, 0.0

    lyapunov = log_jacobian_sum / jacobian_count
    return points, lyapunov


__all__ = [
    "DEFAULT_MIN_BOX_SIZE",
    # Constants
    "DEFAULT_NUM_POINTS",
    "DEFAULT_NUM_SCALES",
    "DEFAULT_NUM_TRANSFORMS",
    "DEFAULT_SCALE_MAX",
    "DEFAULT_SCALE_MIN",
    "DEFAULT_TRANSLATION_RANGE",
    # Classes
    "FractalConfig",
    "FractalGrowthEngine",
    "FractalMetrics",
    # Functions
    "estimate_fractal_dimension",
    "generate_fractal_ifs",
]
