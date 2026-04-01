"""Tests for TDA-calibrated gamma pipeline.

# SYNTHETIC_PROXY: all tests on synthetic data.
"""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.validation.zebrafish.kde_adapter import (
    CellDensityAdapter,
    KDEConfig,
)
from mycelium_fractal_net.validation.zebrafish.tda_calibrated import (
    CalibratedGammaComputer,
    TDACalibratedValidator,
    TDAFrame,
    TDAFrameExtractor,
    TDAValidationReport,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def stripe_fields():
    from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
        SyntheticZebrafishConfig,
        SyntheticZebrafishGenerator,
        ZebrafishPhenotype,
    )

    gen = SyntheticZebrafishGenerator()
    arrays = gen.generate_sequence(
        SyntheticZebrafishConfig(
            grid_size=64,
            n_timepoints=25,
            seed=42,
            phenotype=ZebrafishPhenotype.WILD_TYPE,
        )
    )
    kde = CellDensityAdapter(KDEConfig(grid_size=64))
    return [kde.compute_density_field(a) for a in arrays]


@pytest.fixture(scope="module")
def spot_fields():
    from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
        SyntheticZebrafishConfig,
        SyntheticZebrafishGenerator,
        ZebrafishPhenotype,
    )

    gen = SyntheticZebrafishGenerator()
    arrays = gen.generate_sequence(
        SyntheticZebrafishConfig(
            grid_size=64,
            n_timepoints=25,
            seed=43,
            phenotype=ZebrafishPhenotype.MUTANT,
        )
    )
    kde = CellDensityAdapter(KDEConfig(grid_size=64))
    return [kde.compute_density_field(a) for a in arrays]


# ── KDE Tests ─────────────────────────────────────────────────


class TestKDEAdapter:
    def test_coordinate_input_gives_correct_shape(self):
        kde = CellDensityAdapter(KDEConfig(grid_size=64))
        coords = np.random.default_rng(0).random((200, 2)) * 100
        field = kde.compute_density_field(coords)
        assert field.shape == (64, 64)

    def test_output_in_unit_interval(self):
        kde = CellDensityAdapter(KDEConfig(grid_size=64))
        coords = np.random.default_rng(1).random((150, 2)) * 50
        field = kde.compute_density_field(coords)
        assert field.min() >= -1e-6
        assert field.max() <= 1.0 + 1e-6

    def test_image_input_normalized(self):
        kde = CellDensityAdapter(KDEConfig(grid_size=32))
        img = np.random.default_rng(2).random((32, 32)) * 500
        field = kde.compute_density_field(img)
        assert field.max() <= 1.0 + 1e-6

    def test_both_formats_produce_valid_fields(self):
        kde = CellDensityAdapter(KDEConfig(grid_size=64))
        from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
            SyntheticZebrafishConfig,
            SyntheticZebrafishGenerator,
            ZebrafishPhenotype,
        )

        gen = SyntheticZebrafishGenerator()
        wt = gen.generate_sequence(
            SyntheticZebrafishConfig(
                n_timepoints=1, seed=0, phenotype=ZebrafishPhenotype.WILD_TYPE
            )
        )
        mut = gen.generate_sequence(
            SyntheticZebrafishConfig(
                n_timepoints=1, seed=0, phenotype=ZebrafishPhenotype.MUTANT
            )
        )
        f_wt = kde.compute_density_field(wt[0])
        f_mut = kde.compute_density_field(mut[0])
        assert f_wt.shape == f_mut.shape == (64, 64)


# ── TDA Frame Tests ────────────────────────────────────���──────


class TestTDAFrameExtractor:
    def test_extract_correct_count(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        assert len(frames) == len(stripe_fields)

    def test_frames_have_valid_beta_0(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        for f in frames:
            assert f.beta_0 >= 0
            assert f.pers_entropy_0 >= 0.0

    def test_stripe_pattern_type_not_always_indeterminate(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        types = {f.pattern_type for f in frames}
        assert types != {"indeterminate"}, f"All frames indeterminate: {types}"

    def test_spot_has_nonneg_beta_0(self, spot_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(spot_fields)
        stripe_b0 = np.mean([f.beta_0 for f in frames])
        assert stripe_b0 >= 0


# ── Calibrated Gamma Tests ────────────────────────────────────


class TestCalibratedGammaComputer:
    def test_compute_returns_result(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        computer = CalibratedGammaComputer(n_bootstrap=100)
        result = computer.compute(frames, "wild_type", label_real=False)
        assert isinstance(result.gamma, float)
        assert result.phenotype == "wild_type"

    def test_label_real_propagates(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        computer = CalibratedGammaComputer(n_bootstrap=50)
        result = computer.compute(frames, "test", label_real=True)
        assert result.label_real is True
        assert result.evidence_type == "real"

    def test_gamma_near_1_check(self, stripe_fields):
        extractor = TDAFrameExtractor()
        frames = extractor.extract_series(stripe_fields)
        computer = CalibratedGammaComputer(
            n_bootstrap=50, gamma_1_tolerance=0.5
        )
        result = computer.compute(frames, "wt", label_real=False)
        expected = abs(result.gamma - 1.0) < 0.5
        assert result.gamma_near_1 == expected

    def test_insufficient_frames_returns_invalid(self):
        frames = [
            TDAFrame(0, 0.0, 1.0, 2, 0, 0.5, 0.1, 0.3, "stripes"),
            TDAFrame(1, 0.0, 1.0, 2, 0, 0.5, 0.1, 0.3, "stripes"),
        ]
        computer = CalibratedGammaComputer(n_bootstrap=50)
        result = computer.compute(frames, "test", label_real=False)
        assert result.valid is False


# ── Full Pipeline Test ────────────────────────────────────────


class TestTDACalibratedValidator:
    def test_full_pipeline_synthetic(self, stripe_fields, spot_fields):
        validator = TDACalibratedValidator(
            kde_config=KDEConfig(grid_size=64),
            n_bootstrap=100,
            verbose=False,
        )
        report = validator.validate(
            stripe_fields, spot_fields, label_real=False
        )
        assert isinstance(report, TDAValidationReport)
        assert report.verdict in ("SUPPORTED", "FALSIFIED", "INCONCLUSIVE")
        assert report.label_real is False
        assert isinstance(report.wt_in_organoid_ci, bool)

    def test_summary_contains_key_fields(self, stripe_fields, spot_fields):
        validator = TDACalibratedValidator(n_bootstrap=50)
        report = validator.validate(stripe_fields, spot_fields)
        summary = report.summary()
        assert "TDA-CALIBRATED" in summary
        assert "gamma=" in summary
        assert "VERDICT" in summary
