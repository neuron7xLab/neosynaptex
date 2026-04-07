"""Tests for core.accel — GEOSYNC-ACCEL Python integration layer.

Verifies that the transparent fallback between Rust and numpy backends
produces correct, consistent results for gamma computation, Hilbert
curve indexing, and Euclidean distance computation.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np

from core.accel import (
    ACCEL_BACKEND,
    compute_gamma_accel,
    euclidean_distances,
    hilbert_indices,
    hilbert_sort,
    simd_info,
)


class TestGammaAccel:
    """Tests for SIMD-accelerated gamma computation."""

    def test_perfect_power_law(self) -> None:
        """K = 100 * C^(-1.0) should yield gamma ~ 1.0."""
        topo = np.arange(1, 51, dtype=np.float64)
        cost = 100.0 / topo
        result = compute_gamma_accel(topo, cost)
        assert abs(result["gamma"] - 1.0) < 0.05
        assert result["r2"] > 0.99
        assert result["verdict"] == "METASTABLE"
        assert result["n_valid"] == 50

    def test_insufficient_data(self) -> None:
        """Fewer than min_pairs should return INSUFFICIENT_DATA."""
        topo = np.array([1.0, 2.0])
        cost = np.array([5.0, 3.0])
        result = compute_gamma_accel(topo, cost, min_pairs=5)
        assert result["verdict"] == "INSUFFICIENT_DATA"

    def test_bootstrap_gammas_present(self) -> None:
        """Bootstrap gammas should be returned as a list."""
        topo = np.arange(1, 51, dtype=np.float64)
        cost = 100.0 / topo
        result = compute_gamma_accel(topo, cost, bootstrap_n=50)
        assert isinstance(result["bootstrap_gammas"], list)
        assert len(result["bootstrap_gammas"]) > 0

    def test_ci_bounds(self) -> None:
        """CI bounds should contain gamma for well-behaved data."""
        topo = np.arange(1, 101, dtype=np.float64)
        cost = 100.0 / topo
        result = compute_gamma_accel(topo, cost)
        assert result["ci_low"] <= result["gamma"] <= result["ci_high"]

    def test_list_input(self) -> None:
        """Should accept Python lists as input."""
        topo = list(range(1, 51))
        cost = [100.0 / t for t in topo]
        result = compute_gamma_accel(topo, cost)
        assert abs(result["gamma"] - 1.0) < 0.05

    def test_noisy_power_law(self) -> None:
        """Noisy power-law data should still produce reasonable gamma."""
        rng = np.random.default_rng(42)
        topo = np.arange(1, 201, dtype=np.float64)
        cost = 100.0 / topo + rng.normal(0, 0.05, 200)
        cost = np.clip(cost, 0.01, None)
        result = compute_gamma_accel(topo, cost)
        assert abs(result["gamma"] - 1.0) < 0.3
        assert result["verdict"] in ("METASTABLE", "WARNING")


class TestHilbertSort:
    """Tests for Hilbert curve spatial indexing."""

    def test_basic_sort(self) -> None:
        """Hilbert sort should return valid permutation indices."""
        coords = [(0.0, 0.0), (100.0, 100.0), (1.0, 1.0), (99.0, 99.0)]
        indices = hilbert_sort(coords)
        assert sorted(indices) == [0, 1, 2, 3]

    def test_empty_coords(self) -> None:
        """Empty input should return empty indices."""
        assert hilbert_sort([]) == []

    def test_single_point(self) -> None:
        """Single point should return [0]."""
        assert hilbert_sort([(42.0, 37.0)]) == [0]

    def test_numpy_input(self) -> None:
        """Should accept numpy arrays as input."""
        coords = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
        indices = hilbert_sort(coords)
        assert len(indices) == 3

    def test_hilbert_indices_batch(self) -> None:
        """Hilbert indices should be non-negative integers."""
        coords = [(i * 0.1, i * 0.2) for i in range(100)]
        idx = hilbert_indices(coords)
        assert len(idx) == 100
        assert all(i >= 0 for i in idx)


class TestEuclideanDistances:
    """Tests for SIMD-dispatched Euclidean distance."""

    def test_basic_distances(self) -> None:
        """Known distances should match expected values."""
        ax = [0.0, 3.0, 1.0]
        ay = [0.0, 4.0, 1.0]
        dists = euclidean_distances(ax, ay, 0.0, 0.0)
        assert abs(dists[0] - 0.0) < 1e-10
        assert abs(dists[1] - 5.0) < 1e-10
        assert abs(dists[2] - 2**0.5) < 1e-10

    def test_numpy_input(self) -> None:
        """Should accept numpy arrays."""
        ax = np.array([0.0, 1.0, 2.0])
        ay = np.array([0.0, 0.0, 0.0])
        dists = euclidean_distances(ax, ay, 0.0, 0.0)
        assert abs(dists[0] - 0.0) < 1e-10
        assert abs(dists[1] - 1.0) < 1e-10
        assert abs(dists[2] - 2.0) < 1e-10

    def test_large_batch(self) -> None:
        """Large batch should complete without errors."""
        rng = np.random.default_rng(42)
        ax = rng.uniform(-180, 180, 10000)
        ay = rng.uniform(-90, 90, 10000)
        dists = euclidean_distances(ax, ay, 0.0, 0.0)
        assert len(dists) == 10000
        assert all(d >= 0 for d in dists)


class TestSimdInfo:
    """Tests for system capability reporting."""

    def test_info_keys(self) -> None:
        """simd_info should return expected keys."""
        info = simd_info()
        assert "simd_level" in info
        assert "cache_line_bytes" in info
        assert "num_cores" in info
        assert info["num_cores"] >= 1
        assert info["cache_line_bytes"] > 0

    def test_backend_string(self) -> None:
        """ACCEL_BACKEND should be a recognized value."""
        assert ACCEL_BACKEND in ("rust+simd", "numpy")
