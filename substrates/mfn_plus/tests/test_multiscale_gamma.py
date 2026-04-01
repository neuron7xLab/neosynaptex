"""Tests for multi-scale topological gamma pipeline.

Pre-validated: Stripe gamma=-0.856, Noise gamma=-0.156 (5.5x separation).
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.validation.zebrafish.multiscale_gamma import (
    DEFAULT_SCALES,
    MultiScaleGammaComputer,
    MultiScaleResult,
    MultiScaleValidator,
    PREVALIDATED_NOISE_GAMMA,
    PREVALIDATED_STRIPE_GAMMA,
    RandomControlGenerator,
)


# ── Fixtures ──────────────────────────────────────────────────


def _make_stripe(N: int = 64, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.linspace(0, N, N)
    f = 0.5 + 0.4 * np.cos(2 * np.pi / 25 * x[np.newaxis, :])
    return np.clip(f + rng.normal(0, 0.05, (N, N)), 0, 1)


@pytest.fixture(scope="module")
def stripe_field():
    return _make_stripe()


@pytest.fixture(scope="module")
def noise_field():
    return np.random.default_rng(99).random((64, 64))


@pytest.fixture(scope="module")
def stripe_series():
    N = 64
    x = np.linspace(0, N, N)
    fields = []
    for t in range(20):
        rng = np.random.default_rng(t * 100)
        drift = 0.02 * t
        f = 0.5 + 0.4 * np.cos(2 * np.pi / 25 * (x[np.newaxis, :] + drift))
        fields.append(np.clip(f + rng.normal(0, 0.05, (N, N)), 0, 1))
    return fields


# ── RandomControlGenerator ────────────────────────────────────


class TestRandomControlGenerator:
    def test_spatial_shuffle_preserves_histogram(self, stripe_field):
        ctrl = RandomControlGenerator(seed=0)
        shuffled = ctrl.spatial_shuffle([stripe_field])[0]
        np.testing.assert_allclose(
            np.sort(stripe_field.flatten()),
            np.sort(shuffled.flatten()),
            atol=1e-10,
        )

    def test_spatial_shuffle_destroys_spatial_correlation(self, stripe_field):
        ctrl = RandomControlGenerator(seed=0)
        shuffled = ctrl.spatial_shuffle([stripe_field])[0]
        ac_orig = float(np.mean(stripe_field[:, 1:] * stripe_field[:, :-1]))
        ac_shuf = float(np.mean(shuffled[:, 1:] * shuffled[:, :-1]))
        assert ac_orig > ac_shuf

    def test_gaussian_noise_in_unit_interval(self):
        ctrl = RandomControlGenerator()
        for f in ctrl.gaussian_noise(5, 64):
            assert f.min() >= 0.0 and f.max() <= 1.0


# ── MultiScaleGammaComputer ──────────────────────────────────


class TestMultiScaleGammaComputer:
    def test_compute_single_returns_result(self, stripe_field):
        c = MultiScaleGammaComputer(n_bootstrap=100)
        r = c.compute_single(stripe_field, "stripe")
        assert isinstance(r, MultiScaleResult)

    def test_stripe_gamma_near_prevalidated(self, stripe_field):
        c = MultiScaleGammaComputer(n_bootstrap=200)
        r = c.compute_single(stripe_field, "stripe")
        assert abs(r.gamma_b0 - PREVALIDATED_STRIPE_GAMMA) < 0.25

    def test_noise_smaller_abs_gamma(self, stripe_field, noise_field):
        c = MultiScaleGammaComputer(n_bootstrap=100)
        rs = c.compute_single(stripe_field, "stripe")
        rn = c.compute_single(noise_field, "noise")
        assert rs.abs_gamma > rn.abs_gamma

    def test_stripe_organized_noise_not(self, stripe_field, noise_field):
        c = MultiScaleGammaComputer(n_bootstrap=100)
        assert c.compute_single(stripe_field, "s").is_organized is True
        assert c.compute_single(noise_field, "n").is_organized is False

    def test_series_more_points(self, stripe_series):
        c = MultiScaleGammaComputer(n_bootstrap=100)
        r = c.compute_series(stripe_series, "ss")
        assert r.n_scale_points >= len(DEFAULT_SCALES) * 2

    def test_scale_points_bounded(self, stripe_field):
        c = MultiScaleGammaComputer(n_bootstrap=50)
        r = c.compute_single(stripe_field, "t")
        assert 0 <= r.n_scale_points <= len(DEFAULT_SCALES)


# ── MultiScaleValidator ──────────────────────────────────────


class TestMultiScaleValidator:
    def test_validate_returns_report(self, stripe_series):
        v = MultiScaleValidator(n_bootstrap=100)
        rpt = v.validate(stripe_series, label_real=False)
        assert rpt.verdict in ("SUPPORTED", "FALSIFIED", "INCONCLUSIVE")

    def test_separation_positive(self, stripe_series):
        v = MultiScaleValidator(n_bootstrap=100)
        assert v.validate(stripe_series).separation_ratio >= 0.0

    def test_wt_is_organized(self, stripe_series):
        v = MultiScaleValidator(n_bootstrap=200)
        rpt = v.validate(stripe_series)
        assert rpt.wild_type.is_organized is True

    def test_summary_has_key_fields(self, stripe_series):
        v = MultiScaleValidator(n_bootstrap=50)
        s = v.validate(stripe_series).summary()
        assert "gamma_b0" in s
        assert "VERDICT" in s
        assert "Separation" in s
