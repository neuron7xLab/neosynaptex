"""Tests for core.gamma_fdt_estimator — Task 2 deliverable."""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from core.gamma_fdt_estimator import (
    GammaFDTEstimate,
    GammaFDTEstimator,
    simulate_ou_pair,
)

FloatArray = NDArray[np.float64]


def test_construction_validation() -> None:
    with pytest.raises(ValueError):
        GammaFDTEstimator(dt=0.0)
    with pytest.raises(ValueError):
        GammaFDTEstimator(bootstrap_n=-1)
    with pytest.raises(ValueError):
        GammaFDTEstimator(block_size=0)


def test_shape_and_length_validation() -> None:
    est = GammaFDTEstimator(dt=1.0, bootstrap_n=0)
    with pytest.raises(ValueError):
        est.estimate(np.zeros((3, 2)), np.zeros((3, 2)), 0.1)
    with pytest.raises(ValueError):
        est.estimate(np.zeros(10), np.zeros(11), 0.1)
    with pytest.raises(ValueError):
        est.estimate(np.zeros(5), np.zeros(5), 0.1)


def test_zero_variance_noise_fails_gracefully() -> None:
    est = GammaFDTEstimator(dt=1.0, bootstrap_n=0)
    with pytest.raises(ValueError):
        est.estimate(np.zeros(100), np.zeros(100), 0.1)


def test_recovers_known_gamma_response_branch() -> None:
    """Inject γ = 0.7 into OU, estimate via FDT response branch, assert tol."""
    gamma_true = 0.7
    dt = 0.01
    n = 20_000
    noise, response = simulate_ou_pair(
        gamma_true=gamma_true,
        T=1.0,
        n_steps=n,
        dt=dt,
        perturbation=1.0,
        seed=7,
    )
    est = GammaFDTEstimator(dt=dt, bootstrap_n=50, block_size=256, seed=7)
    out = est.estimate(noise, response, perturbation=1.0)
    assert isinstance(out, GammaFDTEstimate)
    assert out.method == "response"
    # Response branch with common random numbers is very accurate.
    assert abs(out.gamma_hat - gamma_true) < 0.05, f"gamma_hat={out.gamma_hat} vs true={gamma_true}"


def test_recovers_known_gamma_variance_branch() -> None:
    """Variance branch (no perturbation) recovers γ within 25 %."""
    gamma_true = 1.2
    dt = 0.01
    n = 50_000
    noise, response = simulate_ou_pair(
        gamma_true=gamma_true,
        T=1.0,
        n_steps=n,
        dt=dt,
        perturbation=0.0,
        seed=13,
    )
    est = GammaFDTEstimator(dt=dt, bootstrap_n=0, block_size=512, seed=13)
    out = est.estimate(noise, response, perturbation=0.0)
    assert out.method == "variance"
    assert abs(out.gamma_hat_var - gamma_true) / gamma_true < 0.25


def test_reproducibility_same_seed() -> None:
    """Two independent runs with identical seeds must match exactly."""
    dt = 0.01
    n_a1, r_a1 = simulate_ou_pair(1.0, 1.0, 5_000, dt, 1.0, seed=99)
    n_a2, r_a2 = simulate_ou_pair(1.0, 1.0, 5_000, dt, 1.0, seed=99)
    np.testing.assert_allclose(n_a1, n_a2)
    np.testing.assert_allclose(r_a1, r_a2)

    est1 = GammaFDTEstimator(dt=dt, bootstrap_n=30, seed=11)
    est2 = GammaFDTEstimator(dt=dt, bootstrap_n=30, seed=11)
    o1 = est1.estimate(n_a1, r_a1, 1.0)
    o2 = est2.estimate(n_a2, r_a2, 1.0)
    assert o1.gamma_hat == pytest.approx(o2.gamma_hat)
    assert o1.gamma_hat_var == pytest.approx(o2.gamma_hat_var)
    assert o1.uncertainty == pytest.approx(o2.uncertainty)


def test_zero_perturbation_falls_back_to_variance() -> None:
    dt = 0.05
    noise, response = simulate_ou_pair(1.0, 1.0, 4_000, dt, 0.0, seed=3)
    est = GammaFDTEstimator(dt=dt, bootstrap_n=0, seed=3)
    out = est.estimate(noise, response, perturbation=0.0)
    assert out.method == "variance"
    assert out.gamma_hat == pytest.approx(out.gamma_hat_var)


def test_bootstrap_uncertainty_nonneg_and_finite() -> None:
    dt = 0.02
    noise, response = simulate_ou_pair(0.8, 1.0, 6_000, dt, 0.5, seed=17)
    est = GammaFDTEstimator(dt=dt, bootstrap_n=40, block_size=128, seed=17)
    out = est.estimate(noise, response, perturbation=0.5)
    assert np.isfinite(out.uncertainty)
    assert out.uncertainty >= 0.0


def test_sensitivity_curve_monotone_stability() -> None:
    """γ̂ should be (approximately) insensitive to perturbation amplitude."""
    gamma_true = 1.0
    dt = 0.01
    n = 10_000

    def sim(a: float) -> tuple[FloatArray, FloatArray]:
        return simulate_ou_pair(
            gamma_true=gamma_true,
            T=1.0,
            n_steps=n,
            dt=dt,
            perturbation=a,
            seed=21,
        )

    est = GammaFDTEstimator(dt=dt, bootstrap_n=0, seed=21)
    amps = np.array([0.25, 0.5, 1.0, 2.0], dtype=np.float64)
    curve = est.sensitivity_curve(sim, amps)
    assert curve.shape == amps.shape
    # All values should land within ±20 % of the truth — that is the
    # "linear response" regime: γ̂ should not depend on amplitude.
    assert np.all(np.abs(curve - gamma_true) / gamma_true < 0.2)


def test_simulate_ou_pair_validates_inputs() -> None:
    with pytest.raises(ValueError):
        simulate_ou_pair(-1.0, 1.0, 100, 0.01, 1.0, seed=1)
    with pytest.raises(ValueError):
        simulate_ou_pair(1.0, 0.0, 100, 0.01, 1.0, seed=1)
    with pytest.raises(ValueError):
        simulate_ou_pair(1.0, 1.0, 4, 0.01, 1.0, seed=1)
