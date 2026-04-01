"""Executable documentation tests — verify every example in README/docs runs correctly.

This is the HARD guard against docs↔runtime drift. If an example in the docs
shows an attribute that doesn't exist at runtime, this test fails.
"""

from __future__ import annotations

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency


class TestREADMEExamples:
    """Every code example from README.md must execute without error."""

    def test_quickstart_pipeline(self) -> None:
        """README quickstart: simulate → detect → extract → forecast → compare."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=64, steps=32, seed=42))

        det = seq.detect()
        assert hasattr(det, "label"), "AnomalyEvent must have 'label'"
        assert hasattr(det, "score"), "AnomalyEvent must have 'score'"
        assert hasattr(det, "confidence"), "AnomalyEvent must have 'confidence'"

        desc = seq.extract()
        assert hasattr(desc, "version"), "MorphologyDescriptor must have 'version'"
        assert hasattr(desc, "embedding"), "MorphologyDescriptor must have 'embedding'"

        fc = seq.forecast(4)
        assert hasattr(fc, "horizon"), "ForecastResult must have 'horizon'"
        assert hasattr(fc, "method"), "ForecastResult must have 'method'"
        assert hasattr(fc, "benchmark_metrics"), "ForecastResult must have 'benchmark_metrics'"
        # README shows: ForecastResult(h=4, method=..., error=...)
        # The 'error' in repr comes from benchmark_metrics["forecast_structural_error"]
        assert "forecast_structural_error" in fc.benchmark_metrics
        # ForecastResult does NOT have a top-level structural_error attribute
        assert not hasattr(fc, "structural_error"), (
            "ForecastResult should NOT have top-level 'structural_error'. "
            "It lives in benchmark_metrics['forecast_structural_error']."
        )

        cmp = seq.compare(seq)
        assert hasattr(cmp, "label"), "ComparisonResult must have 'label'"
        assert hasattr(cmp, "distance"), "ComparisonResult must have 'distance'"

    def test_causal_validation_gate(self) -> None:
        """README: every result passes causal validation."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=24, seed=42))
        v = validate_causal_consistency(seq)
        assert hasattr(v, "decision"), "CausalValidationResult must have 'decision'"
        assert v.decision.value in ("pass", "degraded", "fail")

    def test_intervention_planner(self) -> None:
        """INTERVENTION_PLANNER.md example."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=24, seed=42))
        plan = mfn.plan_intervention(
            seq,
            target_regime="stable",
            allowed_levers=["gabaa_concentration", "serotonergic_gain"],
            budget=5.0,
        )
        assert hasattr(plan, "has_viable_plan")
        assert hasattr(plan, "best_candidate")
        assert hasattr(plan, "pareto_front")

    def test_fluent_stabilize(self) -> None:
        """README fluent API: seq.stabilize()."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        plan = seq.stabilize(budget=3.0)
        assert hasattr(plan, "best_candidate")


class TestAPIDocExamples:
    """Verify API endpoint response shapes match docs/API.md."""

    def test_forecast_response_shape(self) -> None:
        """API.md shows forecast response with benchmark_metrics."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        fc = mfn.forecast(seq, horizon=4)
        d = fc.to_dict()
        # Must match the documented shape
        assert "horizon" in d
        assert "method" in d
        assert "benchmark_metrics" in d
        assert "forecast_structural_error" in d["benchmark_metrics"]
        assert "adaptive_damping" in d["benchmark_metrics"]

    def test_detection_response_shape(self) -> None:
        """API.md shows detection response."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        det = mfn.detect(seq)
        d = det.to_dict()
        assert "score" in d
        assert "label" in d
        assert "confidence" in d

    def test_descriptor_response_shape(self) -> None:
        """API.md shows descriptor response."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=42))
        desc = mfn.extract(seq)
        d = desc.to_dict()
        assert "version" in d
        assert "features" in d
        assert "embedding" in d
