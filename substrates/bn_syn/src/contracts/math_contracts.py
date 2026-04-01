"""Assertion-based mathematical contracts for deterministic validation.

Each helper validates a narrowly scoped invariant and raises ``AssertionError``
with a diagnostic token when the invariant is violated.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def assert_non_empty_text(value: str) -> None:
    """Require non-whitespace text content.

    Raises:
        AssertionError: If ``value`` is empty or whitespace-only.
    """
    if not value.strip():
        raise AssertionError("empty_text")


def assert_numeric_finite_and_bounded(values: Iterable[float], *, bound: float = 1e12) -> None:
    """Require all numeric values to be finite and within ``±bound``."""
    for value in values:
        if not math.isfinite(value):
            raise AssertionError("non_finite_detected")
        if abs(value) > bound:
            raise AssertionError("range_violation_abs_gt_bound")


def assert_dt_stability(dt: float, max_eigenvalue: float, *, method: str = "euler") -> None:
    """Validate explicit-step stability using ``dt * |lambda_max|`` thresholds.

    Supported methods are ``euler`` and ``rk4``.
    """
    method_l = method.lower()
    threshold = 1.0 if method_l == "euler" else 2.785 if method_l == "rk4" else None
    if threshold is None:
        raise AssertionError(f"unsupported_method:{method}")
    product = dt * abs(max_eigenvalue)
    if product >= threshold:
        raise AssertionError(
            f"dt_stability_violation:method={method_l}:dt|lambda|={product:.6g}:threshold={threshold}"
        )


def assert_state_finite_after_step(state: np.ndarray, step_index: int) -> None:
    """Require state vector to remain finite after a simulation step."""
    if not np.all(np.isfinite(state)):
        bad = np.argwhere(~np.isfinite(state)).flatten().tolist()
        raise AssertionError(f"state_non_finite:step={step_index}:indices={bad}")


def assert_energy_bounded(energy_series: np.ndarray, max_energy: float) -> None:
    """Require 1D finite energy trace to stay bounded and non-increasing."""
    energy = np.asarray(energy_series, dtype=np.float64)
    if energy.ndim != 1 or energy.size == 0:
        raise AssertionError("energy_series_invalid_shape")
    if np.any(~np.isfinite(energy)):
        raise AssertionError("energy_non_finite")
    over = np.where(np.abs(energy) > max_energy)[0]
    if over.size:
        idx = int(over[0])
        raise AssertionError(f"energy_bound_violation:index={idx}:value={energy[idx]:.6g}")
    deltas = np.diff(energy)
    inc = np.where(deltas > 1e-4)[0]
    if inc.size:
        idx = int(inc[0] + 1)
        raise AssertionError(f"energy_monotonicity_violation:index={idx}:delta={deltas[inc[0]]:.6g}")


def assert_integration_tolerance_consistency(atol: float, rtol: float, dt: float) -> None:
    """Check tolerance scales against integration step size and float precision."""
    if not (atol < dt):
        raise AssertionError(f"atol_dt_inconsistent:atol={atol}:dt={dt}")
    if not (rtol > np.finfo(np.float64).eps):
        raise AssertionError(f"rtol_too_small:rtol={rtol}")


def assert_phase_range(phases: np.ndarray) -> None:
    """Require phases to lie in either ``[0, 2π)`` or ``[-π, π)``."""
    vals = np.asarray(phases, dtype=np.float64)
    if vals.size == 0:
        raise AssertionError("phase_empty")
    in_0_2pi = np.all((vals >= 0.0) & (vals < 2.0 * np.pi))
    in_pm_pi = np.all((vals >= -np.pi) & (vals < np.pi))
    if not (in_0_2pi or in_pm_pi):
        bad = np.where(~(((vals >= 0.0) & (vals < 2.0 * np.pi)) | ((vals >= -np.pi) & (vals < np.pi))))[0]
        raise AssertionError(f"phase_out_of_range:indices={bad[:10].tolist()}")


def assert_order_parameter_range(r: float) -> None:
    """Require Kuramoto order parameter ``r`` to be in ``[0, 1]`` (with epsilon)."""
    eps = 1e-10
    if not (-eps <= r <= 1.0 + eps):
        raise AssertionError(f"order_parameter_out_of_range:r={r}")


def assert_order_parameter_computation(phases: np.ndarray, reported_r: float, tol: float = 1e-6) -> None:
    """Cross-check reported order parameter against direct recomputation."""
    vals = np.asarray(phases, dtype=np.float64)
    recomputed = float(np.abs(np.mean(np.exp(1j * vals))))
    if abs(recomputed - reported_r) >= tol:
        raise AssertionError(
            f"order_parameter_mismatch:reported={reported_r:.9g}:recomputed={recomputed:.9g}:tol={tol}"
        )


def assert_phase_velocity_finite(dtheta_dt: np.ndarray) -> None:
    """Require phase velocity array values to be finite."""
    vals = np.asarray(dtheta_dt, dtype=np.float64)
    if not np.all(np.isfinite(vals)):
        raise AssertionError("phase_velocity_non_finite")


def assert_coupling_matrix_properties(K: np.ndarray, expected_symmetric: bool = True) -> None:
    """Validate coupling matrix shape, finiteness, and optional symmetry."""
    arr = np.asarray(K)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise AssertionError(f"coupling_shape_invalid:shape={arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise AssertionError("coupling_non_finite")
    if expected_symmetric and not np.allclose(arr, arr.T, atol=1e-12):
        raise AssertionError("coupling_not_symmetric")
    _ = float(np.max(np.abs(np.linalg.eigvals(arr))))


def assert_adjacency_binary(A: np.ndarray) -> None:
    """Require square binary adjacency with zero diagonal (no self-loops)."""
    arr = np.asarray(A)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise AssertionError("adjacency_shape_invalid")
    if not np.all(np.isin(arr, (0, 1))):
        raise AssertionError("adjacency_non_binary")
    if not np.all(np.diag(arr) == 0):
        raise AssertionError("adjacency_self_loops")


def assert_weight_matrix_nonnegative(W: np.ndarray) -> None:
    """Require all synaptic weights to be non-negative."""
    arr = np.asarray(W, dtype=np.float64)
    if np.any(arr < 0):
        idx = np.argwhere(arr < 0)[0].tolist()
        raise AssertionError(f"weight_negative:index={idx}:value={arr[tuple(idx)]}")


def assert_no_catastrophic_cancellation(
    a: np.ndarray, b: np.ndarray, result: np.ndarray, context: str
) -> None:
    """Guard subtraction-sensitive regions against catastrophic cancellation."""
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    rr = np.asarray(result, dtype=np.float64)
    ref = np.maximum(np.abs(aa), np.abs(bb))
    small = np.abs(aa - bb)
    mask = (ref > 0) & (small / ref < 1e-8)
    if np.any(mask):
        if np.any(rr[mask] == 0.0):
            raise AssertionError(f"catastrophic_cancellation:{context}")
        rel_err = np.abs((rr - (aa - bb)) / np.maximum(np.abs(aa - bb), 1e-30))
        if np.any(rel_err[mask] > 1e-3):
            raise AssertionError(f"catastrophic_cancellation:{context}")


def assert_no_log_domain_violation(x: np.ndarray, context: str) -> None:
    """Require strictly positive arguments for log-domain operations."""
    arr = np.asarray(x, dtype=np.float64)
    bad = np.where(arr <= 0)[0]
    if bad.size:
        raise AssertionError(f"log_domain_violation:{context}:indices={bad[:10].tolist()}")


def assert_no_exp_overflow_risk(x: np.ndarray, context: str) -> None:
    """Flag exponent arguments with overflow risk in float64 arithmetic."""
    arr = np.asarray(x, dtype=np.float64)
    bad = np.where(np.abs(arr) > 500.0)[0]
    if bad.size:
        raise AssertionError(f"exp_overflow_risk:{context}:indices={bad[:10].tolist()}")


def assert_no_division_by_zero_risk(denominator: np.ndarray, context: str) -> None:
    """Require denominators to remain away from near-zero machine underflow."""
    arr = np.asarray(denominator, dtype=np.float64)
    bad = np.where(np.abs(arr) < 1e-300)[0]
    if bad.size:
        raise AssertionError(f"division_by_zero_risk:{context}:indices={bad[:10].tolist()}")


def assert_dtype_consistency(arrays: dict[str, np.ndarray]) -> None:
    """Require all provided arrays to share the same dtype."""
    dtypes = {name: np.asarray(value).dtype for name, value in arrays.items()}
    unique = {str(v) for v in dtypes.values()}
    if len(unique) > 1:
        raise AssertionError(f"dtype_mismatch:{dtypes}")


def assert_no_nan_in_dataset(data: np.ndarray, name: str) -> None:
    """Reject datasets containing NaN values."""
    arr = np.asarray(data, dtype=np.float64)
    if np.isnan(arr).any():
        raise AssertionError(f"dataset_nan:{name}")


def assert_no_duplicate_rows(data: np.ndarray, name: str) -> None:
    """Require a 2D dataset with unique rows only."""
    arr = np.asarray(data)
    if arr.ndim != 2:
        raise AssertionError(f"dataset_not_2d:{name}")
    unique_rows = np.unique(arr, axis=0)
    if unique_rows.shape[0] != arr.shape[0]:
        raise AssertionError(f"dataset_duplicate_rows:{name}")


def assert_column_ranges(
    data: np.ndarray, column_specs: dict[str, tuple[float, float]], name: str
) -> None:
    """Validate structured-array columns against inclusive numeric ranges."""
    if data.dtype.names is None:
        raise AssertionError(f"dataset_not_structured:{name}")
    for col, (lo, hi) in column_specs.items():
        if col not in data.dtype.names:
            raise AssertionError(f"missing_column:{name}:{col}")
        vals = np.asarray(data[col], dtype=np.float64)
        if np.any((vals < lo) | (vals > hi)):
            raise AssertionError(f"column_out_of_range:{name}:{col}")


def assert_probability_normalization(probs: np.ndarray, axis: int, tol: float = 1e-8) -> None:
    """Require probabilities to sum to one along the selected axis."""
    arr = np.asarray(probs, dtype=np.float64)
    sums = np.sum(arr, axis=axis)
    if not np.allclose(sums, 1.0, atol=tol, rtol=0.0):
        raise AssertionError("probability_not_normalized")


def assert_timeseries_monotonic_time(t: np.ndarray) -> None:
    """Require strictly increasing timestamps in a time series."""
    arr = np.asarray(t, dtype=np.float64)
    if np.any(np.diff(arr) <= 0):
        raise AssertionError("time_not_strictly_increasing")
