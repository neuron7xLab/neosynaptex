"""Tests for fractal IFS generation and Lyapunov stability."""

import numpy as np
import pytest

pytest.importorskip("torch")

from mycelium_fractal_net.model import (
    compute_lyapunov_exponent,
    generate_fractal_ifs,
)


def test_fractal_ifs_output_shape() -> None:
    """Test IFS generates correct number of points."""
    rng = np.random.default_rng(42)
    num_points = 1000

    points, _ = generate_fractal_ifs(rng, num_points=num_points)

    assert points.shape == (num_points, 2)


def test_fractal_ifs_lyapunov_negative() -> None:
    """Test Lyapunov exponent is negative (stable dynamics)."""
    rng = np.random.default_rng(42)

    _, lyapunov = generate_fractal_ifs(rng, num_points=5000)

    # Lyapunov < 0 indicates stable, contractive dynamics
    assert lyapunov < 0


def test_fractal_ifs_points_bounded() -> None:
    """Test IFS points remain bounded (don't explode)."""
    rng = np.random.default_rng(42)

    points, _ = generate_fractal_ifs(rng, num_points=1000)

    # Points should remain within reasonable bounds
    assert np.all(np.abs(points) < 100)


def test_fractal_ifs_deterministic() -> None:
    """Test IFS generation is deterministic with same seed."""
    rng1 = np.random.default_rng(123)
    rng2 = np.random.default_rng(123)

    points1, lyap1 = generate_fractal_ifs(rng1, num_points=100)
    points2, lyap2 = generate_fractal_ifs(rng2, num_points=100)

    assert np.allclose(points1, points2)
    assert abs(lyap1 - lyap2) < 1e-10


def test_lyapunov_exponent_from_history() -> None:
    """Test Lyapunov computation from field history."""
    # Create simple converging field history
    history = np.zeros((10, 8, 8))
    for t in range(10):
        history[t] = np.random.randn(8, 8) * (0.9**t)

    lyapunov = compute_lyapunov_exponent(history)

    # Should be finite
    assert np.isfinite(lyapunov)


def test_lyapunov_exponent_short_history() -> None:
    """Test Lyapunov with very short history returns 0."""
    history = np.random.randn(1, 8, 8)

    lyapunov = compute_lyapunov_exponent(history)

    assert lyapunov == 0.0


def test_lyapunov_zero_divergence_is_zero() -> None:
    """Stable trajectories with no change should have zero Lyapunov exponent."""
    # Constant field over time
    history = np.zeros((5, 4, 4))

    lyapunov = compute_lyapunov_exponent(history)

    assert lyapunov == 0.0


def test_lyapunov_grid_size_invariant() -> None:
    """Lyapunov exponent should not inflate solely from larger grids."""
    base_history = np.stack(
        [
            np.zeros((2, 2)),
            np.full((2, 2), 0.01),
            np.full((2, 2), 0.02),
        ]
    )

    # Tile the same dynamics to a larger grid; divergence per cell is identical.
    tiled_history = np.tile(base_history, (1, 2, 2))

    small_exponent = compute_lyapunov_exponent(base_history)
    large_exponent = compute_lyapunov_exponent(tiled_history)

    assert small_exponent != 0.0
    assert np.isclose(small_exponent, large_exponent)
