"""Contract tests for FractalPreservingInterpolator."""

import json

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from mycelium_fractal_net.core.scale_engine import (
    BoxCountingDimensionEstimator,
    FractalBudgetExceededError,
    FractalInterpolatorConfig,
    FractalPreservingInterpolator,
    MemoryBudgetGuard,
    ScaleRejectedError,
    SpectralCorrector,
)


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def fractal_64(rng):
    noise = rng.random((64, 64))
    return (
        gaussian_filter(noise, 1) * 0.5 + gaussian_filter(noise, 4) * 0.3 + gaussian_filter(noise, 8) * 0.2
    ).astype(np.float64)


# ── D_box preservation ───────────────────────────────────────


class TestFractalContracts:
    def test_single_step_drift(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, r = interp.scale_step(fractal_64, 128)
        assert r.d_box_drift <= 0.05 or r.gate_status == "LOW_CONFIDENCE"

    def test_ladder_preserved(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, j = interp.scale_to(fractal_64, 512)
        assert j.overall_d_box_preserved

    def test_512_closes_debt(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, j = interp.scale_to(fractal_64, 512)
        assert j.scale_512_passed

    def test_identity_no_drift(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, j = interp.scale_to(fractal_64, 64)
        assert j.transitions[0].d_box_drift < 1e-10

    def test_report_serializable(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, j = interp.scale_to(fractal_64, 128)
        assert len(json.dumps(j.model_dump())) > 100

    def test_journey_summary(self, fractal_64):
        interp = FractalPreservingInterpolator()
        _, j = interp.scale_to(fractal_64, 128)
        assert "SCALE" in j.summary()


# ── Scale policy ─────────────────────────────────────────────


class TestScalePolicy:
    def test_1024_blocked_default(self, fractal_64):
        interp = FractalPreservingInterpolator()
        with pytest.raises(FractalBudgetExceededError):
            interp.scale_step(fractal_64, 1024)

    def test_above_1024_rejected(self, fractal_64):
        interp = FractalPreservingInterpolator(FractalInterpolatorConfig(allow_experimental_1024=True))
        with pytest.raises(ScaleRejectedError):
            interp.scale_step(fractal_64, 2048)

    def test_1024_optin_accepted(self):
        guard = MemoryBudgetGuard()
        b = guard.enforce_policy(1024, allow_experimental_1024=True)
        assert b.grid_size == 1024


# ── Box counting ─────────────────────────────────────────────


class TestBoxCounting:
    def test_uniform_low_dbox(self):
        d, r2 = BoxCountingDimensionEstimator().estimate(np.ones((64, 64)) * 0.5)
        assert d <= 1.5 or r2 < 0.8

    def test_checkerboard_high_dbox(self):
        f = np.zeros((64, 64))
        f[::2, ::2] = 1.0
        f[1::2, 1::2] = 1.0
        d, r2 = BoxCountingDimensionEstimator().estimate(f)
        if r2 >= 0.8:
            assert d >= 1.5

    def test_range(self):
        rng = np.random.default_rng(17)
        est = BoxCountingDimensionEstimator()
        for _ in range(20):
            d, _ = est.estimate(rng.random((32, 32)))
            assert 1.0 <= d <= 2.0

    def test_small_grid_low_conf(self):
        est = BoxCountingDimensionEstimator()
        _, r2 = est.estimate(np.random.rand(4, 4))
        assert est.is_low_confidence(np.random.rand(4, 4), r2)


# ── Spectral corrector ───────────────────────────────────────


class TestSpectralCorrector:
    def test_zero_alpha_identity(self, fractal_64):
        sc = SpectralCorrector()
        result = sc.apply(fractal_64, fractal_64, alpha=0.0)
        assert np.allclose(result, fractal_64)

    def test_correction_changes_field(self, fractal_64):
        from scipy.ndimage import zoom

        small = zoom(fractal_64, 0.5, order=3)
        sc = SpectralCorrector()
        corrected = sc.apply(fractal_64, small, alpha=0.8)
        assert not np.allclose(corrected, small)
        assert corrected.shape == small.shape


# ── Memory budget ────────────────────────────────────────────


class TestMemoryBudget:
    def test_small_fits_ram(self):
        b = MemoryBudgetGuard().estimate(32)
        assert b.fits_in_ram
        assert b.recommended_backend == "ram"

    def test_512_memmap_recommended(self):
        b = MemoryBudgetGuard().estimate(512)
        assert b.recommended_backend == "memmap"

    def test_policy_raises_1024(self):
        with pytest.raises(FractalBudgetExceededError):
            MemoryBudgetGuard().enforce_policy(1024)

    def test_policy_raises_2048(self):
        with pytest.raises(ScaleRejectedError):
            MemoryBudgetGuard().enforce_policy(2048)
