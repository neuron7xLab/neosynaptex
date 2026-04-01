"""
Runtime Invariants and Guards for Hippocampal CA1-LAM.

This module provides runtime validation functions that can be enabled
in debug/test mode and disabled in production for performance.

Invariants:
1. Shape checks - consistent input/output dimensions
2. Finite checks - no NaN/Inf values
3. Bounded weights - weights within [W_min, W_max]
4. State bounds - state sizes don't grow unbounded
5. Determinism - same seed produces same outputs
6. Spectral stability - ρ(W) ≤ 1.0
7. Non-negativity - certain values must be non-negative
8. Probability normalization - probabilities sum to 1
"""

from __future__ import annotations

import functools
import threading
from typing import Any, Callable, TypeVar

import numpy as np

# Thread-local storage for guards state (thread-safe)
_guards_local = threading.local()


def _get_guards_enabled() -> bool:
    """Get thread-local guards enabled state."""
    if not hasattr(_guards_local, "enabled"):
        _guards_local.enabled = True  # Default enabled
    return _guards_local.enabled


def set_guards_enabled(enabled: bool) -> None:
    """Enable or disable runtime guards for the current thread."""
    _guards_local.enabled = enabled


def guards_enabled() -> bool:
    """Check if guards are currently enabled for the current thread."""
    return _get_guards_enabled()


class InvariantViolation(Exception):
    """Exception raised when a runtime invariant is violated."""


# =============================================================================
# SHAPE CHECKS
# =============================================================================


def check_shape_1d(arr: np.ndarray, expected_size: int, name: str = "array") -> None:
    """
    Check that array is 1D with expected size.

    Args:
        arr: Array to check
        expected_size: Expected number of elements
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if arr.ndim != 1:
        raise InvariantViolation(
            f"{name}: expected 1D array, got {arr.ndim}D with shape {arr.shape}"
        )
    if arr.shape[0] != expected_size:
        raise InvariantViolation(f"{name}: expected size {expected_size}, got {arr.shape[0]}")


def check_shape_2d(arr: np.ndarray, expected_shape: tuple[int, int], name: str = "array") -> None:
    """
    Check that array is 2D with expected shape.

    Args:
        arr: Array to check
        expected_shape: Expected (rows, cols)
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if arr.ndim != 2:
        raise InvariantViolation(
            f"{name}: expected 2D array, got {arr.ndim}D with shape {arr.shape}"
        )
    if arr.shape != expected_shape:
        raise InvariantViolation(f"{name}: expected shape {expected_shape}, got {arr.shape}")


def check_square_matrix(arr: np.ndarray, name: str = "matrix") -> int:
    """
    Check that array is a square matrix.

    Args:
        arr: Array to check
        name: Name for error messages

    Returns:
        Size of the matrix (number of rows/cols)
    """
    if not _get_guards_enabled():
        return arr.shape[0] if arr.ndim >= 1 else 0
    if arr.ndim != 2:
        raise InvariantViolation(f"{name}: expected 2D array, got {arr.ndim}D")
    if arr.shape[0] != arr.shape[1]:
        raise InvariantViolation(f"{name}: expected square matrix, got shape {arr.shape}")
    return arr.shape[0]


# =============================================================================
# FINITE CHECKS
# =============================================================================


def check_finite(arr: np.ndarray, name: str = "array") -> None:
    """
    Check that array contains only finite values (no NaN or Inf).

    Args:
        arr: Array to check
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if not np.all(np.isfinite(arr)):
        n_nan = np.sum(np.isnan(arr))
        n_inf = np.sum(np.isinf(arr))
        raise InvariantViolation(f"{name}: contains {n_nan} NaN and {n_inf} Inf values")


def check_no_nan(arr: np.ndarray, name: str = "array") -> None:
    """
    Check that array contains no NaN values.

    Args:
        arr: Array to check
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if np.any(np.isnan(arr)):
        n_nan = np.sum(np.isnan(arr))
        raise InvariantViolation(f"{name}: contains {n_nan} NaN values")


# =============================================================================
# BOUNDED CHECKS
# =============================================================================


def check_bounded(
    arr: np.ndarray,
    low: float,
    high: float,
    name: str = "array",
    strict: bool = False,
) -> None:
    """
    Check that array values are within bounds.

    Args:
        arr: Array to check
        low: Lower bound (inclusive unless strict)
        high: Upper bound (inclusive unless strict)
        name: Name for error messages
        strict: If True, bounds are exclusive
    """
    if not _get_guards_enabled():
        return
    if strict:
        if np.any(arr <= low) or np.any(arr >= high):
            raise InvariantViolation(
                f"{name}: values must be in ({low}, {high}), "
                f"got range [{arr.min()}, {arr.max()}]"
            )
    else:
        if np.any(arr < low) or np.any(arr > high):
            raise InvariantViolation(
                f"{name}: values must be in [{low}, {high}], "
                f"got range [{arr.min()}, {arr.max()}]"
            )


def check_non_negative(arr: np.ndarray, name: str = "array") -> None:
    """
    Check that array values are non-negative.

    Args:
        arr: Array to check
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if np.any(arr < 0):
        n_neg = np.sum(arr < 0)
        min_val = arr.min()
        raise InvariantViolation(
            f"{name}: must be non-negative, found {n_neg} negative values, min={min_val}"
        )


def check_probability(arr: np.ndarray, name: str = "probability", axis: int = -1) -> None:
    """
    Check that array represents valid probabilities.

    Args:
        arr: Array to check (should sum to 1 along axis)
        name: Name for error messages
        axis: Axis along which probabilities should sum to 1
    """
    if not _get_guards_enabled():
        return
    check_bounded(arr, 0.0, 1.0, name)
    sums = np.sum(arr, axis=axis)
    if not np.allclose(sums, 1.0, rtol=1e-5, atol=1e-5):
        raise InvariantViolation(
            f"{name}: probabilities must sum to 1, "
            f"got sums in range [{sums.min()}, {sums.max()}]"
        )


# =============================================================================
# SPECTRAL STABILITY
# =============================================================================


def compute_spectral_radius(weights: np.ndarray) -> float:
    """
    Compute spectral radius of weight matrix.

    Args:
        weights: Square weight matrix

    Returns:
        Spectral radius (maximum absolute eigenvalue)
    """
    eigenvalues = np.linalg.eigvals(weights)
    return float(np.max(np.abs(eigenvalues)))


def check_spectral_radius(
    weights: np.ndarray,
    max_radius: float = 1.0,
    name: str = "weights",
) -> float:
    """
    Check that weight matrix has spectral radius ≤ max_radius.

    Args:
        weights: Square weight matrix
        max_radius: Maximum allowed spectral radius
        name: Name for error messages

    Returns:
        Computed spectral radius
    """
    if not _get_guards_enabled():
        return 0.0
    check_square_matrix(weights, name)
    rho = compute_spectral_radius(weights)
    if rho > max_radius:
        raise InvariantViolation(f"{name}: spectral radius {rho:.4f} exceeds maximum {max_radius}")
    return rho


# =============================================================================
# STATE SIZE BOUNDS
# =============================================================================


def check_state_size(size: int, max_size: int, name: str = "state") -> None:
    """
    Check that state size doesn't exceed maximum.

    Args:
        size: Current size
        max_size: Maximum allowed size
        name: Name for error messages
    """
    if not _get_guards_enabled():
        return
    if size > max_size:
        raise InvariantViolation(f"{name}: size {size} exceeds maximum {max_size}")


# =============================================================================
# DETERMINISM CHECK
# =============================================================================


def check_determinism(
    func: Callable[..., np.ndarray],
    *args: Any,
    seed: int = 42,
    rtol: float = 1e-10,
    atol: float = 1e-10,
    **kwargs: Any,
) -> bool:
    """
    Check that a function produces deterministic outputs given the same seed.

    Args:
        func: Function to test
        *args: Positional arguments to function
        seed: Random seed to use
        rtol: Relative tolerance for comparison
        atol: Absolute tolerance for comparison
        **kwargs: Keyword arguments to function

    Returns:
        True if deterministic

    Raises:
        InvariantViolation: If outputs differ between runs
    """
    if not _get_guards_enabled():
        return True

    # First run
    np.random.seed(seed)
    result1 = func(*args, **kwargs)

    # Second run with same seed
    np.random.seed(seed)
    result2 = func(*args, **kwargs)

    if not np.allclose(result1, result2, rtol=rtol, atol=atol):
        max_diff = np.max(np.abs(result1 - result2))
        raise InvariantViolation(
            f"Function {func.__name__} is not deterministic: " f"max difference = {max_diff}"
        )
    return True


# =============================================================================
# DECORATOR FOR GUARDED FUNCTIONS
# =============================================================================


F = TypeVar("F", bound=Callable[..., Any])


def guarded(func: F) -> F:
    """
    Decorator to wrap function with standard guards.

    Checks inputs and outputs for finite values.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if _get_guards_enabled():
            # Check array inputs
            for i, arg in enumerate(args):
                if isinstance(arg, np.ndarray):
                    check_finite(arg, f"arg_{i}")
            for key, val in kwargs.items():
                if isinstance(val, np.ndarray):
                    check_finite(val, key)

        result = func(*args, **kwargs)

        if _get_guards_enabled():
            # Check array outputs
            if isinstance(result, np.ndarray):
                check_finite(result, f"{func.__name__}_output")
            elif isinstance(result, dict):
                for key, val in result.items():
                    if isinstance(val, np.ndarray):
                        check_finite(val, f"{func.__name__}.{key}")

        return result

    return wrapper  # type: ignore[return-value]


# =============================================================================
# VALIDATION SUMMARY
# =============================================================================


def validate_memory_state(
    weights: np.ndarray,
    activations: np.ndarray,
    weight_min: float = 0.0,
    weight_max: float = 10.0,
    max_spectral_radius: float = 1.0,
) -> dict[str, bool]:
    """
    Comprehensive validation of memory state.

    Args:
        weights: Weight matrix [N, N]
        activations: Activation vector [N]
        weight_min: Minimum weight value
        weight_max: Maximum weight value
        max_spectral_radius: Maximum spectral radius

    Returns:
        Dictionary of validation results
    """
    results = {
        "shape_valid": True,
        "finite_valid": True,
        "bounds_valid": True,
        "spectral_valid": True,
    }

    try:
        n = check_square_matrix(weights, "weights")
        check_shape_1d(activations, n, "activations")
    except InvariantViolation:
        results["shape_valid"] = False

    try:
        check_finite(weights, "weights")
        check_finite(activations, "activations")
    except InvariantViolation:
        results["finite_valid"] = False

    try:
        check_bounded(weights, weight_min, weight_max, "weights")
    except InvariantViolation:
        results["bounds_valid"] = False

    try:
        check_spectral_radius(weights, max_spectral_radius, "weights")
    except (InvariantViolation, np.linalg.LinAlgError):
        results["spectral_valid"] = False

    return results
