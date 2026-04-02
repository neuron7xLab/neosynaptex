from __future__ import annotations

import numpy as np

from core.block_bootstrap import (
    autocorrelation_time,
    block_bootstrap_gamma,
    effective_sample_size,
    iid_bootstrap_gamma,
)


def test_autocorrelation_time_ar1_recovery():
    phi = 0.8
    rng = np.random.default_rng(123)
    n = 4000
    x = np.zeros(n, dtype=np.float64)
    eps = rng.normal(0, 1, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    tau_hat = autocorrelation_time(x)
    tau_true = (1 + phi) / (1 - phi)
    assert abs(tau_hat - tau_true) / tau_true < 0.2


def test_block_bootstrap_ci_wider_than_iid_for_autocorrelated():
    rng = np.random.default_rng(7)
    n = 256
    topo = np.linspace(1, 10, n)
    noise = np.zeros(n)
    eps = rng.normal(0, 0.1, n)
    for i in range(1, n):
        noise[i] = 0.9 * noise[i - 1] + eps[i]
    cost = 10.0 * topo ** (-1.0) + noise
    lt = np.log(topo)
    lc = np.log(np.clip(np.abs(cost), 1e-6, None))
    iid = iid_bootstrap_gamma(lt, lc, n_boot=300, seed=11)
    block = block_bootstrap_gamma(lt, lc, block_length=16, n_boot=300, seed=11)
    iid_w = iid.ci_high - iid.ci_low
    block_w = block.ci_high - block.ci_low
    assert block_w >= iid_w


def test_effective_sample_size_less_than_raw_for_autocorrelated():
    rng = np.random.default_rng(17)
    n = 1000
    x = np.zeros(n)
    e = rng.normal(size=n)
    for i in range(1, n):
        x[i] = 0.85 * x[i - 1] + e[i]
    tau = autocorrelation_time(x)
    neff = effective_sample_size(n, tau)
    assert neff < n
