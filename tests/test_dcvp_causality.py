"""Causality battery — spec §V.

Synthetic ground truth: a linearly-coupled driver/response system must
pass Granger and TE, while independent noise must fail both.
"""

from __future__ import annotations

import numpy as np

from formal.dcvp.causality import (
    baseline_drift,
    cascade_lag,
    effect_size,
    granger_robust,
    stationarity,
    te_null,
    transfer_entropy,
)


def _coupled_pair(n: int = 300, lag: int = 2, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    y = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.6 * x[t - 1] + rng.normal()
        if t > lag:
            y[t] = 0.5 * y[t - 1] + 0.7 * x[t - lag] + 0.2 * rng.normal()
        else:
            y[t] = rng.normal()
    return x, y


def _independent_pair(n: int = 300, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    return rng.normal(size=n), rng.normal(size=n + 7)[:n]


def test_stationarity_rejects_ramp() -> None:
    ramp = np.arange(200.0)
    rep = stationarity(ramp)
    assert rep.is_stationary is False


def test_stationarity_accepts_white_noise() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    rep = stationarity(x)
    assert rep.nan_fraction == 0.0


def test_transfer_entropy_positive_for_coupled() -> None:
    x, y = _coupled_pair(n=400, lag=2)
    te_xy = transfer_entropy(x, y, lag=2)
    te_yx = transfer_entropy(y, x, lag=2)
    assert te_xy > 0.0
    assert te_xy > te_yx  # direction matters


def test_te_null_z_high_for_coupled() -> None:
    x, y = _coupled_pair(n=500, lag=2, seed=1)
    obs, mu, sigma = te_null(x, y, n_surrogates=100, rng=np.random.default_rng(0), lag=2)
    z = (obs - mu) / (sigma + 1e-12)
    assert z > 2.0


def test_te_null_z_low_for_independent() -> None:
    x, y = _independent_pair(n=500, seed=2)
    obs, mu, sigma = te_null(x, y, n_surrogates=100, rng=np.random.default_rng(0))
    z = (obs - mu) / (sigma + 1e-12)
    assert z < 3.0


def test_granger_detects_coupling() -> None:
    x, y = _coupled_pair(n=400, lag=2, seed=3)
    p, lag = granger_robust(x, y, max_lag=5, seed=0)
    assert p < 0.01
    assert lag >= 1


def test_granger_no_false_positive_on_independent() -> None:
    x, y = _independent_pair(n=400, seed=4)
    p, _ = granger_robust(x, y, max_lag=5, seed=0)
    assert p > 0.01


def test_cascade_lag_stable_for_coupled() -> None:
    x, y = _coupled_pair(n=1000, lag=3, seed=5)
    mean_lag, cv = cascade_lag(x, y, max_lag=6, n_blocks=6)
    assert mean_lag >= 1
    assert cv < 1.0


def test_effect_size_positive_for_coupled() -> None:
    x, y = _coupled_pair(n=400, lag=2, seed=6)
    assert effect_size(x, y) > baseline_drift(x)
