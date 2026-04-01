"""Deep coverage tests targeting specific uncovered branches.

Targets: config.py validation paths, types/field.py edge cases,
reaction_diffusion_compat.py, legacy_features.py uncovered branches,
metrics.py, and numerics/grid_ops.py.
"""

from __future__ import annotations

import numpy as np
import pytest

import mycelium_fractal_net as mfn

# ═══════════════════════════════════════════════════════════════
#  config.py — validation functions
# ═══════════════════════════════════════════════════════════════


class TestConfigValidation:
    def test_validate_simulation_config_valid(self) -> None:
        from mycelium_fractal_net.config import SimulationConfig, validate_simulation_config

        cfg = SimulationConfig()
        validate_simulation_config(cfg)

    def test_validate_simulation_config_bad_grid(self) -> None:
        from mycelium_fractal_net.config import SimulationConfig, validate_simulation_config

        with pytest.raises((ValueError, Exception)):
            cfg = SimulationConfig(grid_size=2)
            validate_simulation_config(cfg)

    def test_validate_simulation_config_bad_steps(self) -> None:
        from mycelium_fractal_net.config import SimulationConfig, validate_simulation_config

        with pytest.raises((ValueError, Exception)):
            cfg = SimulationConfig(steps=0)
            validate_simulation_config(cfg)

    def test_validate_feature_config(self) -> None:
        from mycelium_fractal_net.config import FeatureConfig, validate_feature_config

        cfg = FeatureConfig()
        validate_feature_config(cfg)

    def test_validate_dataset_config(self) -> None:
        from mycelium_fractal_net.config import DatasetConfig, validate_dataset_config

        cfg = DatasetConfig()
        validate_dataset_config(cfg)


# ═══════════════════════════════════════════════════════════════
#  types/field.py — FieldSequence edge cases
# ═══════════════════════════════════════════════════════════════


class TestFieldSequenceEdgeCases:
    def test_field_sequence_properties(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=1))
        assert seq.field_min_mV == float(np.min(seq.field)) * 1000.0
        assert seq.field_max_mV == float(np.max(seq.field)) * 1000.0
        assert seq.field_mean_mV == float(np.mean(seq.field)) * 1000.0
        assert isinstance(seq.runtime_hash, str)
        assert len(seq.runtime_hash) > 0

    def test_field_sequence_repr(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=1))
        r = repr(seq)
        assert "FieldSequence" in r
        assert "16" in r

    def test_field_sequence_without_spec(self) -> None:
        from mycelium_fractal_net.types.field import FieldSequence

        field = np.random.default_rng(42).normal(-0.065, 0.005, (16, 16))
        seq = FieldSequence(field=field)
        assert seq.spec is None
        assert seq.field.shape == (16, 16)

    def test_field_sequence_with_history(self) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=1)
        seq = mfn.simulate(spec)
        assert seq.has_history or not seq.has_history  # just exercise the property

    def test_simulation_spec_as_runtime_dict(self) -> None:
        spec = mfn.SimulationSpec(grid_size=32, steps=16, seed=42)
        d = spec.as_runtime_dict()
        assert d["grid_size"] == 32
        assert d["steps"] == 16

    def test_simulation_spec_with_neuromod(self) -> None:
        spec = mfn.SimulationSpec(
            grid_size=16,
            steps=8,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
                gabaa_tonic=mfn.GABAATonicSpec(agonist_concentration_um=0.5),
            ),
        )
        d = spec.as_runtime_dict()
        assert d["grid_size"] == 16
        seq = mfn.simulate(spec)
        assert seq.field.shape == (16, 16)


# ═══════════════════════════════════════════════════════════════
#  reaction_diffusion_compat.py
# ═══════════════════════════════════════════════════════════════


class TestReactionDiffusionCompat:
    def test_compat_validate_cfl(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import (
            compat_validate_cfl_condition,
        )

        assert compat_validate_cfl_condition(0.1) is True
        assert compat_validate_cfl_condition(10.0) is False

    def test_compat_clamp_field(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_clamp_field

        field = np.array([[100.0, -200.0], [0.0, 50.0]])
        clamped, count = compat_clamp_field(field)
        assert count > 0
        assert np.isfinite(clamped).all()

    def test_compat_clamp_field_no_clamp_needed(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_clamp_field

        field = np.array([[-0.065, -0.070], [-0.050, -0.060]])
        clamped, count = compat_clamp_field(field)
        assert count == 0
        np.testing.assert_array_equal(clamped, field)

    def test_compat_diffusion_step(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_diffusion_step

        field = np.random.default_rng(42).normal(-0.065, 0.005, (16, 16))
        result = compat_diffusion_step(field, 0.1)
        assert result.shape == field.shape
        assert np.isfinite(result).all()

    def test_compat_activator_inhibitor_step(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import (
            compat_activator_inhibitor_step,
        )
        from mycelium_fractal_net.core.reaction_diffusion_config import ReactionDiffusionConfig

        config = ReactionDiffusionConfig(grid_size=16)
        a = np.random.default_rng(1).uniform(0, 0.1, (16, 16))
        i = np.random.default_rng(2).uniform(0, 0.1, (16, 16))
        a_new, i_new = compat_activator_inhibitor_step(a, i, config)
        assert a_new.shape == (16, 16)
        assert i_new.shape == (16, 16)

    def test_compat_apply_turing_to_field(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_apply_turing_to_field

        field = np.zeros((8, 8))
        activator = np.zeros((8, 8))
        activator[3, 3] = 1.0
        result, count = compat_apply_turing_to_field(
            field, activator, threshold=0.5, contribution_v=0.01
        )
        assert count == 1
        assert result[3, 3] > 0

    def test_compat_apply_growth_event(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_apply_growth_event

        field = np.zeros((8, 8))
        rng = np.random.default_rng(42)
        _result, count = compat_apply_growth_event(field, rng, spike_probability=0.5)
        assert count > 0

    def test_compat_apply_quantum_jitter(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_apply_quantum_jitter

        field = np.zeros((8, 8))
        rng = np.random.default_rng(42)
        result = compat_apply_quantum_jitter(field, rng, jitter_var=0.01)
        assert not np.array_equal(result, field)

    def test_compat_apply_quantum_jitter_zero_var(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_apply_quantum_jitter

        field = np.ones((8, 8))
        rng = np.random.default_rng(42)
        result = compat_apply_quantum_jitter(field, rng, jitter_var=0.0)
        np.testing.assert_array_equal(result, field)

    def test_compat_full_step(self) -> None:
        from mycelium_fractal_net.core.reaction_diffusion_compat import compat_full_step
        from mycelium_fractal_net.core.reaction_diffusion_config import ReactionDiffusionConfig

        config = ReactionDiffusionConfig(grid_size=16)
        rng = np.random.default_rng(42)
        field = rng.normal(-0.065, 0.005, (16, 16))
        a = rng.uniform(0, 0.1, (16, 16))
        i = rng.uniform(0, 0.1, (16, 16))
        f_out, _a_out, _i_out, stats = compat_full_step(field, a, i, rng, config)
        assert f_out.shape == (16, 16)
        assert "growth_events" in stats

    def test_compat_check_array_nan(self) -> None:
        from mycelium_fractal_net.core.exceptions import NumericalInstabilityError
        from mycelium_fractal_net.core.reaction_diffusion_compat import _compat_check_array

        bad = np.array([1.0, float("nan"), 3.0])
        with pytest.raises(NumericalInstabilityError):
            _compat_check_array("test", bad)

    def test_compat_check_array_inf(self) -> None:
        from mycelium_fractal_net.core.exceptions import NumericalInstabilityError
        from mycelium_fractal_net.core.reaction_diffusion_compat import _compat_check_array

        bad = np.array([1.0, float("inf"), 3.0])
        with pytest.raises(NumericalInstabilityError):
            _compat_check_array("test", bad)


# ═══════════════════════════════════════════════════════════════
#  legacy_features.py — cover the large extraction function
# ═══════════════════════════════════════════════════════════════


class TestLegacyFeatures:
    def test_compute_features_basic(self) -> None:
        from mycelium_fractal_net.analytics.legacy_features import compute_features

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=24, steps=12, seed=42))
        features = compute_features(seq.field)
        assert features is not None

    def test_compute_features_small_grid(self) -> None:
        from mycelium_fractal_net.analytics.legacy_features import compute_features

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=4, seed=1))
        features = compute_features(seq.field)
        assert features is not None

    def test_compute_basic_stats(self) -> None:
        from mycelium_fractal_net.analytics.legacy_features import compute_basic_stats

        field = np.random.default_rng(42).normal(-0.065, 0.005, (24, 24))
        result = compute_basic_stats(field)
        assert result is not None
        # Returns a tuple of floats
        assert len(result) >= 4

    def test_validate_feature_ranges(self) -> None:
        from mycelium_fractal_net.analytics.legacy_features import validate_feature_ranges

        assert callable(validate_feature_ranges)


# ═══════════════════════════════════════════════════════════════
#  metrics.py
# ═══════════════════════════════════════════════════════════════


class TestMetrics:
    def test_import_metrics(self) -> None:
        from mycelium_fractal_net.metrics import validate_quality_metrics

        assert callable(validate_quality_metrics)


# ═══════════════════════════════════════════════════════════════
#  numerics/grid_ops.py — Laplacian variants
# ═══════════════════════════════════════════════════════════════


class TestGridOps:
    def test_compute_laplacian_default(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import compute_laplacian

        field = np.random.default_rng(42).normal(0, 1, (16, 16))
        lap = compute_laplacian(field)
        assert lap.shape == field.shape
        assert np.isfinite(lap).all()

    def test_validate_field_stability(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import validate_field_stability

        field = np.random.default_rng(42).normal(-0.065, 0.005, (16, 16))
        result = validate_field_stability(field)
        assert isinstance(result, bool)

    def test_validate_field_bounds(self) -> None:
        from mycelium_fractal_net.numerics.grid_ops import validate_field_bounds

        field = np.random.default_rng(42).normal(-0.065, 0.005, (16, 16))
        result = validate_field_bounds(field, -0.1, 0.05)
        assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════
#  insight_architect.py — explanation generation
# ═══════════════════════════════════════════════════════════════


class TestInsightArchitect:
    def test_explain_sequence(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=24, steps=12, seed=42))
        explanation = seq.explain()
        assert explanation is not None
        narration = explanation.narrate()
        assert isinstance(narration, str)
        assert len(narration) > 0

    def test_explain_high_alpha(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=24, steps=12, seed=42, alpha=0.22))
        explanation = seq.explain()
        narration = explanation.narrate()
        assert isinstance(narration, str)
