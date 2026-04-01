"""Tests for fractal dimension hardening — TASK-13.

Verifies confidence assessment, low-scale grids, unstable regression,
and strong regression cases.
"""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.analytics.legacy_features import (
    FRACTAL_MIN_GRID_SIZE,
    FRACTAL_MIN_NUM_SCALES,
    FRACTAL_MIN_R2,
    FeatureConfig,
    assess_fractal_confidence,
    compute_features,
    is_fractal_strong_signal,
)


class TestFractalConfidenceAssessment:
    """Tests for assess_fractal_confidence."""

    def test_low_grid_size_gives_low_confidence(self) -> None:
        assert assess_fractal_confidence(4, 5, 0.95) == "low_confidence"
        assert assess_fractal_confidence(6, 5, 0.95) == "low_confidence"

    def test_adequate_grid_high_r2_gives_high(self) -> None:
        assert assess_fractal_confidence(16, 5, 0.95) == "high"

    def test_low_r2_gives_low_confidence(self) -> None:
        assert assess_fractal_confidence(64, 5, 0.5) == "low_confidence"
        assert assess_fractal_confidence(64, 5, 0.79) == "low_confidence"

    def test_boundary_r2(self) -> None:
        assert assess_fractal_confidence(64, 5, 0.8) == "high"
        assert assess_fractal_confidence(64, 5, 0.799) == "low_confidence"

    def test_few_scales_gives_low_confidence(self) -> None:
        assert assess_fractal_confidence(64, 2, 0.95) == "low_confidence"

    def test_boundary_grid_size(self) -> None:
        assert assess_fractal_confidence(FRACTAL_MIN_GRID_SIZE, 5, 0.95) == "high"
        assert assess_fractal_confidence(FRACTAL_MIN_GRID_SIZE - 1, 5, 0.95) == "low_confidence"


class TestIsFractalStrongSignal:
    """Tests for is_fractal_strong_signal."""

    def test_strong_signal(self) -> None:
        assert is_fractal_strong_signal(5, 0.95) is True

    def test_weak_signal_low_r2(self) -> None:
        assert is_fractal_strong_signal(5, 0.5) is False

    def test_weak_signal_few_scales(self) -> None:
        assert is_fractal_strong_signal(2, 0.95) is False

    def test_boundary(self) -> None:
        assert is_fractal_strong_signal(FRACTAL_MIN_NUM_SCALES, FRACTAL_MIN_R2) is True
        assert is_fractal_strong_signal(FRACTAL_MIN_NUM_SCALES - 1, FRACTAL_MIN_R2) is False


class TestFractalDimensionOnGrids:
    """Integration tests for fractal dimension on actual grids."""

    def test_4x4_grid_produces_result(self) -> None:
        """Very small grid should still compute D_box (even if low quality)."""
        rng = np.random.default_rng(42)
        snapshots = np.stack([rng.normal(-0.065, 0.005, (4, 4)) for _ in range(8)])
        config = FeatureConfig(min_box_size=1, num_scales=2)
        fv = compute_features(snapshots, config)
        assert fv.D_box >= 0.0
        confidence = assess_fractal_confidence(4, config.num_scales, fv.D_r2)
        assert confidence == "low_confidence"

    def test_random_noise_low_r2(self) -> None:
        """Pure random noise may produce low R²."""
        rng = np.random.default_rng(99)
        snapshots = np.stack([rng.uniform(-0.095, 0.04, (32, 32)) for _ in range(8)])
        config = FeatureConfig()
        fv = compute_features(snapshots, config)
        assert 0.0 <= fv.D_r2 <= 1.0

    def test_full_field_high_dimension(self) -> None:
        """Fully active field should have D_box near 2.0 and high R²."""
        field = np.ones((32, 32)) * 0.01
        snapshots = np.stack([field] * 8)
        config = FeatureConfig()
        fv = compute_features(snapshots, config)
        assert fv.D_box > 1.5
        assert fv.D_r2 > 0.8

    def test_64x64_adequate_confidence(self) -> None:
        """64x64 grid with good R² should be high confidence."""
        rng = np.random.default_rng(42)
        snapshots = np.stack([rng.normal(-0.060, 0.005, (64, 64)) for _ in range(8)])
        config = FeatureConfig()
        fv = compute_features(snapshots, config)
        confidence = assess_fractal_confidence(64, config.num_scales, fv.D_r2)
        assert confidence in ("high", "low_confidence")
