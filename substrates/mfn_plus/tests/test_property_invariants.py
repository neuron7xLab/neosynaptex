"""Property-based tests for simulation and descriptor invariants.

Uses Hypothesis to verify contracts hold across wide parameter ranges.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

# ═══════════════════════════════════════════════════════════════
#  Simulation invariants
# ═══════════════════════════════════════════════════════════════


class TestSimulationInvariants:
    """Properties that must hold for ALL valid simulation parameters."""

    @given(
        grid_size=st.sampled_from([8, 16, 24, 32]),
        steps=st.integers(min_value=1, max_value=32),
        seed=st.integers(min_value=0, max_value=10000),
        alpha=st.floats(min_value=0.05, max_value=0.24),
    )
    @settings(max_examples=30, deadline=10000)
    def test_field_always_finite(self, grid_size: int, steps: int, seed: int, alpha: float) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=steps,
                seed=seed,
                alpha=alpha,
            )
        )
        assert np.isfinite(seq.field).all(), "Field contains NaN or Inf"

    @given(
        grid_size=st.sampled_from([8, 16, 24]),
        steps=st.integers(min_value=1, max_value=16),
        seed=st.integers(min_value=0, max_value=5000),
    )
    @settings(max_examples=20, deadline=10000)
    def test_field_shape_matches_spec(self, grid_size: int, steps: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=steps,
                seed=seed,
            )
        )
        assert seq.field.shape == (grid_size, grid_size)

    @given(seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=15, deadline=10000)
    def test_deterministic_with_seed(self, seed: int) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=seed)
        s1 = mfn.simulate(spec)
        s2 = mfn.simulate(spec)
        np.testing.assert_array_equal(s1.field, s2.field)

    @given(
        grid_size=st.sampled_from([16, 24]),
        steps=st.integers(min_value=4, max_value=16),
        seed=st.integers(min_value=0, max_value=5000),
    )
    @settings(max_examples=15, deadline=10000)
    def test_field_biophysical_bounds(self, grid_size: int, steps: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=steps,
                seed=seed,
            )
        )
        # Field should be within biophysical bounds: [-95mV, +40mV] in volts
        assert seq.field.min() >= -0.100, f"Field below -100mV: {seq.field.min()}"
        assert seq.field.max() <= 0.045, f"Field above +45mV: {seq.field.max()}"


# ═══════════════════════════════════════════════════════════════
#  Descriptor invariants
# ═══════════════════════════════════════════════════════════════


class TestDescriptorInvariants:
    """Properties that must hold for ALL valid descriptors."""

    @given(
        grid_size=st.sampled_from([16, 24, 32]),
        steps=st.integers(min_value=4, max_value=16),
        seed=st.integers(min_value=0, max_value=5000),
    )
    @settings(max_examples=15, deadline=10000)
    def test_embedding_always_finite(self, grid_size: int, steps: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=steps,
                seed=seed,
            )
        )
        desc = seq.extract()
        assert all(np.isfinite(x) for x in desc.embedding), "Embedding contains NaN/Inf"

    @given(
        grid_size=st.sampled_from([16, 24]),
        seed=st.integers(min_value=0, max_value=3000),
    )
    @settings(max_examples=10, deadline=10000)
    def test_embedding_dimension_constant(self, grid_size: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=8,
                seed=seed,
            )
        )
        desc = seq.extract()
        assert len(desc.embedding) == 57, f"Embedding dim={len(desc.embedding)}, expected 57"

    @given(seed=st.integers(min_value=0, max_value=5000))
    @settings(max_examples=10, deadline=10000)
    def test_descriptor_serialization_roundtrip(self, seed: int) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=seed))
        desc = seq.extract()
        d = desc.to_dict()
        assert isinstance(d, dict)
        assert "version" in d
        assert "embedding" in d


# ═══════════════════════════════════════════════════════════════
#  Detection invariants
# ═══════════════════════════════════════════════════════════════


class TestDetectionInvariants:
    """Properties that must hold for ALL detections."""

    @given(
        grid_size=st.sampled_from([16, 24]),
        steps=st.integers(min_value=4, max_value=16),
        seed=st.integers(min_value=0, max_value=5000),
    )
    @settings(max_examples=15, deadline=10000)
    def test_score_bounded(self, grid_size: int, steps: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=steps,
                seed=seed,
            )
        )
        det = seq.detect()
        assert 0.0 <= det.score <= 1.0, f"Score {det.score} out of [0,1]"

    @given(
        grid_size=st.sampled_from([16, 24]),
        seed=st.integers(min_value=0, max_value=3000),
    )
    @settings(max_examples=10, deadline=10000)
    def test_confidence_bounded(self, grid_size: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=8,
                seed=seed,
            )
        )
        det = seq.detect()
        assert 0.0 <= det.confidence <= 1.0

    @given(seed=st.integers(min_value=0, max_value=5000))
    @settings(max_examples=10, deadline=10000)
    def test_label_in_vocabulary(self, seed: int) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=seed))
        det = seq.detect()
        valid_labels = {"nominal", "watch", "anomalous"}
        assert det.label in valid_labels, f"Label '{det.label}' not in {valid_labels}"


# ═══════════════════════════════════════════════════════════════
#  Causal gate invariants
# ═══════════════════════════════════════════════════════════════


class TestCausalGateInvariants:
    """Properties that must hold for ALL causal validations."""

    @given(
        grid_size=st.sampled_from([16, 24]),
        seed=st.integers(min_value=0, max_value=3000),
    )
    @settings(max_examples=10, deadline=15000)
    def test_clean_simulation_always_passes_strict(self, grid_size: int, seed: int) -> None:
        seq = mfn.simulate(
            mfn.SimulationSpec(
                grid_size=grid_size,
                steps=8,
                seed=seed,
            )
        )
        v = validate_causal_consistency(seq, mode="strict")
        assert v.decision.value in ("pass", "degraded"), (
            f"Clean sim failed causal gate: {v.error_count}E {v.warning_count}W"
        )

    @given(seed=st.integers(min_value=0, max_value=5000))
    @settings(max_examples=10, deadline=15000)
    def test_provenance_hash_deterministic(self, seed: int) -> None:
        spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=seed)
        seq = mfn.simulate(spec)
        v1 = validate_causal_consistency(seq, mode="strict")
        v2 = validate_causal_consistency(seq, mode="strict")
        assert v1.provenance_hash == v2.provenance_hash
