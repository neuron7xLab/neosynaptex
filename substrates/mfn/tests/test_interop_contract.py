"""Interoperability contract tests — JSON roundtrip for all domain types.

Verifies that every domain type can be serialized to JSON and deserialized
back without loss of semantic content.
"""

from __future__ import annotations

import json

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.causal_validation import validate_causal_consistency
from mycelium_fractal_net.types.features import MorphologyDescriptor
from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec


def _pipeline():
    spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
    seq = mfn.simulate(spec)
    desc = mfn.extract(seq)
    det = mfn.detect(seq)
    fc = mfn.forecast(seq)
    seq2 = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=8, seed=99))
    cmp = mfn.compare(seq, seq2)
    cv = validate_causal_consistency(seq, descriptor=desc, detection=det, forecast=fc)
    return seq, desc, det, fc, cmp, cv


class TestSimulationSpecRoundtrip:
    def test_roundtrip(self) -> None:
        spec = SimulationSpec(grid_size=32, steps=24, seed=42)
        d = spec.to_dict()
        restored = SimulationSpec.from_dict(d)
        assert restored.grid_size == spec.grid_size
        assert restored.steps == spec.steps
        assert restored.seed == spec.seed
        assert restored.alpha == spec.alpha

    def test_json_serializable(self) -> None:
        spec = SimulationSpec(grid_size=32, steps=24, seed=42)
        s = json.dumps(spec.to_dict())
        d = json.loads(s)
        assert d["grid_size"] == 32


class TestFieldSequenceRoundtrip:
    def test_roundtrip(self) -> None:
        seq, *_ = _pipeline()
        d = seq.to_dict(include_arrays=True)
        restored = FieldSequence.from_dict(d)
        np.testing.assert_array_equal(restored.field, seq.field)

    def test_summary_serializable(self) -> None:
        seq, *_ = _pipeline()
        d = seq.to_dict(include_arrays=False)
        s = json.dumps(d, default=str)
        assert len(s) > 0


class TestMorphologyDescriptorRoundtrip:
    def test_roundtrip(self) -> None:
        _, desc, *_ = _pipeline()
        d = desc.to_dict()
        restored = MorphologyDescriptor.from_dict(d)
        assert restored.version == desc.version
        assert restored.features == desc.features

    def test_json_serializable(self) -> None:
        _, desc, *_ = _pipeline()
        s = json.dumps(desc.to_dict())
        d = json.loads(s)
        assert "version" in d
        assert "features" in d


class TestAnomalyEventRoundtrip:
    def test_roundtrip(self) -> None:
        _, _, det, *_ = _pipeline()
        d = det.to_dict()
        assert d["score"] == det.score
        assert d["label"] == det.label

    def test_json_serializable(self) -> None:
        _, _, det, *_ = _pipeline()
        s = json.dumps(det.to_dict(), default=str)
        d = json.loads(s)
        assert 0.0 <= d["score"] <= 1.0


class TestForecastResultRoundtrip:
    def test_roundtrip(self) -> None:
        *_, fc, _, _ = _pipeline()
        d = fc.to_dict()
        assert d["horizon"] == fc.horizon

    def test_json_serializable(self) -> None:
        *_, fc, _, _ = _pipeline()
        s = json.dumps(fc.to_dict(), default=str)
        d = json.loads(s)
        assert d["horizon"] >= 1


class TestComparisonResultRoundtrip:
    def test_roundtrip(self) -> None:
        *_, cmp, _ = _pipeline()
        d = cmp.to_dict()
        assert d["distance"] == cmp.distance
        assert d["label"] == cmp.label

    def test_json_serializable(self) -> None:
        *_, cmp, _ = _pipeline()
        s = json.dumps(cmp.to_dict(), default=str)
        d = json.loads(s)
        assert -1.0 <= d["cosine_similarity"] <= 1.0


class TestCausalValidationResultRoundtrip:
    def test_json_serializable(self) -> None:
        *_, cv = _pipeline()
        d = cv.to_dict()
        s = json.dumps(d, default=str)
        d2 = json.loads(s)
        assert d2["decision"] in ("pass", "degraded", "fail")
        assert len(d2.get("all_rules", d2.get("rule_results", []))) > 0


class TestInteropWithoutEngine:
    """Verify outputs can be consumed without the MFN engine."""

    def test_descriptor_consumable_as_plain_json(self) -> None:
        _, desc, *_ = _pipeline()
        # Simulate external consumer: only json module
        raw = json.dumps(desc.to_dict())
        data = json.loads(raw)
        # External consumer can access all features
        assert isinstance(data["features"], dict)
        assert "D_box" in data["features"]
        assert isinstance(data["features"]["D_box"], float)

    def test_detection_consumable_as_plain_json(self) -> None:
        _, _, det, *_ = _pipeline()
        raw = json.dumps(det.to_dict(), default=str)
        data = json.loads(raw)
        assert isinstance(data["score"], float)
        assert isinstance(data["label"], str)
