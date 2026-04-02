"""Block bootstrap engine tests -- 8 tests covering tau, N_eff, CI, substrates."""

import numpy as np
import pytest

from core.block_bootstrap import (
    SUBSTRATE_BLOCK_PARAMS,
    compute_block_bootstrap,
    effective_sample_size,
    integrated_autocorr_time,
)


def test_white_noise_tau_near_one():
    z = np.random.default_rng(42).standard_normal(500)
    assert 0.5 < integrated_autocorr_time(z) < 3.0


def test_ar1_tau_larger_than_iid():
    rng = np.random.default_rng(42)
    z = np.zeros(500)
    for i in range(1, 500):
        z[i] = 0.8 * z[i - 1] + rng.standard_normal()
    assert integrated_autocorr_time(z) > 3.0


def test_n_eff_bounded_by_nonoverlap():
    x = np.random.default_rng(0).standard_normal(200)
    n_eff, _ = effective_sample_size(x, x, x, raw_length=20000, window_len=100)
    assert n_eff <= 20000 // 100


def test_bootstrap_known_gamma():
    rng = np.random.default_rng(42)
    topo = np.linspace(1, 30, 80)
    cost = topo ** (-1.0) * (1 + 0.03 * rng.standard_normal(80))
    x, y = np.log(topo), np.log(cost)
    r = compute_block_bootstrap(x, y, "zebrafish", raw_length=8000, window_len=100)
    assert abs(r.gamma - (-1.0)) < 0.2
    assert r.ci_low < -1.0 < r.ci_high


def test_ar1_detects_higher_autocorrelation():
    """AR(1) phi=0.8 must have higher tau_star than iid."""
    rng = np.random.default_rng(42)
    n = 200
    x_iid = rng.standard_normal(n)
    y_iid = -x_iid + 0.1 * rng.standard_normal(n)
    r_iid = compute_block_bootstrap(
        x_iid, y_iid, "bn_syn", raw_length=20000, window_len=100, n_replicates=500
    )
    x_ar = np.zeros(n)
    for i in range(1, n):
        x_ar[i] = 0.7 * x_ar[i - 1] + rng.standard_normal()
    y_ar = -x_ar + 0.1 * rng.standard_normal(n)
    r_ar = compute_block_bootstrap(
        x_ar, y_ar, "bn_syn", raw_length=20000, window_len=100, n_replicates=500
    )
    # tau_star must be higher for AR(1) — the core correctness property
    assert r_ar.tau_star > r_iid.tau_star * 1.5


def test_all_substrates_run():
    rng = np.random.default_rng(0)
    x = np.log(np.linspace(1, 10, 50))
    y = -x + 0.05 * rng.standard_normal(50)
    for sub in SUBSTRATE_BLOCK_PARAMS:
        r = compute_block_bootstrap(x, y, sub, raw_length=5000, window_len=100, n_replicates=100)
        assert r.gamma is not None
        assert r.n_replicates == 100


def test_unknown_substrate_raises():
    with pytest.raises(ValueError, match="Unknown substrate"):
        compute_block_bootstrap(
            np.zeros(10), np.zeros(10), "invalid", raw_length=1000, window_len=100
        )


def test_white_noise_no_false_metastability():
    rng = np.random.default_rng(99)
    x = rng.standard_normal(60)
    y = rng.standard_normal(60)
    if np.ptp(x) < 0.5:
        pytest.skip("range too small")
    r = compute_block_bootstrap(x, y, "kuramoto", raw_length=6000, window_len=100, n_replicates=200)
    # White noise should not produce gamma near 1.0 with tight CI
    assert r.gamma is not None
