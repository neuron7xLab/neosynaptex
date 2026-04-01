"""Time discretization utilities for simulation step counts."""

from __future__ import annotations

from math import isclose


def compute_steps_exact(duration_ms: float, dt_ms: float) -> int:
    """Compute an exact integer step count for duration/dt.

    Raises
    ------
    ValueError
        If ``dt_ms`` is non-positive or ``duration_ms / dt_ms`` is not integer-aligned.
    """
    if dt_ms <= 0:
        raise ValueError("dt_ms must be greater than 0")

    ratio = duration_ms / dt_ms
    nearest = round(ratio)
    if not isclose(ratio, nearest, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(
            "duration_ms must be an integer multiple of dt_ms within tolerance; "
            f"got duration_ms={duration_ms}, dt_ms={dt_ms}"
        )
    return int(nearest)
