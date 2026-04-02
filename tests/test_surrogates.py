from __future__ import annotations

import numpy as np
from scipy.stats import ks_2samp

from core.surrogates import block_shuffle, iaaft_surrogate, null_family_test, shared_phase_iaaft


def _acf1(x: np.ndarray) -> float:
    x0 = x[:-1] - np.mean(x[:-1])
    x1 = x[1:] - np.mean(x[1:])
    denom = np.sqrt(np.dot(x0, x0) * np.dot(x1, x1))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(x0, x1) / denom)


def test_iaaft_preserves_power_spectrum_within_10pct():
    rng = np.random.default_rng(101)
    n = 512
    t = np.arange(n)
    x = np.sin(2 * np.pi * t / 32) + 0.3 * np.sin(2 * np.pi * t / 9) + rng.normal(0, 0.2, n)
    s = iaaft_surrogate(x, rng)
    p0 = np.abs(np.fft.rfft(x)) ** 2
    p1 = np.abs(np.fft.rfft(s)) ** 2
    rel = np.mean(np.abs(p0 - p1) / (p0 + 1e-12))
    assert rel < 0.10


def test_iaaft_preserves_amplitude_distribution():
    rng = np.random.default_rng(102)
    x = rng.normal(0, 1.2, 512) ** 3
    s = iaaft_surrogate(x, rng)
    _, p = ks_2samp(x, s)
    assert p > 0.05


def test_shuffle_destroys_autocorrelation():
    rng = np.random.default_rng(103)
    x = np.cumsum(rng.normal(size=600))
    sh = rng.permutation(x)
    assert abs(_acf1(sh)) < abs(_acf1(x))


def test_block_shuffle_preserves_within_block_structure():
    rng = np.random.default_rng(104)
    x = np.arange(60, dtype=float)
    y = block_shuffle(x, block_length=5, rng=rng)
    orig_blocks = {tuple(x[i : i + 5]) for i in range(0, 60, 5)}
    new_blocks = [tuple(y[i : i + 5]) for i in range(0, 60, 5)]
    assert all(b in orig_blocks for b in new_blocks)


def test_pure_noise_nulls_non_significant():
    rng = np.random.default_rng(105)
    lt = rng.normal(size=256)
    lc = rng.normal(size=256)
    out = null_family_test(lt, lc, n_surrogates=99, seed=13)
    assert all(v["p_value"] > 0.05 for v in out.values())


def test_known_signal_significant_for_at_least_one_null():
    rng = np.random.default_rng(106)
    topo = np.linspace(1, 20, 300)
    cost = 12.0 * topo ** (-1.0) + rng.normal(0, 0.03, 300)
    lt = np.log(topo)
    lc = np.log(np.clip(cost, 1e-6, None))
    out = null_family_test(lt, lc, n_surrogates=99, seed=14)
    assert any(v["p_value"] < 0.05 for v in out.values())


def test_shared_phase_iaaft_preserves_cross_channel_correlation():
    rng = np.random.default_rng(107)
    n = 512
    base = np.sin(2 * np.pi * np.arange(n) / 20) + rng.normal(0, 0.1, n)
    ch1 = base + rng.normal(0, 0.05, n)
    ch2 = 0.7 * base + rng.normal(0, 0.05, n)
    x = np.vstack([ch1, ch2])
    y = shared_phase_iaaft(x, rng)
    corr_x = float(np.corrcoef(x)[0, 1])
    corr_y = float(np.corrcoef(y)[0, 1])
    assert abs(corr_x - corr_y) < 0.15
