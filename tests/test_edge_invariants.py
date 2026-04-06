"""Edge-case & invariant tests for core signal-processing primitives.

These tests lock down behavior at the boundaries where most bugs hide:
    - degenerate input (empty, constant, NaN, tiny N)
    - determinism under fixed seed
    - mathematical invariants that must hold regardless of input distribution

Covered modules:
    * core.bootstrap   — BootstrapSummary under tiny/degenerate populations
    * core.iaaft       — surrogate spectrum-preservation + p-value bounds
    * core.coherence   — transfer_entropy_gamma non-negativity + short-input safety
    * core.rqa         — recurrence quantification on constant/random signals
    * core.gamma       — scaling-law recovery under controlled noise

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import math

import numpy as np
import pytest


# ===================================================================
# core.bootstrap
# ===================================================================
class TestBootstrapSummaryEdges:
    def test_empty_array_returns_nan_summary(self):
        from core.bootstrap import bootstrap_summary

        s = bootstrap_summary(np.array([]))
        assert s.n == 0
        assert math.isnan(s.gamma)
        assert math.isnan(s.ci_low)
        assert math.isnan(s.ci_high)
        assert math.isnan(s.p_permutation)

    def test_below_minimum_n_returns_nan_summary(self):
        from core.bootstrap import bootstrap_summary

        # 2 values is below the n < 3 guard
        s = bootstrap_summary([1.0, 1.1])
        assert s.n == 2
        assert math.isnan(s.gamma)

    def test_nan_values_filtered_before_size_check(self):
        from core.bootstrap import bootstrap_summary

        s = bootstrap_summary([1.0, float("nan"), float("nan")])
        assert s.n == 1
        assert math.isnan(s.gamma)

    def test_identical_values_zero_std_ci_collapses(self):
        from core.bootstrap import bootstrap_summary

        s = bootstrap_summary([1.0] * 20)
        assert s.gamma == pytest.approx(1.0)
        assert s.std == pytest.approx(0.0, abs=1e-12)
        assert s.ci_low == pytest.approx(1.0)
        assert s.ci_high == pytest.approx(1.0)

    def test_deterministic_under_fixed_seed(self):
        from core.bootstrap import bootstrap_summary

        rng = np.random.default_rng(2026)
        data = rng.normal(1.0, 0.05, 30)
        a = bootstrap_summary(data, seed=17, bootstrap_n=100, permutation_n=100)
        b = bootstrap_summary(data, seed=17, bootstrap_n=100, permutation_n=100)
        assert a == b

    def test_permutation_p_monotone_with_effect(self):
        """Larger deviation from null → smaller p-value."""
        from core.bootstrap import bootstrap_summary

        rng = np.random.default_rng(0)
        # Effect sizes: 0.01, 0.05, 0.20 standard deviations from null=1.0
        near = rng.normal(1.01, 0.05, 50)
        mid = rng.normal(1.10, 0.05, 50)
        far = rng.normal(1.40, 0.05, 50)
        p_near = bootstrap_summary(near, seed=1, bootstrap_n=200, permutation_n=200).p_permutation
        p_mid = bootstrap_summary(mid, seed=1, bootstrap_n=200, permutation_n=200).p_permutation
        p_far = bootstrap_summary(far, seed=1, bootstrap_n=200, permutation_n=200).p_permutation
        assert p_near >= p_mid >= p_far
        assert p_far < 0.05

    def test_permutation_p_never_exactly_zero(self):
        """Phipson–Smyth correction: p = (hits+1)/(n+1), never 0."""
        from core.bootstrap import bootstrap_summary

        data = np.full(30, 100.0)  # huge effect vs null=1.0
        s = bootstrap_summary(data, seed=1, permutation_n=50)
        assert s.p_permutation > 0.0
        # Summary rounds to 6 decimals, so compare with a tolerance
        assert s.p_permutation == pytest.approx(1 / 51, abs=1e-5)


class TestPermutationPValueEdges:
    def test_nan_on_insufficient_points(self):
        from core.bootstrap import permutation_p_value

        p = permutation_p_value(np.array([1.0, 2.0]), np.array([1.0, 2.0]))
        assert math.isnan(p)

    def test_nan_filtered_on_non_positive(self):
        from core.bootstrap import permutation_p_value

        topo = np.array([1.0, 2.0, -3.0, 4.0])
        cost = np.array([1.0, 2.0, 3.0, 0.0])  # 0 filtered out
        # Only 2 valid rows remain → NaN
        p = permutation_p_value(topo, cost)
        assert math.isnan(p)

    def test_strong_scaling_yields_small_p(self):
        """permutation_p_value is two-sided against the null γ = 1.0.

        Permuting the log-topo axis produces slopes near 0 → |0−1| = 1.
        So the test only rejects when |observed γ − 1| > 1, i.e., γ far
        outside [0, 2]. We pick γ_true = 3.0 to guarantee rejection.
        """
        from core.bootstrap import permutation_p_value

        rng = np.random.default_rng(7)
        topo = np.linspace(1.0, 100.0, 40)
        cost = topo ** (-3.0) * (1.0 + 0.02 * rng.standard_normal(40))
        p = permutation_p_value(topo, cost, n_perm=200, seed=7)
        assert p <= 0.05

    def test_null_slope_yields_large_p(self):
        """When γ ≈ 1.0 the null cannot be rejected."""
        from core.bootstrap import permutation_p_value

        rng = np.random.default_rng(5)
        topo = np.linspace(1.0, 100.0, 40)
        cost = topo ** (-1.0) * (1.0 + 0.02 * rng.standard_normal(40))
        p = permutation_p_value(topo, cost, n_perm=200, seed=5)
        assert p > 0.1


# ===================================================================
# core.iaaft
# ===================================================================
class TestIAAFTSurrogate:
    def test_preserves_power_spectrum(self):
        from core.iaaft import iaaft_surrogate

        rng = np.random.default_rng(42)
        sig = rng.standard_normal(512)
        surr, _, spec_err = iaaft_surrogate(sig, rng=np.random.default_rng(0))
        assert spec_err < 1e-3  # spectrum within tolerance

    def test_preserves_amplitude_distribution(self):
        from core.iaaft import iaaft_surrogate

        rng = np.random.default_rng(42)
        sig = rng.standard_normal(512)
        surr, *_ = iaaft_surrogate(sig, rng=np.random.default_rng(0))
        assert np.allclose(np.sort(surr), np.sort(sig))

    def test_deterministic_with_same_rng_seed(self):
        from core.iaaft import iaaft_surrogate

        sig = np.random.default_rng(42).standard_normal(300)
        a, *_ = iaaft_surrogate(sig, rng=np.random.default_rng(99))
        b, *_ = iaaft_surrogate(sig, rng=np.random.default_rng(99))
        np.testing.assert_array_equal(a, b)

    def test_kuramoto_iaaft_preserves_shape(self):
        from core.iaaft import kuramoto_iaaft

        rng = np.random.default_rng(42)
        phases = rng.uniform(-np.pi, np.pi, (5, 300))
        surr = kuramoto_iaaft(phases, n_iter=30, seed=7)
        assert surr.shape == phases.shape
        # Output must remain in (-pi, pi]
        assert np.all(surr >= -np.pi - 1e-9)
        assert np.all(surr <= np.pi + 1e-9)


class TestSurrogatePValue:
    def test_two_tailed_bounds(self):
        from core.iaaft import surrogate_p_value

        null = np.array([0.1, -0.2, 0.05, -0.05, 0.3])
        # obs smaller than everything -> p = 1.0 (every null |>= |obs|)
        assert surrogate_p_value(0.0, null) == pytest.approx(1.0)
        # obs huge -> p minimal = 1/(N+1)
        assert surrogate_p_value(100.0, null) == pytest.approx(1.0 / (len(null) + 1))

    def test_p_is_in_zero_one(self):
        from core.iaaft import surrogate_p_value

        rng = np.random.default_rng(0)
        null = rng.standard_normal(200)
        for obs in (-5.0, -1.0, 0.0, 1.0, 5.0):
            p = surrogate_p_value(obs, null)
            assert 0.0 < p <= 1.0


# ===================================================================
# core.coherence — transfer_entropy_gamma
# ===================================================================
class TestTransferEntropyGamma:
    def test_nonnegative_te(self):
        """Estimator clamps TE to ≥ 0; random series should hover near 0."""
        from core.coherence import transfer_entropy_gamma

        rng = np.random.default_rng(0)
        x = rng.standard_normal(300)
        y = rng.standard_normal(300)
        result = transfer_entropy_gamma(x, y, n_surrogate=10)
        assert float(result["te"]) >= 0.0

    def test_short_input_returns_nan_safely(self):
        from core.coherence import transfer_entropy_gamma

        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 3.0])
        result = transfer_entropy_gamma(x, y, n_surrogate=5)
        assert "te" in result and "p_value" in result
        assert math.isnan(float(result["te"]))

    def test_nan_input_filtered(self):
        """NaN entries are removed before the length check; resulting series
        may fall below the minimum usable length → safe NaN return."""
        from core.coherence import transfer_entropy_gamma

        x = np.array([1.0, float("nan"), 3.0, float("nan"), 5.0])
        y = np.array([1.0, 2.0, float("nan"), 4.0, 5.0])
        result = transfer_entropy_gamma(x, y, n_surrogate=5)
        assert math.isnan(float(result["te"]))

    def test_deterministic_same_seed(self):
        from core.coherence import transfer_entropy_gamma

        rng = np.random.default_rng(42)
        x = rng.standard_normal(200)
        y = rng.standard_normal(200)
        a = transfer_entropy_gamma(x, y, n_surrogate=10, seed=7)
        b = transfer_entropy_gamma(x, y, n_surrogate=10, seed=7)
        assert a == b


# ===================================================================
# core.rqa
# ===================================================================
class TestRecurrenceQuantification:
    def test_constant_signal_max_recurrence(self):
        """All points identical → recurrence rate must be near 1.0."""
        from core.rqa import recurrence_quantification

        sig = np.ones(200)
        r = recurrence_quantification(sig, embedding_dim=3, tau=1, threshold=0.1, n_surrogate=10)
        assert float(r["rr"]) > 0.95

    def test_random_signal_low_recurrence(self):
        from core.rqa import recurrence_quantification

        rng = np.random.default_rng(42)
        sig = rng.standard_normal(300)
        r = recurrence_quantification(sig, embedding_dim=3, tau=1, n_surrogate=10)
        assert float(r["rr"]) < 0.5

    def test_deterministic_same_seed(self):
        from core.rqa import recurrence_quantification

        rng = np.random.default_rng(42)
        sig = rng.standard_normal(200)
        a = recurrence_quantification(sig, embedding_dim=3, tau=1, n_surrogate=10, seed=1)
        b = recurrence_quantification(sig, embedding_dim=3, tau=1, n_surrogate=10, seed=1)
        assert a == b

    def test_short_signal_returns_nan(self):
        from core.rqa import recurrence_quantification

        r = recurrence_quantification(np.arange(5.0), embedding_dim=3, tau=1, n_surrogate=5)
        assert math.isnan(float(r["rr"]))

    def test_rr_det_lam_in_unit_interval(self):
        """All normalised quantifiers must lie in [0, 1]."""
        from core.rqa import recurrence_quantification

        rng = np.random.default_rng(2026)
        sig = np.sin(np.linspace(0, 20 * np.pi, 400)) + 0.1 * rng.standard_normal(400)
        r = recurrence_quantification(sig, embedding_dim=3, tau=1, n_surrogate=10)
        for key in ("rr", "det", "lam"):
            v = float(r[key])
            assert 0.0 <= v <= 1.0 + 1e-9


# ===================================================================
# core.gamma — scaling recovery under controlled noise
# ===================================================================
class TestGammaRecovery:
    def test_clean_power_law_recovers_exponent(self):
        from core.gamma import compute_gamma

        rng = np.random.default_rng(1)
        topo = np.linspace(1.0, 50.0, 40)
        # True gamma = 1.0 → cost = topo^-1
        cost = topo ** (-1.0) * (1.0 + 0.005 * rng.standard_normal(40))
        result = compute_gamma(topo, cost)
        # GammaResult has .gamma attribute
        assert abs(result.gamma - 1.0) < 0.1

    def test_insufficient_data_safely_handled(self):
        from core.gamma import compute_gamma

        topo = np.array([1.0, 2.0])
        cost = np.array([1.0, 0.5])
        # Must not crash; output may be nan or a small-sample estimate
        result = compute_gamma(topo, cost)
        assert hasattr(result, "gamma")
