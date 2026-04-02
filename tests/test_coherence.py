"""Transfer entropy for gamma traces — 10 tests.

Covers: _embed, _entropy_hist, _joint_entropy_hist, _conditional_entropy,
_iaaft_surrogate, transfer_entropy_gamma.
"""

from __future__ import annotations

import numpy as np

from core.coherence import (
    _conditional_entropy,
    _embed,
    _entropy_hist,
    _iaaft_surrogate,
    _joint_entropy_hist,
    transfer_entropy_gamma,
)


class TestEmbed:
    def test_shape(self):
        x = np.arange(10, dtype=float)
        E = _embed(x, k=2)
        assert E.shape == (8, 3)  # n - k = 10 - 2 = 8, cols = k+1 = 3

    def test_too_short(self):
        x = np.array([1.0, 2.0])
        E = _embed(x, k=3)
        assert E.shape[0] == 0


class TestEntropy:
    def test_uniform_max_entropy(self):
        x = np.arange(1000, dtype=float)
        h = _entropy_hist(x, bins=10)
        # Uniform over 10 bins -> H = log2(10) ≈ 3.32
        assert 3.0 < h < 3.5

    def test_constant_zero_entropy(self):
        x = np.ones(100)
        h = _entropy_hist(x, bins=10)
        assert h == 0.0

    def test_joint_geq_marginal(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(500)
        y = rng.standard_normal(500)
        h_joint = _joint_entropy_hist(x, y, bins=16)
        h_x = _entropy_hist(x, bins=16)
        assert h_joint >= h_x - 0.01  # joint >= marginal (with tolerance)


class TestConditionalEntropy:
    def test_independent_equals_marginal(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(1000)
        y = rng.standard_normal(1000)
        h_cond = _conditional_entropy(x, y, bins=16)
        h_x = _entropy_hist(x, bins=16)
        # H(X|Y) ≈ H(X) when independent
        assert abs(h_cond - h_x) < 0.5


class TestIAAFTSurrogate:
    def test_preserves_distribution(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(200)
        surr = _iaaft_surrogate(x, rng, n_iter=20)
        assert abs(np.mean(np.sort(x)) - np.mean(np.sort(surr))) < 0.01

    def test_length_preserved(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(100)
        surr = _iaaft_surrogate(x, rng)
        assert len(surr) == len(x)


class TestTransferEntropyGamma:
    def test_causal_te_positive(self):
        rng = np.random.default_rng(42)
        n = 500
        x = rng.standard_normal(n)
        y = np.zeros(n)
        for i in range(1, n):
            y[i] = 0.7 * x[i - 1] + 0.3 * rng.standard_normal()
        result = transfer_entropy_gamma(x, y, k=1, n_surrogate=20, seed=42)
        assert result["te"] > 0

    def test_short_signal_returns_nan(self):
        result = transfer_entropy_gamma(np.array([1.0, 2.0]), np.array([3.0, 4.0]))
        assert np.isnan(result["te"])

    def test_p_value_formula(self):
        rng = np.random.default_rng(42)
        n = 300
        x = rng.standard_normal(n)
        y = rng.standard_normal(n)
        result = transfer_entropy_gamma(x, y, n_surrogate=20, seed=42)
        assert 0.0 < result["p_value"] <= 1.0
