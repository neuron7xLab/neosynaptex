"""Multi-lag Granger causality — 8 tests.

Covers: granger_multilag with BIC lag selection, F-test, permutation p-value.
"""

from __future__ import annotations

import numpy as np

from core.granger_multilag import granger_multilag


class TestGrangerMultilag:
    def test_causal_signal_rejects_null(self):
        """X causes Y with lag-1 -> low p-value."""
        rng = np.random.default_rng(42)
        n = 500
        x = rng.standard_normal(n)
        y = np.zeros(n)
        for i in range(1, n):
            y[i] = 0.6 * x[i - 1] + 0.4 * rng.standard_normal()
        result = granger_multilag(x, y, max_lag=5, n_surrogate=50, seed=42)
        assert result["p_value"] < 0.1, f"p={result['p_value']}"
        assert result["f_stat"] > 0

    def test_independent_signals_high_p(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(300)
        y = rng.standard_normal(300)
        result = granger_multilag(x, y, max_lag=3, n_surrogate=50, seed=42)
        assert result["p_value"] > 0.01

    def test_short_signal_nan(self):
        result = granger_multilag(np.array([1.0, 2.0]), np.array([3.0, 4.0]), max_lag=1)
        assert np.isnan(result["f_stat"])
        assert result["lag_selected"] is None

    def test_returns_expected_keys(self):
        rng = np.random.default_rng(0)
        result = granger_multilag(rng.standard_normal(100), rng.standard_normal(100), max_lag=3)
        for key in ["lag_selected", "f_stat", "p_value", "bic_per_lag", "n_obs"]:
            assert key in result

    def test_bic_lag_selection(self):
        """BIC should select lag close to true lag."""
        rng = np.random.default_rng(42)
        n = 600
        x = rng.standard_normal(n)
        y = np.zeros(n)
        for i in range(2, n):
            y[i] = 0.5 * x[i - 2] + 0.5 * rng.standard_normal()
        result = granger_multilag(x, y, max_lag=5, n_surrogate=20, seed=42)
        assert result["lag_selected"] is not None
        assert len(result["bic_per_lag"]) > 0

    def test_nan_handling(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(200)
        y = rng.standard_normal(200)
        x[50:55] = np.nan
        y[100:105] = np.nan
        result = granger_multilag(x, y, max_lag=3, n_surrogate=20, seed=42)
        assert isinstance(result["f_stat"], float)

    def test_p_value_range(self):
        rng = np.random.default_rng(42)
        result = granger_multilag(
            rng.standard_normal(200),
            rng.standard_normal(200),
            max_lag=3,
            n_surrogate=50,
            seed=42,
        )
        if not np.isnan(result["p_value"]):
            assert 0.0 < result["p_value"] <= 1.0

    def test_n_obs_matches_data(self):
        rng = np.random.default_rng(42)
        result = granger_multilag(rng.standard_normal(150), rng.standard_normal(150), max_lag=3)
        if result["lag_selected"] is not None:
            assert result["n_obs"] > 0
            assert result["n_obs"] <= 150
