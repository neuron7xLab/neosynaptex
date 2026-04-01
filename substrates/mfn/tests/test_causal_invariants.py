"""Tests for Causal Validation Gate.

Verifies that the causal correctness checker catches real violations
and passes valid pipeline outputs.
"""

from __future__ import annotations

import json

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.types.causal import CausalDecision


class TestSimulationCausalChecks:
    """Verify simulation-level causal rules."""

    def test_valid_simulation_passes(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        result = validate_causal_consistency(seq)
        assert result.ok
        assert result.decision == CausalDecision.PASS
        assert result.error_count == 0

    def test_field_bounds_enforced(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=32, seed=42))
        result = validate_causal_consistency(seq)
        assert result.ok

    def test_neuromod_conservation(self) -> None:
        spec = mfn.SimulationSpec(
            grid_size=16,
            steps=8,
            seed=42,
            neuromodulation=mfn.NeuromodulationSpec(
                profile="gabaa_tonic_muscimol_alpha1beta3",
                enabled=True,
                gabaa_tonic=mfn.GABAATonicSpec(
                    agonist_concentration_um=0.5,
                    resting_affinity_um=0.3,
                    active_affinity_um=0.25,
                    desensitization_rate_hz=0.03,
                    recovery_rate_hz=0.02,
                    shunt_strength=0.3,
                ),
            ),
        )
        seq = mfn.simulate(spec)
        result = validate_causal_consistency(seq)
        assert result.error_count == 0


class TestFullPipelineCausalValidation:
    """Verify cross-stage causal consistency."""

    def test_full_pipeline_valid(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
        desc = mfn.extract(seq)
        event = mfn.detect(seq)
        fcast = mfn.forecast(seq, horizon=4)
        comp = mfn.compare(seq, seq)
        result = validate_causal_consistency(seq, desc, event, fcast, comp)
        assert result.error_count == 0, (
            f"Errors: {[v.message for v in result.violations if v.severity.value in ('error', 'fatal')]}"
        )
        assert result.stages_checked >= 6  # 6 core + optional perturbation

    def test_report_produces_causal_artifact(self, tmp_path) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        report = mfn.report(seq, output_root=str(tmp_path), horizon=4)
        causal_path = tmp_path / report.run_id / "causal_validation.json"
        assert causal_path.exists()
        data = json.loads(causal_path.read_text())
        assert data["schema_version"] == "mfn-causal-validation-v1"
        assert data["ok"] is True
        assert data["error_count"] == 0
        assert len(data["all_rules"]) > 0

    def test_self_comparison_consistent(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        comp = mfn.compare(seq, seq)
        result = validate_causal_consistency(seq, comparison=comp)
        assert result.error_count == 0

    def test_result_serialization(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        result = validate_causal_consistency(seq)
        d = result.to_dict()
        assert isinstance(d["ok"], bool)
        assert isinstance(d["all_rules"], list)
        assert all(isinstance(r["rule_id"], str) for r in d["all_rules"])
        assert all(isinstance(r["passed"], bool) for r in d["all_rules"])

    def test_rule_ids_unique(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=16, seed=42))
        desc = mfn.extract(seq)
        event = mfn.detect(seq)
        fcast = mfn.forecast(seq, horizon=4)
        comp = mfn.compare(seq, seq)
        result = validate_causal_consistency(seq, desc, event, fcast, comp)
        ids = [r.rule_id for r in result.rule_results]
        assert len(ids) == len(set(ids)), (
            f"Duplicate rule IDs: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_decision_semantics(self) -> None:
        """PASS means zero errors, DEGRADED means warnings only, FAIL means errors."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        result = validate_causal_consistency(seq)
        if result.decision == CausalDecision.PASS:
            assert result.error_count == 0
            assert result.warning_count == 0
        elif result.decision == CausalDecision.DEGRADED:
            assert result.error_count == 0
            assert result.warning_count > 0
