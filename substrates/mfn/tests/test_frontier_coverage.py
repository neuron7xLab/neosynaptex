"""Coverage tests for mathematical frontier modules."""

from __future__ import annotations

import json

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.causal_emergence import (
    discretize_turing_field,
)
from mycelium_fractal_net.analytics.fisher_information import (
    FIMResult,
    compute_fim,
    natural_gradient_step,
)
from mycelium_fractal_net.analytics.rmt_spectral import rmt_diagnostics

# ── FIM compute_fim ──────────────────────────────────────────────────────────


def test_compute_fim_basic() -> None:
    """FIM from simple simulate function."""

    def sim(theta: np.ndarray) -> np.ndarray:
        return np.outer(np.sin(theta[0] * np.arange(8)), np.cos(theta[1] * np.arange(8)))

    result = compute_fim(sim, np.array([1.0, 2.0]), sigma=0.1)
    assert isinstance(result, FIMResult)
    assert result.F.shape == (2, 2)
    assert len(result.eigenvalues) == 2
    assert np.isfinite(result.log_det)
    assert np.isfinite(result.trace)
    assert np.isfinite(result.epistemic_value)
    assert result.cma_init_cov.shape == (2, 2)
    json.dumps(result.to_dict())


def test_compute_fim_precision_equals_F() -> None:
    """Precision matrix should equal F."""

    def sim(theta: np.ndarray) -> np.ndarray:
        return np.ones((4, 4)) * theta[0]

    result = compute_fim(sim, np.array([1.0]), sigma=0.1)
    np.testing.assert_array_equal(result.precision_matrix, result.F)


# ── natural_gradient_step ────────────────────────────────────────────────────


def test_natural_gradient_step() -> None:
    """Natural gradient takes a step and returns FIM."""

    def sim(theta: np.ndarray) -> np.ndarray:
        return np.outer(np.sin(theta[0] * np.arange(4)), np.cos(theta[1] * np.arange(4)))

    def loss(field: np.ndarray) -> float:
        return float(np.sum(field**2))

    theta0 = np.array([1.0, 2.0])
    theta1, fim = natural_gradient_step(sim, loss, theta0, lr=0.001)
    assert theta1.shape == theta0.shape
    assert not np.array_equal(theta0, theta1)
    assert isinstance(fim, FIMResult)


# ── RMT with Gramian ────────────────────────────────────────────────────────


def test_rmt_with_gramian() -> None:
    """RMT diagnostics with W_c Gramian → signal/noise separation."""
    N = 16
    rng = np.random.default_rng(42)
    # Random symmetric Laplacian-like matrix
    A = rng.standard_normal((N, N))
    L = A @ A.T
    # Random Gramian
    W_c = rng.standard_normal((8, 8))
    W_c = W_c @ W_c.T
    result = rmt_diagnostics(L, W_c=W_c, n_samples=100)
    assert result.gram_signal_ratio >= 0.0
    assert result.n_signal_dims >= 0
    assert result.noise_fraction >= 0.0
    assert result.mp_threshold > 0.0
    json.dumps(result.to_dict())


def test_rmt_gram_signal_ratio_in_dict() -> None:
    """gram_signal_ratio appears in to_dict output."""
    L = np.eye(8) * 2 - np.ones((8, 8)) * 0.2
    result = rmt_diagnostics(L)
    d = result.to_dict()
    assert "gram_signal_ratio" in d


# ── discretize_turing_field edge cases ───────────────────────────────────────


def test_discretize_homogeneous() -> None:
    assert discretize_turing_field(np.ones((16, 16)) * 0.5) == 0


def test_discretize_varied_field() -> None:
    """Non-trivial field should return 1, 2, or 3."""
    rng = np.random.default_rng(42)
    field = rng.standard_normal((32, 32))
    state = discretize_turing_field(field)
    assert 0 <= state <= 3


def test_discretize_strong_pattern() -> None:
    """High-variance field with coherent structure."""
    x = np.linspace(0, 4 * np.pi, 32)
    field = np.outer(np.sin(x), np.cos(x)) * 0.1
    state = discretize_turing_field(field)
    assert state in (1, 2, 3)  # not homogeneous


# ── Math frontier with FIM ───────────────────────────────────────────────────


def test_frontier_with_fim() -> None:
    """run_math_frontier with run_fim=True."""
    from mycelium_fractal_net.analytics.math_frontier import run_math_frontier

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=10, seed=42))

    def sim(theta: np.ndarray) -> np.ndarray:
        return mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=10, seed=42)).field

    report = run_math_frontier(
        seq, run_fim=True, fim_simulate_fn=sim, fim_theta=np.array([0.05, 0.06])
    )
    assert report.fim is not None
    assert np.isfinite(report.fim.epistemic_value)
    assert "FIM=" in report.summary()


def test_frontier_fim_in_dict() -> None:
    """FIM data appears in to_dict when computed."""
    from mycelium_fractal_net.analytics.math_frontier import run_math_frontier

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=5, seed=0))

    def sim(theta: np.ndarray) -> np.ndarray:
        return np.ones((8, 8)) * theta[0]

    report = run_math_frontier(
        seq,
        run_rmt=False,
        run_fim=True,
        fim_simulate_fn=sim,
        fim_theta=np.array([1.0]),
    )
    d = report.to_dict()
    assert d["fim"] is not None
    assert "epistemic_value" in d["fim"]
