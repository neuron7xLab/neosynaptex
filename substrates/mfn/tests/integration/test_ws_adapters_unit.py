"""Unit tests for WebSocket adapter helpers."""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.integration.ws_adapters import _compute_fractal_dimension


def test_compute_fractal_dimension_handles_empty_field() -> None:
    """Empty fields should not produce NaNs from log(0) operations."""

    field = np.zeros((16, 16), dtype=float)

    dimension = _compute_fractal_dimension(field)

    assert dimension == 0.0


def test_compute_fractal_dimension_returns_finite_value_for_sparse_activity() -> None:
    """Sparse but non-empty fields should yield a finite, bounded dimension."""

    field = np.zeros((16, 16), dtype=float)
    field[0, 0] = 0.02  # Single active point above threshold

    dimension = _compute_fractal_dimension(field)

    assert np.isfinite(dimension)
    assert 0.0 <= dimension <= 2.0
