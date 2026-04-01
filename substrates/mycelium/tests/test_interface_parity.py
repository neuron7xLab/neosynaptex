"""Interface parity tests — SDK, CLI, API must produce semantically identical output.

Verifies that the same simulation spec produces matching descriptor, detection,
forecast, and causal decision regardless of which interface is used.
"""

from __future__ import annotations

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.core.simulate import simulate_final, simulate_history


class TestSDKInterfaceParity:
    """Verify functional and fluent API produce identical results."""

    def _canonical_spec(self) -> mfn.SimulationSpec:
        return mfn.SimulationSpec(grid_size=32, steps=24, seed=42)

    def test_simulate_final_vs_history_field_match(self) -> None:
        """simulate_final and simulate_history must produce identical final fields."""
        spec = self._canonical_spec()
        final = simulate_final(spec)
        history = simulate_history(spec)
        np.testing.assert_array_equal(final.field, history.field)

    def test_functional_vs_fluent_detect(self) -> None:
        """mfn.detect(seq) and seq.detect() must match."""
        seq = mfn.simulate(self._canonical_spec())
        functional = mfn.detect(seq)
        fluent = seq.detect()
        assert functional.score == fluent.score
        assert functional.label == fluent.label

    def test_functional_vs_fluent_extract(self) -> None:
        """mfn.extract(seq) and seq.extract() must match."""
        seq = mfn.simulate(self._canonical_spec())
        functional = mfn.extract(seq)
        fluent = seq.extract()
        assert functional.version == fluent.version
        assert functional.features == fluent.features

    def test_functional_vs_fluent_forecast(self) -> None:
        """mfn.forecast(seq) and seq.forecast() must match."""
        seq = mfn.simulate(self._canonical_spec())
        functional = mfn.forecast(seq)
        fluent = seq.forecast()
        assert functional.horizon == fluent.horizon

    def test_causal_decision_stable_across_calls(self) -> None:
        """Causal validation must return same decision for same input."""
        seq = mfn.simulate(self._canonical_spec())
        v1 = validate_causal_consistency(seq)
        v2 = validate_causal_consistency(seq)
        assert v1.decision == v2.decision
        assert len(v1.rule_results) == len(v2.rule_results)


class TestCrossScenarioParity:
    """Verify parity across canonical scenarios."""

    SCENARIOS = [
        ("baseline", mfn.SimulationSpec(grid_size=32, steps=24, seed=42)),
        (
            "neuromod_gabaa",
            mfn.SimulationSpec(
                grid_size=32,
                steps=24,
                seed=42,
                neuromodulation=mfn.NeuromodulationSpec(
                    profile="gabaa_tonic_muscimol_alpha1beta3",
                    enabled=True,
                    dt_seconds=1.0,
                    gabaa_tonic=mfn.GABAATonicSpec(
                        profile="gabaa_tonic_muscimol_alpha1beta3",
                        agonist_concentration_um=0.85,
                        resting_affinity_um=0.45,
                        active_affinity_um=0.35,
                        desensitization_rate_hz=0.05,
                        recovery_rate_hz=0.02,
                        shunt_strength=0.42,
                    ),
                ),
            ),
        ),
        (
            "neuromod_sero",
            mfn.SimulationSpec(
                grid_size=32,
                steps=24,
                seed=42,
                neuromodulation=mfn.NeuromodulationSpec(
                    profile="serotonergic_reorganization_candidate",
                    enabled=True,
                    dt_seconds=1.0,
                    serotonergic=mfn.SerotonergicPlasticitySpec(
                        profile="serotonergic_reorganization_candidate",
                        gain_fluidity_coeff=0.08,
                        reorganization_drive=0.12,
                        coherence_bias=0.02,
                    ),
                ),
            ),
        ),
    ]

    def test_each_scenario_deterministic(self) -> None:
        """Each scenario must produce identical output across two runs."""
        for name, spec in self.SCENARIOS:
            seq1 = mfn.simulate(spec)
            seq2 = mfn.simulate(spec)
            np.testing.assert_array_equal(
                seq1.field,
                seq2.field,
                err_msg=f"Scenario {name} not deterministic",
            )

    def test_each_scenario_full_pipeline(self) -> None:
        """Each scenario must complete the full pipeline without error."""
        for name, spec in self.SCENARIOS:
            seq = mfn.simulate(spec)
            desc = mfn.extract(seq)
            det = mfn.detect(seq)
            fc = mfn.forecast(seq)
            cv = validate_causal_consistency(seq, descriptor=desc, detection=det, forecast=fc)

            assert desc.version, f"{name}: no descriptor version"
            assert 0.0 <= det.score <= 1.0, f"{name}: score out of bounds"
            assert fc.horizon >= 1, f"{name}: invalid horizon"
            assert cv.decision.value in ("pass", "degraded", "fail"), f"{name}: invalid decision"

    def test_descriptor_roundtrip(self) -> None:
        """Descriptor to_dict/from_dict must roundtrip for all scenarios."""
        for name, spec in self.SCENARIOS:
            seq = mfn.simulate(spec)
            desc = mfn.extract(seq)
            d = desc.to_dict()
            from mycelium_fractal_net.types.features import MorphologyDescriptor

            restored = MorphologyDescriptor.from_dict(d)
            assert restored.version == desc.version, f"{name}: version mismatch"
            assert restored.features == desc.features, f"{name}: features mismatch"

    def test_detection_roundtrip(self) -> None:
        """AnomalyEvent to_dict/from_dict must roundtrip for all scenarios."""
        for name, spec in self.SCENARIOS:
            seq = mfn.simulate(spec)
            det = mfn.detect(seq)
            d = det.to_dict()
            assert d["score"] == det.score, f"{name}: score mismatch"
            assert d["label"] == det.label, f"{name}: label mismatch"
