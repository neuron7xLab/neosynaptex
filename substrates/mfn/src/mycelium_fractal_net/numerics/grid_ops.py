"""Grid operations for reaction-diffusion simulations."""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from mycelium_fractal_net.types.exceptions import NumericalInstabilityError

if TYPE_CHECKING:
    from numpy.typing import NDArray

# numba loaded on first use — avoids pulling scipy/LLVM on base import
njit = None
_numba_loaded = False


def _load_numba() -> None:
    global njit, _numba_loaded
    if _numba_loaded:
        return
    _numba_loaded = True
    try:
        from numba import njit as _njit
        njit = _njit  # type: ignore[assignment]
    except Exception:  # pragma: no cover
        pass


class BoundaryCondition(Enum):
    PERIODIC = "periodic"
    NEUMANN = "neumann"
    DIRICHLET = "dirichlet"


def _use_accel(use_accel: bool | None) -> bool:
    if use_accel is not None:
        return bool(use_accel)
    return os.getenv("MFN_ENABLE_ACCEL_LAPLACIAN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _laplacian_numpy_periodic(field: NDArray[np.floating]) -> NDArray[np.floating]:
    up = np.roll(field, 1, axis=0)
    down = np.roll(field, -1, axis=0)
    left = np.roll(field, 1, axis=1)
    right = np.roll(field, -1, axis=1)
    return cast("NDArray[np.floating[Any]]", up + down + left + right - 4.0 * field)


def _laplacian_numpy_neumann(field: NDArray[np.floating]) -> NDArray[np.floating]:
    up = np.empty_like(field)
    up[1:, :] = field[:-1, :]
    up[0, :] = field[0, :]

    down = np.empty_like(field)
    down[:-1, :] = field[1:, :]
    down[-1, :] = field[-1, :]

    left = np.empty_like(field)
    left[:, 1:] = field[:, :-1]
    left[:, 0] = field[:, 0]

    right = np.empty_like(field)
    right[:, :-1] = field[:, 1:]
    right[:, -1] = field[:, -1]
    return cast("NDArray[np.floating[Any]]", up + down + left + right - 4.0 * field)


def _laplacian_numpy_dirichlet(field: NDArray[np.floating]) -> NDArray[np.floating]:
    up = np.pad(field[:-1, :], ((1, 0), (0, 0)), mode="constant", constant_values=0)
    down = np.pad(field[1:, :], ((0, 1), (0, 0)), mode="constant", constant_values=0)
    left = np.pad(field[:, :-1], ((0, 0), (1, 0)), mode="constant", constant_values=0)
    right = np.pad(field[:, 1:], ((0, 0), (0, 1)), mode="constant", constant_values=0)
    return cast("NDArray[np.floating[Any]]", up + down + left + right - 4.0 * field)


_laplacian_periodic_jit = None
_laplacian_neumann_jit = None
_laplacian_dirichlet_jit = None
_jit_compiled = False


def _compile_jit_kernels() -> None:
    """Compile numba JIT kernels on first use (avoids loading scipy at import)."""
    global _laplacian_periodic_jit, _laplacian_neumann_jit, _laplacian_dirichlet_jit, _jit_compiled
    if _jit_compiled:
        return
    _jit_compiled = True
    _load_numba()
    if njit is None:
        return

    @njit(cache=True)  # type: ignore[misc]
    def _p_jit(field):  # type: ignore[misc]
        rows, cols = field.shape
        out = np.empty_like(field)
        for i in range(rows):
            up = (i - 1) % rows
            down = (i + 1) % rows
            for j in range(cols):
                left = (j - 1) % cols
                right = (j + 1) % cols
                out[i, j] = field[up, j] + field[down, j] + field[i, left] + field[i, right] - 4.0 * field[i, j]
        return out

    @njit(cache=True)  # type: ignore[misc]
    def _n_jit(field):  # type: ignore[misc]
        rows, cols = field.shape
        out = np.empty_like(field)
        for i in range(rows):
            up = i if i == 0 else i - 1
            down = i if i == rows - 1 else i + 1
            for j in range(cols):
                left = j if j == 0 else j - 1
                right = j if j == cols - 1 else j + 1
                out[i, j] = field[up, j] + field[down, j] + field[i, left] + field[i, right] - 4.0 * field[i, j]
        return out

    @njit(cache=True)  # type: ignore[misc]
    def _d_jit(field):  # type: ignore[misc]
        rows, cols = field.shape
        out = np.empty_like(field)
        for i in range(rows):
            for j in range(cols):
                up = field[i - 1, j] if i > 0 else 0.0
                down = field[i + 1, j] if i < rows - 1 else 0.0
                left = field[i, j - 1] if j > 0 else 0.0
                right = field[i, j + 1] if j < cols - 1 else 0.0
                out[i, j] = up + down + left + right - 4.0 * field[i, j]
        return out

    _laplacian_periodic_jit = _p_jit
    _laplacian_neumann_jit = _n_jit
    _laplacian_dirichlet_jit = _d_jit


def laplacian_backend(use_accel: bool | None = None) -> str:
    if _use_accel(use_accel):
        _compile_jit_kernels()
        if _laplacian_periodic_jit is not None:
            return "numba-jit"
    return "numpy-reference"


def compute_laplacian(
    field: NDArray[np.floating],
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC,
    check_stability: bool = True,
    use_accel: bool | None = None,
) -> NDArray[np.floating]:
    field = np.asarray(field, dtype=np.float64)
    if field.ndim != 2:
        raise ValueError(f"field must be 2D, got ndim={field.ndim}")

    accel = False
    if _use_accel(use_accel):
        _compile_jit_kernels()
        accel = _laplacian_periodic_jit is not None
    if boundary == BoundaryCondition.PERIODIC:
        laplacian = _laplacian_periodic_jit(field) if accel else _laplacian_numpy_periodic(field)
    elif boundary == BoundaryCondition.NEUMANN:
        laplacian = _laplacian_neumann_jit(field) if accel else _laplacian_numpy_neumann(field)
    else:
        laplacian = _laplacian_dirichlet_jit(field) if accel else _laplacian_numpy_dirichlet(field)

    if check_stability:
        validate_field_stability(laplacian, field_name="laplacian")
    return cast("NDArray[np.floating[Any]]", laplacian)


def compute_gradient(
    field: NDArray[np.floating],
    boundary: BoundaryCondition = BoundaryCondition.PERIODIC,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    if boundary == BoundaryCondition.PERIODIC:
        grad_x = (np.roll(field, -1, axis=0) - np.roll(field, 1, axis=0)) / 2.0
        grad_y = (np.roll(field, -1, axis=1) - np.roll(field, 1, axis=1)) / 2.0
    else:
        grad_x = np.zeros_like(field)
        grad_y = np.zeros_like(field)
        grad_x[1:-1, :] = (field[2:, :] - field[:-2, :]) / 2.0
        grad_y[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / 2.0
        if boundary == BoundaryCondition.NEUMANN:
            grad_x[0, :] = 0.0
            grad_x[-1, :] = 0.0
            grad_y[:, 0] = 0.0
            grad_y[:, -1] = 0.0
        else:
            grad_x[0, :] = field[1, :] - field[0, :]
            grad_x[-1, :] = field[-1, :] - field[-2, :]
            grad_y[:, 0] = field[:, 1] - field[:, 0]
            grad_y[:, -1] = field[:, -1] - field[:, -2]
    return cast("NDArray[np.floating[Any]]", grad_x), cast("NDArray[np.floating[Any]]", grad_y)


def compute_field_statistics(field: NDArray[np.floating]) -> dict[str, float]:
    return {
        "min": float(np.min(field)),
        "max": float(np.max(field)),
        "mean": float(np.mean(field)),
        "std": float(np.std(field)),
        "nan_count": int(np.sum(np.isnan(field))),
        "inf_count": int(np.sum(np.isinf(field))),
        "finite_fraction": float(np.mean(np.isfinite(field))),
    }


def validate_field_stability(
    field: NDArray[np.floating],
    field_name: str = "field",
    step: int | None = None,
) -> bool:
    nan_count = int(np.sum(np.isnan(field)))
    inf_count = int(np.sum(np.isinf(field)))
    if nan_count > 0:
        raise NumericalInstabilityError(
            f"NaN values detected in {field_name}",
            step=step,
            field_name=field_name,
            nan_count=nan_count,
        )
    if inf_count > 0:
        raise NumericalInstabilityError(
            f"Inf values detected in {field_name}",
            step=step,
            field_name=field_name,
            inf_count=inf_count,
        )
    return True


def validate_field_bounds(
    field: NDArray[np.floating],
    min_value: float,
    max_value: float,
) -> bool:
    return bool(np.all((field >= min_value) & (field <= max_value)))


def clamp_field(
    field: NDArray[np.floating],
    min_value: float,
    max_value: float,
) -> tuple[NDArray[np.floating], int]:
    needs_clamping = (field < min_value) | (field > max_value)
    clamp_count = int(np.sum(needs_clamping))
    clamped = np.clip(field, min_value, max_value)
    return cast("NDArray[np.floating[Any]]", clamped), clamp_count


__all__ = [
    "BoundaryCondition",
    "clamp_field",
    "compute_field_statistics",
    "compute_gradient",
    "compute_laplacian",
    "laplacian_backend",
    "validate_field_bounds",
    "validate_field_stability",
]
