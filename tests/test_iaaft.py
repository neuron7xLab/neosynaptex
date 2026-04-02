"""IAAFT surrogate engine tests -- spectral fidelity, multivariate, p-value."""

import numpy as np

from core.iaaft import (
    iaaft_multivariate,
    iaaft_surrogate,
    kuramoto_iaaft,
    surrogate_p_value,
)


def test_single_channel_spectral_fidelity():
    rng = np.random.default_rng(42)
    z = np.zeros(500)
    for i in range(1, 500):
        z[i] = 0.8 * z[i - 1] + rng.standard_normal()
    surr, iters, err = iaaft_surrogate(z, rng=np.random.default_rng(0))
    assert err < 1e-4, f"Spectral error too large: {err}"
    assert len(surr) == len(z)
    assert iters > 0


def test_amplitude_distribution_preserved():
    rng = np.random.default_rng(42)
    z = rng.standard_normal(300)
    surr, _, _ = iaaft_surrogate(z, rng=np.random.default_rng(0))
    assert abs(np.sort(z).mean() - np.sort(surr).mean()) < 0.01


def test_multivariate_shape():
    rng = np.random.default_rng(42)
    X = rng.standard_normal((4, 300))
    X_surr = iaaft_multivariate(X, seed=42)
    assert X_surr.shape == X.shape


def test_multivariate_destroys_cross_correlation():
    rng = np.random.default_rng(42)
    base = np.cumsum(rng.standard_normal(200))
    X = np.vstack([base + 0.1 * rng.standard_normal(200) for _ in range(3)])
    orig_corr = np.corrcoef(X)[0, 1]
    X_surr = iaaft_multivariate(X, seed=0)
    surr_corr = np.corrcoef(X_surr)[0, 1]
    assert abs(surr_corr) < abs(orig_corr)


def test_kuramoto_iaaft_shape():
    rng = np.random.default_rng(42)
    phases = rng.uniform(-np.pi, np.pi, (8, 200))
    surr = kuramoto_iaaft(phases, n_iter=50, seed=42)
    assert surr.shape == phases.shape
    assert np.all(np.abs(surr) <= np.pi + 0.01)


def test_p_value_formula():
    gamma_obs = 1.5
    gamma_null = np.array([0.1, 0.5, 1.0, 2.0, 3.0])
    p = surrogate_p_value(gamma_obs, gamma_null)
    # |null| >= |1.5|: 2.0, 3.0 → count=2, p = (1+2)/(5+1) = 0.5
    assert abs(p - 0.5) < 1e-10


def test_p_value_all_exceed():
    p = surrogate_p_value(0.1, np.array([1.0, 2.0, 3.0]))
    assert abs(p - 1.0) < 1e-10


def test_timeout_protection():
    rng = np.random.default_rng(42)
    z = rng.standard_normal(100)
    surr, iters, err = iaaft_surrogate(z, n_iter=10**6, max_time_seconds=0.5, rng=rng)
    assert len(surr) == len(z)
