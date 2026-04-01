"""
Mathematical Constants and Utilities for MLSDM.

This module provides centralized mathematical constants and helper functions
to ensure numerical stability and consistency across the codebase.

Key features:
- Centralized epsilon values for different precision requirements
- Safe mathematical operations (divide, normalize, etc.) with NaN/inf handling
- Consistent validation helpers for numerical inputs
- Entropy calculation with improved numerical stability

Usage:
    from mlsdm.utils.math_constants import (
        EPSILON_NORM,
        EPSILON_DIV,
        safe_norm,
        safe_divide,
        safe_normalize,
        validate_finite,
    )

References:
    - IEEE 754 floating-point standard
    - Numerical Recipes in C (Press et al.)
"""

from __future__ import annotations

import math
from typing import overload

import numpy as np

# =============================================================================
# Centralized Epsilon Constants
# =============================================================================

# For normalization operations (avoiding zero-norm vectors)
# Value chosen to be well above float32 denormals while small enough to detect zero-ish vectors
EPSILON_NORM: float = 1e-9

# For division operations (avoiding division by zero)
# Same as EPSILON_NORM for consistency across operations
EPSILON_DIV: float = 1e-9

# For log operations (log(0) protection)
# Smaller value for log stability in entropy calculations
EPSILON_LOG: float = 1e-12

# For comparisons (relative tolerance)
EPSILON_REL: float = 1e-6

# For absolute tolerance in floating point comparisons
EPSILON_ABS: float = 1e-8


# =============================================================================
# Type Variables
# =============================================================================

# Note: Using overloads instead of TypeVar for better type inference


# =============================================================================
# Validation Helpers
# =============================================================================


def is_finite_scalar(value: float | int | None) -> bool:
    """Check if a scalar value is finite (not NaN, not inf, not None).

    Args:
        value: A scalar numeric value to check.

    Returns:
        True if the value is a finite number, False otherwise.

    Examples:
        >>> is_finite_scalar(1.0)
        True
        >>> is_finite_scalar(float('nan'))
        False
        >>> is_finite_scalar(None)
        False
    """
    if value is None:
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def is_finite_array(arr: np.ndarray) -> bool:
    """Check if all elements of a numpy array are finite.

    Args:
        arr: A numpy array to check.

    Returns:
        True if all elements are finite, False otherwise.

    Examples:
        >>> is_finite_array(np.array([1.0, 2.0, 3.0]))
        True
        >>> is_finite_array(np.array([1.0, np.nan, 3.0]))
        False
    """
    if not isinstance(arr, np.ndarray):
        return False
    return bool(np.all(np.isfinite(arr)))


@overload
def validate_finite(
    value: float,
    name: str = ...,
    default: float | None = ...,
) -> float: ...


@overload
def validate_finite(
    value: np.ndarray,
    name: str = ...,
    default: np.ndarray | None = ...,
) -> np.ndarray: ...


def validate_finite(
    value: float | np.ndarray,
    name: str = "value",
    default: float | np.ndarray | None = None,
) -> float | np.ndarray:
    """Validate that a value is finite, optionally returning a default.

    Args:
        value: The value to validate (scalar or array).
        name: Name of the value for error messages.
        default: Default value to return if validation fails (if provided).

    Returns:
        The original value if valid, or the default if provided and value invalid.

    Raises:
        ValueError: If value is not finite and no default is provided.

    Examples:
        >>> validate_finite(1.0, "x")
        1.0
        >>> validate_finite(float('nan'), "x", default=0.0)
        0.0
    """
    is_valid = is_finite_array(value) if isinstance(value, np.ndarray) else is_finite_scalar(value)

    if is_valid:
        return value

    if default is not None:
        return default

    raise ValueError(f"{name} must be finite, got {value}")


# =============================================================================
# Safe Mathematical Operations
# =============================================================================


def safe_norm(vector: np.ndarray) -> float:
    """Compute L2 norm safely, avoiding overflow for extreme magnitude vectors.

    Uses scaled norm computation to prevent overflow when vector elements
    have very large magnitudes (e.g., 1e30 or greater). This is particularly
    important when processing external input vectors that may have extreme values.

    The algorithm works by:
    1. Finding the maximum absolute value in the vector
    2. Scaling all elements by this maximum value
    3. Computing the norm of the scaled vector
    4. Scaling the result back up

    This ensures that intermediate squared values don't overflow, since
    (x/max)^2 will always be <= 1.0.

    Args:
        vector: Input numpy array of any dimension.

    Returns:
        L2 norm of the vector (always finite and non-negative).
        Returns 0.0 for zero vectors, inf for vectors containing inf.

    Examples:
        >>> safe_norm(np.array([3.0, 4.0]))
        5.0
        >>> safe_norm(np.array([1e30, 1e30]))  # No overflow
        1.4142135623730951e+30
        >>> safe_norm(np.array([0.0, 0.0]))
        0.0
    """
    if vector.size == 0:
        return 0.0

    # Find maximum absolute value for scaling
    max_abs = np.max(np.abs(vector))

    if max_abs == 0.0:
        return 0.0

    # Handle extreme cases where max_abs itself might be inf
    if not np.isfinite(max_abs):
        return float("inf")

    # Scale down to prevent overflow, compute norm, scale back up
    scaled_vec = vector / max_abs
    scaled_norm = np.sqrt(np.sum(scaled_vec * scaled_vec))

    return float(max_abs * scaled_norm)


@overload
def safe_divide(
    numerator: float,
    denominator: float,
    epsilon: float = ...,
) -> float: ...


@overload
def safe_divide(
    numerator: np.ndarray,
    denominator: np.ndarray,
    epsilon: float = ...,
) -> np.ndarray: ...


def safe_divide(
    numerator: float | np.ndarray,
    denominator: float | np.ndarray,
    epsilon: float = EPSILON_DIV,
) -> float | np.ndarray:
    """Safely divide numerator by denominator, avoiding division by zero.

    Args:
        numerator: The numerator (scalar or array).
        denominator: The denominator (scalar or array).
        epsilon: Small value to add to denominator to avoid div-by-zero.

    Returns:
        The result of numerator / (denominator + epsilon).

    Examples:
        >>> safe_divide(1.0, 0.0)
        1000000000.0
        >>> safe_divide(np.array([1.0, 2.0]), np.array([0.0, 1.0]))
        array([1.e+09, 2.e+00])
    """
    if isinstance(denominator, np.ndarray):
        # For arrays, use numpy's where for efficiency
        safe_denom = np.where(np.abs(denominator) < epsilon, epsilon, denominator)
        return numerator / safe_denom
    else:
        # For scalars - ensure we work with floats
        denom_float = float(denominator)
        safe_denom_scalar = denom_float if abs(denom_float) >= epsilon else epsilon
        return float(numerator) / safe_denom_scalar


def safe_normalize(
    vector: np.ndarray,
    epsilon: float = EPSILON_NORM,
) -> np.ndarray:
    """Safely normalize a vector to unit length, handling zero-norm and extreme vectors.

    Uses safe_norm internally to prevent overflow with extreme magnitude vectors.

    Args:
        vector: Input vector to normalize.
        epsilon: Minimum norm threshold; vectors with smaller norms
                are returned as-is to avoid numerical instability.

    Returns:
        Normalized vector (unit length) or original vector if norm < epsilon.

    Examples:
        >>> safe_normalize(np.array([3.0, 4.0]))
        array([0.6, 0.8])
        >>> safe_normalize(np.array([0.0, 0.0]))
        array([0., 0.])
    """
    norm = safe_norm(vector)
    if norm < epsilon:
        return vector
    return vector / norm


@overload
def safe_log(
    value: float,
    epsilon: float = ...,
) -> float: ...


@overload
def safe_log(
    value: np.ndarray,
    epsilon: float = ...,
) -> np.ndarray: ...


def safe_log(
    value: float | np.ndarray,
    epsilon: float = EPSILON_LOG,
) -> float | np.ndarray:
    """Safely compute log, avoiding log(0) by adding epsilon.

    Args:
        value: Input value(s) for logarithm.
        epsilon: Small value to add before taking log.

    Returns:
        Natural logarithm of (value + epsilon).

    Examples:
        >>> safe_log(0.0)
        -27.631...
        >>> safe_log(np.array([0.0, 1.0]))
        array([-27.631...,  0.   ])
    """
    if isinstance(value, np.ndarray):
        return np.log(value + epsilon)
    else:
        return math.log(value + epsilon)


@overload
def safe_log2(
    value: float,
    epsilon: float = ...,
) -> float: ...


@overload
def safe_log2(
    value: np.ndarray,
    epsilon: float = ...,
) -> np.ndarray: ...


def safe_log2(
    value: float | np.ndarray,
    epsilon: float = EPSILON_LOG,
) -> float | np.ndarray:
    """Safely compute log base 2, avoiding log(0) by adding epsilon.

    Args:
        value: Input value(s) for logarithm.
        epsilon: Small value to add before taking log.

    Returns:
        Base-2 logarithm of (value + epsilon).

    Examples:
        >>> safe_log2(0.0)
        -39.863...
        >>> safe_log2(np.array([0.0, 1.0]))
        array([-39.863...,  0.   ])
    """
    if isinstance(value, np.ndarray):
        return np.log2(value + epsilon)
    else:
        return math.log2(value + epsilon)


# =============================================================================
# Statistical Helpers
# =============================================================================


def safe_entropy(
    vector: np.ndarray,
    epsilon: float = EPSILON_LOG,
) -> float:
    """Compute Shannon entropy of a vector with improved numerical stability.

    Uses the softmax transformation to convert the vector to probabilities,
    then computes entropy. Handles edge cases (empty arrays, zero sums)
    gracefully.

    Args:
        vector: Input vector (will be converted to probabilities via softmax).
        epsilon: Small value for log stability.

    Returns:
        Shannon entropy in bits (base 2). Returns 0.0 for empty or zero vectors.

    Note:
        This implementation subtracts the max before exp for numerical stability
        (log-sum-exp trick), avoiding overflow for large values.

    Examples:
        >>> safe_entropy(np.array([1.0, 1.0]))  # Uniform distribution
        1.0
        >>> safe_entropy(np.array([1.0, 0.0, 0.0]))  # Concentrated
        0.0
    """
    if vector.size == 0:
        return 0.0

    # Take absolute value to handle negative numbers
    v = np.abs(vector)
    max_abs = v.max()
    if max_abs < epsilon:
        return 0.0

    # Numerical stability: subtract max before exp (log-sum-exp trick)
    v_shifted = v - max_abs
    exp_v = np.exp(v_shifted)
    total = exp_v.sum()

    if total < epsilon:
        return 0.0

    # Compute probabilities
    p = exp_v / total

    # Shannon entropy: -sum(p * log2(p + epsilon))
    return float(-np.sum(p * np.log2(p + epsilon)))


def cosine_similarity(
    v1: np.ndarray,
    v2: np.ndarray,
    epsilon: float = EPSILON_NORM,
) -> float:
    """Compute cosine similarity between two vectors safely.

    Args:
        v1: First vector.
        v2: Second vector.
        epsilon: Minimum norm threshold for numerical stability.

    Returns:
        Cosine similarity in range [-1, 1]. Returns 0.0 if either vector
        has norm below epsilon.

    Examples:
        >>> cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
        1.0
        >>> cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0]))
        0.0
    """
    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))

    if norm1 < epsilon or norm2 < epsilon:
        return 0.0

    return float(np.dot(v1, v2) / (norm1 * norm2))


def batch_cosine_similarity(
    query: np.ndarray,
    vectors: np.ndarray,
    epsilon: float = EPSILON_NORM,
) -> np.ndarray:
    """Compute cosine similarity between a query and multiple vectors.

    Args:
        query: Query vector of shape (d,).
        vectors: Matrix of vectors of shape (n, d).
        epsilon: Minimum norm threshold for numerical stability.

    Returns:
        Array of cosine similarities of shape (n,), preserving the dtype of vectors.

    Examples:
        >>> q = np.array([1.0, 0.0])
        >>> vs = np.array([[1.0, 0.0], [0.0, 1.0]])
        >>> batch_cosine_similarity(q, vs)
        array([1., 0.])
    """
    # Determine output dtype from input vectors
    output_dtype = vectors.dtype if vectors.dtype in (np.float32, np.float64) else np.float64

    query_norm = float(np.linalg.norm(query))
    if query_norm < epsilon:
        return np.zeros(len(vectors), dtype=output_dtype)

    vector_norms = np.linalg.norm(vectors, axis=1)
    # Avoid division by zero
    safe_norms = np.where(vector_norms < epsilon, 1.0, vector_norms)

    similarities = np.dot(vectors, query) / (safe_norms * query_norm)

    # Set similarity to 0 for zero-norm vectors
    similarities = np.where(vector_norms < epsilon, 0.0, similarities)

    return similarities.astype(output_dtype)
