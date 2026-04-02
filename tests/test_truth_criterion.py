"""Truth Criterion (Section 3) — 10 tests.

Covers: rolling_beta, calibrate_epsilon, detect_shift_events,
check_synchronicity, wavelet_coherence_window, surrogate_test.
evaluate_truth_criterion is skipped (depends on bn_syn.transfer_entropy).
"""

from __future__ import annotations

import numpy as np

from contracts.truth_criterion import (
    ShiftEvent,
    calibrate_epsilon,
    check_synchronicity,
    detect_shift_events,
    rolling_beta,
    surrogate_test,
    wavelet_coherence_window,
)


class TestRollingBeta:
    def test_white_noise_beta_near_zero(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(500)
        t, betas = rolling_beta(x, fs=1.0, window=64, step=8)
        assert len(betas) > 0
        # White noise: beta ≈ 0 (flat PSD)
        assert abs(np.median(betas)) < 1.5

    def test_brownian_beta_near_two(self):
        rng = np.random.default_rng(42)
        x = np.cumsum(rng.standard_normal(500))
        t, betas = rolling_beta(x, fs=1.0, window=64, step=8)
        assert len(betas) > 0
        # Brownian: beta ≈ 2
        assert np.median(betas) > 1.0

    def test_short_signal_empty(self):
        t, betas = rolling_beta(np.array([1.0, 2.0, 3.0]), window=64)
        assert len(betas) == 0


class TestCalibrateEpsilon:
    def test_floor(self):
        # Very stable betas -> sigma small -> epsilon = floor
        betas = np.ones(100) + 0.001 * np.random.default_rng(0).standard_normal(100)
        eps = calibrate_epsilon(betas, k=2.0)
        assert eps >= 0.05

    def test_ceiling(self):
        # Very noisy betas -> sigma large -> epsilon = ceiling
        betas = np.random.default_rng(0).standard_normal(100) * 10
        eps = calibrate_epsilon(betas, k=2.0)
        assert eps <= 0.50

    def test_proportional_to_sigma(self):
        rng = np.random.default_rng(42)
        betas_low = 1.0 + 0.05 * rng.standard_normal(200)
        betas_high = 1.0 + 0.2 * rng.standard_normal(200)
        eps_low = calibrate_epsilon(betas_low)
        eps_high = calibrate_epsilon(betas_high)
        assert eps_high >= eps_low


class TestDetectShiftEvents:
    def test_detects_departure(self):
        betas = np.array([1.0, 1.0, 1.5, 1.0, 0.5, 1.0])
        t_centers = np.arange(6)
        events = detect_shift_events(betas, t_centers, epsilon=0.15)
        assert len(events) >= 2  # 1.5 and 0.5 both depart from 1.0

    def test_no_events_in_stable(self):
        betas = np.ones(10) + 0.01 * np.arange(10)
        t_centers = np.arange(10)
        events = detect_shift_events(betas, t_centers, epsilon=0.15)
        assert len(events) == 0


class TestCheckSynchronicity:
    def test_synchronized(self):
        e1 = [ShiftEvent(t_index=100, delta_beta=0.3, channel="a")]
        e2 = [ShiftEvent(t_index=102, delta_beta=-0.2, channel="b")]
        result = check_synchronicity(e1, e2, delta_t=5.0)
        assert result.synchronized
        assert result.dt == 2.0

    def test_not_synchronized(self):
        e1 = [ShiftEvent(t_index=100, delta_beta=0.3, channel="a")]
        e2 = [ShiftEvent(t_index=200, delta_beta=-0.2, channel="b")]
        result = check_synchronicity(e1, e2, delta_t=5.0)
        assert not result.synchronized

    def test_empty_events(self):
        result = check_synchronicity([], [], delta_t=5.0)
        assert not result.synchronized
        assert result.dt is None


class TestWaveletCoherence:
    def test_identical_signals_high(self):
        rng = np.random.default_rng(42)
        x = np.cumsum(rng.standard_normal(200))
        coh = wavelet_coherence_window(x, x, t_center=100)
        assert coh > 0.5

    def test_short_signal_zero(self):
        coh = wavelet_coherence_window(np.array([1.0, 2.0]), np.array([3.0, 4.0]), t_center=1)
        assert coh == 0.0


class TestSurrogateTest:
    def test_identical_signals_significant(self):
        rng = np.random.default_rng(42)
        x = np.cumsum(rng.standard_normal(200))
        coh = wavelet_coherence_window(x, x, t_center=100)
        p, sig = surrogate_test(x, x, coh, n_surrogates=19, seed=42)
        assert 0.0 < p <= 1.0

    def test_independent_not_significant(self):
        rng = np.random.default_rng(42)
        x = rng.standard_normal(200)
        y = rng.standard_normal(200)
        coh = wavelet_coherence_window(x, y, t_center=100)
        p, sig = surrogate_test(x, y, coh, n_surrogates=19, seed=42)
        # Independent signals -> coherence not significant
        assert p > 0.01
