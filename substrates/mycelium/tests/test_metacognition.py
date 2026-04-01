"""Tests for MetaCognitiveLayer — system's awareness of its own epistemic state."""

from __future__ import annotations

import json

import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.metacognition import MetaCognitiveLayer, MetaCognitiveReport
from mycelium_fractal_net.core.unified_engine import UnifiedEngine


@pytest.fixture(scope="module")
def engine_and_report() -> tuple:
    engine = UnifiedEngine()
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
    report = engine.analyze(seq)
    return engine, report


def test_evaluate_returns_report(engine_and_report: tuple) -> None:
    _engine, report = engine_and_report
    meta = MetaCognitiveLayer()
    mc = meta.evaluate(report)
    assert isinstance(mc, MetaCognitiveReport)


def test_coherence_bounded(engine_and_report: tuple) -> None:
    _engine, report = engine_and_report
    mc = MetaCognitiveLayer().evaluate(report)
    assert 0.0 <= mc.coherence_score <= 1.0
    assert mc.n_signals_agree <= mc.n_signals_total


def test_confidence_bounded(engine_and_report: tuple) -> None:
    _engine, report = engine_and_report
    mc = MetaCognitiveLayer().evaluate(report)
    assert 0.0 <= mc.confidence <= 1.0


def test_surprise_non_negative(engine_and_report: tuple) -> None:
    _engine, _report = engine_and_report
    meta = MetaCognitiveLayer()
    # Feed several reports to build distribution
    for seed in range(10):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=seed))
        r = UnifiedEngine().analyze(seq)
        meta.evaluate(r)
    mc = meta.evaluate(engine_and_report[1])
    assert mc.surprise >= 0.0


def test_summary_format(engine_and_report: tuple) -> None:
    mc = MetaCognitiveLayer().evaluate(engine_and_report[1])
    s = mc.summary()
    assert "[META]" in s
    assert "coherence=" in s
    assert "confidence=" in s
    assert "surprise=" in s


def test_interpretation_not_empty(engine_and_report: tuple) -> None:
    mc = MetaCognitiveLayer().evaluate(engine_and_report[1])
    interp = mc.interpretation()
    assert len(interp) > 20


def test_to_dict_json(engine_and_report: tuple) -> None:
    mc = MetaCognitiveLayer().evaluate(engine_and_report[1])
    d = mc.to_dict()
    json.dumps(d)
    assert "coherence_score" in d
    assert "confidence" in d
    assert "surprise" in d


def test_contradiction_detection() -> None:
    """Fabricate contradictory report — coherence should drop."""

    class FakeReport:
        severity = "stable"
        is_critical_slowing = True  # contradicts stable
        basin_stability = 0.2  # contradicts stable
        ews_score = 0.9  # contradicts nominal
        anomaly_label = "nominal"  # contradicts high EWS
        anomaly_score = 0.5
        spectral_expanding = False  # contradicts stable
        causal_decision = "pass"
        delta_alpha = 2.0
        hurst_exponent = 1.5
        chi_invariant = 0.3

    mc = MetaCognitiveLayer().evaluate(FakeReport())
    assert mc.coherence_score < 0.5, f"Expected low coherence, got {mc.coherence_score}"
    assert len(mc.contradictions) >= 3


def test_high_coherence_normal_report(engine_and_report: tuple) -> None:
    """Normal report should have reasonable coherence."""
    mc = MetaCognitiveLayer().evaluate(engine_and_report[1])
    # Normal simulation typically has coherent signals
    assert mc.coherence_score >= 0.6


def test_engine_has_metacognition() -> None:
    engine = UnifiedEngine()
    assert engine.metacognition is not None
    # Use qualname check: sys.modules clearing in test_layer_boundaries
    # can cause class identity mismatch with isinstance.
    assert type(engine.metacognition).__qualname__ == "MetaCognitiveLayer"
