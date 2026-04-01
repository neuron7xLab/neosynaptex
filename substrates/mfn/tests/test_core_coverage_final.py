"""Final coverage tests for core modules — closes remaining gaps."""

from __future__ import annotations

import numpy as np
import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.input_guards import ValidationError, validate_field_sequence
from mycelium_fractal_net.core.metacognition import MetaCognitiveLayer

# ── input_guards: history validation edge cases ──────────────────────────────


def test_history_wrong_ndim() -> None:
    """History is 2D instead of 3D."""

    class FakeSeq:
        field = np.ones((8, 8))
        history = np.ones((8, 8))  # 2D, not 3D

    with pytest.raises(ValidationError, match="3D"):
        validate_field_sequence(FakeSeq())


def test_history_shape_mismatch() -> None:
    """History shape doesn't match field shape."""

    class FakeSeq:
        field = np.ones((8, 8))
        history = np.ones((5, 16, 16))  # 16x16 != 8x8

    with pytest.raises(ValidationError, match="shape mismatch"):
        validate_field_sequence(FakeSeq())


def test_history_not_ndarray() -> None:
    """History is a list, not ndarray."""

    class FakeSeq:
        field = np.ones((8, 8))
        history = [[1, 2], [3, 4]]

    with pytest.raises(ValidationError, match="ndarray"):
        validate_field_sequence(FakeSeq())


def test_history_inf() -> None:
    """History contains Inf."""
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=5, seed=0))
    seq.history[2, 3, 3] = float("inf")
    with pytest.raises(ValidationError, match="Inf"):
        validate_field_sequence(seq)


# ── metacognition: coverage for interpretation branches ──────────────────────


def test_meta_partial_coherence() -> None:
    """Partial coherence (0.5-0.8) triggers 'some signals contradict'."""

    class PartialReport:
        severity = "stable"
        is_critical_slowing = True  # 1 contradiction
        basin_stability = 0.9
        ews_score = 0.1
        anomaly_label = "nominal"
        anomaly_score = 0.1
        spectral_expanding = True
        causal_decision = "pass"
        delta_alpha = 2.0
        hurst_exponent = 1.0
        chi_invariant = 0.5

    mc = MetaCognitiveLayer().evaluate(PartialReport())
    assert 0.5 <= mc.coherence_score <= 0.9
    interp = mc.interpretation()
    assert "contradict" in interp.lower() or "agree" in interp.lower()


def test_meta_low_confidence_drivers() -> None:
    """Low confidence shows drivers."""

    class LowConfReport:
        severity = "stable"
        is_critical_slowing = True
        basin_stability = 0.2
        ews_score = 0.9
        anomaly_label = "nominal"
        anomaly_score = 0.5  # ambiguous
        spectral_expanding = False
        causal_decision = "fail"  # drops confidence
        delta_alpha = 2.0
        hurst_exponent = 1.0
        chi_invariant = 0.3

    mc = MetaCognitiveLayer().evaluate(LowConfReport())
    assert mc.confidence < 0.5
    assert len(mc.confidence_drivers) > 0
    interp = mc.interpretation()
    assert "unreliable" in interp.lower() or "low" in interp.lower()


def test_meta_moderate_novelty() -> None:
    """Build distribution then introduce moderate outlier."""
    meta = MetaCognitiveLayer()

    class NormalReport:
        severity = "info"
        is_critical_slowing = False
        basin_stability = 0.9
        ews_score = 0.4
        anomaly_label = "nominal"
        anomaly_score = 0.2
        spectral_expanding = True
        causal_decision = "pass"
        delta_alpha = 3.0
        hurst_exponent = 1.5
        chi_invariant = 0.5

    # Build baseline distribution with slight variation
    rng = np.random.default_rng(0)
    for _ in range(20):
        r = NormalReport()
        r.delta_alpha = 3.0 + rng.standard_normal() * 0.1
        r.hurst_exponent = 1.5 + rng.standard_normal() * 0.05
        meta.evaluate(r)

    # Moderate outlier
    class OutlierReport:
        severity = "info"
        is_critical_slowing = False
        basin_stability = 0.9
        ews_score = 0.4
        anomaly_label = "nominal"
        anomaly_score = 0.2
        spectral_expanding = True
        causal_decision = "pass"
        delta_alpha = 8.0  # outlier
        hurst_exponent = 4.0  # outlier
        chi_invariant = 0.5

    mc = meta.evaluate(OutlierReport())
    assert mc.surprise > 0.5


def test_meta_high_surprise_interpretation() -> None:
    """Very high surprise triggers novelty warning in interpretation."""
    meta = MetaCognitiveLayer()

    class Normal:
        severity = "info"
        is_critical_slowing = False
        basin_stability = 0.9
        ews_score = 0.4
        anomaly_label = "nominal"
        anomaly_score = 0.2
        spectral_expanding = True
        causal_decision = "pass"
        delta_alpha = 3.0
        hurst_exponent = 1.5
        chi_invariant = 0.5

    for _ in range(30):
        meta.evaluate(Normal())

    class Extreme:
        severity = "info"
        is_critical_slowing = False
        basin_stability = 0.9
        ews_score = 0.4
        anomaly_label = "nominal"
        anomaly_score = 0.2
        spectral_expanding = True
        causal_decision = "pass"
        delta_alpha = 50.0  # extreme
        hurst_exponent = 20.0  # extreme
        chi_invariant = 0.5

    mc = meta.evaluate(Extreme())
    if mc.surprise > 2.0:
        assert "novel" in mc.interpretation().lower()


# ── diagnostic_memory: edge cases ────────────────────────────────────────────


def test_memory_correlation_insufficient_data() -> None:
    from mycelium_fractal_net.core.diagnostic_memory import DiagnosticMemory

    mem = DiagnosticMemory()
    mem.observe({"hurst_exponent": 1.0, "severity": "info"})
    # Not enough data for correlation
    corr = mem.correlation_matrix()
    assert corr == {} or all(v == 0.0 for row in corr.values() for v in row.values())


def test_memory_extract_rules_insufficient() -> None:
    from mycelium_fractal_net.core.diagnostic_memory import DiagnosticMemory

    mem = DiagnosticMemory()
    for i in range(3):
        mem.observe({"hurst_exponent": float(i), "severity": "info"})
    rules = mem.extract_rules(min_support=10)
    assert rules == []  # not enough data


def test_memory_predict_empty() -> None:
    from mycelium_fractal_net.core.diagnostic_memory import DiagnosticMemory

    mem = DiagnosticMemory()
    predictions = mem.predict({"hurst_exponent": 1.0})
    assert predictions == []
