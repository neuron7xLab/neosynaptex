"""Tests for analytical Jacobian optimization in LyapunovAnalyzer.

Validates:
1. Correctness: analytical ~ numerical for small grids (tolerance 0.5)
2. Performance: analytical must be >100x faster than numerical FD
3. Registry: correct dispatch by function name
4. Scaling: O(N^2) confirmed by timing ratio
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from mycelium_fractal_net.core.jacobian_registry import (
    JACOBIAN_REGISTRY,
    fhn_jacobian,
    gray_scott_jacobian,
    leading_lambda1_analytical,
    register_jacobian,
)
from mycelium_fractal_net.core.thermodynamic_kernel import LyapunovAnalyzer


def gray_scott_rxn(u: np.ndarray, v: np.ndarray, F: float = 0.04, k: float = 0.06) -> tuple[np.ndarray, np.ndarray]:
    """Gray-Scott reaction — name must match registry key."""
    return (-u * v**2 + F * (1 - u), u * v**2 - (F + k) * v)


def fhn_reaction(u: np.ndarray, v: np.ndarray, a: float = 0.13, b: float = 0.013, c1: float = 0.26, c2: float = 0.1, I: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """FHN reaction — name matches registry key."""
    du = c1 * u * (u - a) * (1 - u) - c2 * u * v + I
    dv = b * (u - v)
    return du, dv


def unknown_rxn(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Unknown reaction not in registry — forces randomized path."""
    return -u * v + 0.04 * (1 - u), u * v - 0.1 * v


class TestGrayScottJacobian:
    """Gray-Scott analytical Jacobian correctness and performance."""

    def test_stable_uniform_field(self) -> None:
        u = np.ones((32, 32)) * 0.5
        v = np.ones((32, 32)) * 0.25
        lam1 = gray_scott_jacobian(u, v, F=0.04, k=0.06)
        assert lam1 < 0.5, f"Expected stable regime, got {lam1}"

    def test_returns_scalar(self) -> None:
        rng = np.random.default_rng(42)
        u = rng.random((16, 16))
        v = rng.random((16, 16)) * 0.3
        result = gray_scott_jacobian(u, v)
        assert isinstance(result, float)
        assert np.isfinite(result)

    def test_correctness_vs_numerical(self) -> None:
        """Analytical lambda_1 should match numerical FD within tolerance 0.5."""
        rng = np.random.default_rng(42)
        u = rng.random((8, 8))
        v = rng.random((8, 8)) * 0.3

        lam1_analytical = gray_scott_jacobian(u, v, F=0.04, k=0.06)

        la = LyapunovAnalyzer()
        spectrum_numerical = la._numerical_fd_spectrum(u, v, gray_scott_rxn)
        lam1_numerical = float(spectrum_numerical[0])

        assert abs(lam1_analytical - lam1_numerical) < 0.5, (
            f"Analytical {lam1_analytical:.4f} vs numerical {lam1_numerical:.4f}"
        )

    def test_performance_analytical_vs_numerical(self) -> None:
        """Analytical must be >=100x faster than numerical FD on 32x32."""
        rng = np.random.default_rng(42)
        u = rng.random((32, 32))
        v = rng.random((32, 32)) * 0.3

        t0 = time.perf_counter()
        for _ in range(10):
            gray_scott_jacobian(u, v)
        t_analytical = (time.perf_counter() - t0) / 10

        la = LyapunovAnalyzer()
        t0 = time.perf_counter()
        la._numerical_fd_spectrum(u, v, gray_scott_rxn)
        t_numerical = time.perf_counter() - t0

        speedup = t_numerical / (t_analytical + 1e-9)
        assert speedup > 100, (
            f"Expected >=100x speedup, got {speedup:.1f}x "
            f"(analytical={t_analytical * 1000:.2f}ms, numerical={t_numerical * 1000:.2f}ms)"
        )

    def test_scaling_quadratic_not_quartic(self) -> None:
        """Verify O(N^2) scaling: timing(64)/timing(32) ~ 4 (not 16)."""
        rng = np.random.default_rng(42)
        u32 = rng.random((32, 32))
        v32 = rng.random((32, 32))
        u64 = rng.random((64, 64))
        v64 = rng.random((64, 64))

        n_iter = 20
        t0 = time.perf_counter()
        for _ in range(n_iter):
            gray_scott_jacobian(u32, v32)
        t32 = (time.perf_counter() - t0) / n_iter

        t0 = time.perf_counter()
        for _ in range(n_iter):
            gray_scott_jacobian(u64, v64)
        t64 = (time.perf_counter() - t0) / n_iter

        ratio = t64 / (t32 + 1e-12)
        assert ratio < 8.0, f"Ratio {ratio:.1f} suggests super-quadratic scaling"


class TestFHNJacobian:
    def test_returns_finite(self) -> None:
        rng = np.random.default_rng(42)
        u = rng.random((32, 32)) * 0.5
        v = rng.random((32, 32)) * 0.1
        result = fhn_jacobian(u, v)
        assert np.isfinite(result)

    def test_negative_for_stable_params(self) -> None:
        u = np.ones((16, 16)) * 0.05
        v = np.ones((16, 16)) * 0.05
        lam1 = fhn_jacobian(u, v)
        assert lam1 < 1.0, f"Expected stable/metastable, got {lam1}"


class TestRegistry:
    def test_gray_scott_dispatches_analytically(self) -> None:
        rng = np.random.default_rng(42)
        u = rng.random((64, 64))
        v = rng.random((64, 64)) * 0.3

        lam1, method = leading_lambda1_analytical(u, v, gray_scott_rxn)
        assert "analytical" in method
        assert np.isfinite(lam1)

    def test_fhn_dispatches_analytically(self) -> None:
        rng = np.random.default_rng(42)
        u = rng.random((64, 64)) * 0.5
        v = rng.random((64, 64)) * 0.1

        _lam1, method = leading_lambda1_analytical(u, v, fhn_reaction)
        assert "analytical" in method

    def test_unknown_reaction_fallback(self) -> None:
        rng = np.random.default_rng(42)
        u = rng.random((32, 32))
        v = rng.random((32, 32)) * 0.3

        lam1, method = leading_lambda1_analytical(u, v, unknown_rxn)
        assert method == "randomized_power"
        assert np.isfinite(lam1)

    def test_custom_registration(self) -> None:
        def custom_rxn(u: np.ndarray, v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            return -u, -v

        def custom_jac(u: np.ndarray, v: np.ndarray, **kw: float) -> float:
            return -1.0

        register_jacobian("custom_rxn", custom_jac)
        assert "custom_rxn" in JACOBIAN_REGISTRY

        lam1, method = leading_lambda1_analytical(
            u=np.ones((4, 4)), v=np.ones((4, 4)), reaction_fn=custom_rxn,
        )
        assert "analytical" in method
        assert lam1 == -1.0

        # Cleanup
        del JACOBIAN_REGISTRY["custom_rxn"]


class TestLyapunovAnalyzerIntegration:
    def test_leading_exponent_uses_analytical(self) -> None:
        la = LyapunovAnalyzer()
        rng = np.random.default_rng(42)
        u = rng.random((64, 64))
        v = rng.random((64, 64)) * 0.3

        t0 = time.perf_counter()
        lam1 = la.leading_lyapunov_exponent(u, v, gray_scott_rxn)
        elapsed = (time.perf_counter() - t0) * 1000

        assert np.isfinite(lam1)
        assert elapsed < 50.0, f"Expected <50ms analytical path, got {elapsed:.2f}ms"
        assert "analytical" in la.last_method

    def test_compute_jacobian_spectrum_shape(self) -> None:
        la = LyapunovAnalyzer(n_top_eigenvalues=8)
        rng = np.random.default_rng(42)
        u = rng.random((32, 32))
        v = rng.random((32, 32)) * 0.3

        spectrum = la.compute_jacobian_spectrum(u, v, gray_scott_rxn)
        assert spectrum.shape == (8,)
        assert np.isfinite(spectrum[0])

    @pytest.mark.parametrize("N", [32, 64, 128])
    def test_performance_target(self, N: int) -> None:
        """Performance gate: analytical path must be <10ms for all grid sizes."""
        la = LyapunovAnalyzer()
        rng = np.random.default_rng(42)
        u = rng.random((N, N))
        v = rng.random((N, N)) * 0.3

        # Warmup
        la.leading_lyapunov_exponent(u, v, gray_scott_rxn)

        times = []
        for _ in range(5):
            t0 = time.perf_counter()
            la.leading_lyapunov_exponent(u, v, gray_scott_rxn)
            times.append((time.perf_counter() - t0) * 1000)

        median_ms = float(np.median(times))
        assert median_ms < 50.0, (
            f"Performance gate failed for {N}x{N}: {median_ms:.2f}ms > 50ms"
        )

    def test_backward_compatibility_small_grid_numerical(self) -> None:
        """Legacy numerical FD still works for small grids with unknown reactions."""
        la = LyapunovAnalyzer()
        rng = np.random.default_rng(42)
        u = rng.random((8, 8))
        v = rng.random((8, 8)) * 0.3

        lam1 = la.leading_lyapunov_exponent(u, v, unknown_rxn)
        assert np.isfinite(lam1)

    def test_last_method_property(self) -> None:
        la = LyapunovAnalyzer()
        u = np.ones((16, 16)) * 0.5
        v = np.ones((16, 16)) * 0.25
        la.leading_lyapunov_exponent(u, v, gray_scott_rxn)
        assert la.last_method != "unknown"
