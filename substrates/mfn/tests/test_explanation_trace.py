"""Explanation trace tests — verify machine-readable decision audit trail."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.core.explanation_trace import (
    ExplanationTrace,
    build_explanation_trace,
)


def _full_pipeline():
    spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
    seq = mfn.simulate(spec)
    desc = mfn.extract(seq)
    det = mfn.detect(seq)
    fc = mfn.forecast(seq)
    cv = validate_causal_consistency(seq, descriptor=desc, detection=det, forecast=fc)
    return seq, desc, det, fc, cv


class TestExplanationTrace:
    def test_trace_generated(self) -> None:
        _, desc, det, fc, cv = _full_pipeline()
        trace = build_explanation_trace(detection=det, descriptor=desc, forecast=fc, causal=cv)
        assert isinstance(trace, ExplanationTrace)

    def test_trace_has_detection(self) -> None:
        _, _desc, det, _fc, _cv = _full_pipeline()
        trace = build_explanation_trace(detection=det)
        assert trace.detection_trace is not None
        assert trace.detection_trace.final_score >= 0.0
        assert trace.detection_trace.final_label != "unknown"

    def test_trace_has_decision_path(self) -> None:
        _, _desc, det, _fc, _cv = _full_pipeline()
        trace = build_explanation_trace(detection=det)
        assert len(trace.detection_trace.decision_path) > 0

    def test_trace_has_thresholds(self) -> None:
        _, _desc, det, _fc, _cv = _full_pipeline()
        trace = build_explanation_trace(detection=det)
        assert len(trace.detection_trace.thresholds) > 0
        assert "anomaly_baseline" in trace.detection_trace.thresholds

    def test_trace_has_causal(self) -> None:
        _, _desc, _det, _fc, cv = _full_pipeline()
        trace = build_explanation_trace(causal=cv)
        assert trace.causal_trace is not None
        assert trace.causal_trace.rules_evaluated > 0
        assert trace.causal_trace.decision in ("pass", "degraded", "fail")

    def test_trace_to_dict(self) -> None:
        _, desc, det, fc, cv = _full_pipeline()
        trace = build_explanation_trace(detection=det, descriptor=desc, forecast=fc, causal=cv)
        d = trace.to_dict()
        assert d["schema_version"] == "mfn-explanation-trace-v1"
        assert d["detection"] is not None
        assert d["causal"] is not None

    def test_trace_to_json(self) -> None:
        _, desc, det, fc, cv = _full_pipeline()
        trace = build_explanation_trace(detection=det, descriptor=desc, forecast=fc, causal=cv)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            trace.to_json(f.name)
            data = json.loads(Path(f.name).read_text())
        assert data["schema_version"] == "mfn-explanation-trace-v1"
        assert isinstance(data["detection"]["decision_path"], list)

    def test_trace_margin_to_flip(self) -> None:
        _, _desc, det, _fc, _cv = _full_pipeline()
        trace = build_explanation_trace(detection=det)
        assert trace.detection_trace.margin_to_flip >= 0.0

    def test_partial_trace(self) -> None:
        """Trace with only some sections should work."""
        _, _, det, _, _ = _full_pipeline()
        trace = build_explanation_trace(detection=det)
        assert trace.detection_trace is not None
        assert trace.forecast_trace is None
        assert trace.causal_trace is None
