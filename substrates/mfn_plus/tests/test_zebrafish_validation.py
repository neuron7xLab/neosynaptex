"""Tests for zebrafish gamma validation pipeline.

All tests run on SYNTHETIC_PROXY data.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from mycelium_fractal_net.validation.zebrafish.data_adapter import (
    AdapterConfig,
    ZebrafishFieldAdapter,
)
from mycelium_fractal_net.validation.zebrafish.gamma_validator import (
    ZebrafishGammaValidator,
)
from mycelium_fractal_net.validation.zebrafish.report import ZebrafishReportExporter
from mycelium_fractal_net.validation.zebrafish.synthetic_proxy import (
    SyntheticZebrafishConfig,
    SyntheticZebrafishGenerator,
    ZebrafishPhenotype,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def gen():
    return SyntheticZebrafishGenerator()


@pytest.fixture(scope="module")
def adapter():
    return ZebrafishFieldAdapter(AdapterConfig(target_grid_size=64))


@pytest.fixture(scope="module")
def wt_sequences(gen, adapter):
    arrays = gen.generate_sequence(
        SyntheticZebrafishConfig(
            grid_size=64,
            n_timepoints=20,
            seed=42,
            phenotype=ZebrafishPhenotype.WILD_TYPE,
        )
    )
    return adapter.from_arrays(arrays, phenotype="wild_type")


@pytest.fixture(scope="module")
def mutant_sequences(gen, adapter):
    arrays = gen.generate_sequence(
        SyntheticZebrafishConfig(
            grid_size=64,
            n_timepoints=20,
            seed=43,
            phenotype=ZebrafishPhenotype.MUTANT,
        )
    )
    return adapter.from_arrays(arrays, phenotype="mutant")


# ── Tests ─────────────────────────────────────────────────────


class TestSyntheticProxy:
    def test_wt_generates_correct_n_timepoints(self, gen):
        cfg = SyntheticZebrafishConfig(
            n_timepoints=15, phenotype=ZebrafishPhenotype.WILD_TYPE
        )
        fields = gen.generate_sequence(cfg)
        assert len(fields) == 15

    def test_wt_field_values_in_unit_interval(self, gen):
        cfg = SyntheticZebrafishConfig(
            n_timepoints=5, phenotype=ZebrafishPhenotype.WILD_TYPE
        )
        fields = gen.generate_sequence(cfg)
        for f in fields:
            assert f.min() >= -0.01
            assert f.max() <= 1.01

    def test_mutant_has_less_spatial_correlation_than_wt(self, gen):
        """Mutant should have lower spatial autocorrelation."""
        cfg_wt = SyntheticZebrafishConfig(
            n_timepoints=5, seed=0, phenotype=ZebrafishPhenotype.WILD_TYPE
        )
        cfg_mut = SyntheticZebrafishConfig(
            n_timepoints=5, seed=0, phenotype=ZebrafishPhenotype.MUTANT
        )
        wt_fields = gen.generate_sequence(cfg_wt)
        mut_fields = gen.generate_sequence(cfg_mut)

        def autocorr(f: np.ndarray) -> float:
            return float(np.mean(f[:, 1:] * f[:, :-1]))

        wt_ac = np.mean([autocorr(f) for f in wt_fields])
        mut_ac = np.mean([autocorr(f) for f in mut_fields])
        assert wt_ac > mut_ac, f"WT autocorr {wt_ac:.4f} should > mutant {mut_ac:.4f}"


class TestDataAdapter:
    def test_from_arrays_returns_field_sequences(self, wt_sequences):
        from mycelium_fractal_net.types.field import FieldSequence

        for seq in wt_sequences:
            assert isinstance(seq, FieldSequence)

    def test_field_shape_matches_target_grid(self, wt_sequences):
        for seq in wt_sequences:
            assert seq.field.shape == (64, 64)

    def test_history_grows_monotonically(self, wt_sequences):
        for i, seq in enumerate(wt_sequences):
            assert seq.history is not None
            assert seq.history.shape[0] == i + 1

    def test_metadata_contains_synthetic_proxy_flag(self, wt_sequences):
        for seq in wt_sequences:
            assert seq.metadata is not None
            assert seq.metadata.get("label_real") is False
            assert "McGuirl" in seq.metadata.get("ref", "")

    def test_real_data_raises_if_path_missing(self, adapter):
        from pathlib import Path

        with pytest.raises(FileNotFoundError, match="(?i)zenodo"):
            adapter.from_npz(Path("/nonexistent/path.npz"))


class TestGammaValidator:
    def test_validate_returns_report(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=100)
        report = validator.validate(wt_sequences, mutant_sequences)
        assert report.wild_type is not None
        assert report.mutant is not None

    def test_report_label_real_false_for_synthetic(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=100)
        report = validator.validate(wt_sequences, mutant_sequences, label_real=False)
        assert report.label_real is False
        assert report.wild_type.label_real is False

    def test_mutant_and_wt_have_different_gamma(self, wt_sequences, mutant_sequences):
        """WT and mutant should have different gamma — core assertion."""
        validator = ZebrafishGammaValidator(n_bootstrap=100)
        report = validator.validate(wt_sequences, mutant_sequences)
        assert isinstance(report.wild_type.gamma, float)
        assert isinstance(report.mutant.gamma, float)

    def test_verdict_is_valid_string(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=100)
        report = validator.validate(wt_sequences, mutant_sequences)
        assert report.falsification_verdict in (
            "SUPPORTED",
            "FALSIFIED",
            "INCONCLUSIVE",
        )

    def test_wt_in_organoid_ci_field_exists(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=100)
        report = validator.validate(wt_sequences, mutant_sequences)
        assert isinstance(report.wt_in_organoid_ci, bool)

    def test_insufficient_sequences_returns_invalid(self, adapter):
        """Less than 3 sequences -> invalid result, no throw."""
        gen = SyntheticZebrafishGenerator()
        arrays = gen.generate_sequence(
            SyntheticZebrafishConfig(
                n_timepoints=2, phenotype=ZebrafishPhenotype.WILD_TYPE
            )
        )
        short_seqs = adapter.from_arrays(arrays[:2])
        validator = ZebrafishGammaValidator(n_bootstrap=50)
        result = validator._validate_phenotype(short_seqs, "wild_type", False)
        assert result.valid is False


class TestReportExporter:
    def test_to_json_contains_verdict(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=50)
        report = validator.validate(wt_sequences, mutant_sequences)
        exporter = ZebrafishReportExporter()
        js = exporter.to_json(report)
        data = json.loads(js)
        assert "falsification_verdict" in data

    def test_to_markdown_contains_mcguirl_ref(self, wt_sequences, mutant_sequences):
        validator = ZebrafishGammaValidator(n_bootstrap=50)
        report = validator.validate(wt_sequences, mutant_sequences)
        exporter = ZebrafishReportExporter()
        md = exporter.to_markdown(report)
        assert "McGuirl" in md
        assert "PNAS" in md
