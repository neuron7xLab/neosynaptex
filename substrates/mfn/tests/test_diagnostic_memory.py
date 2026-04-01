"""Tests for DiagnosticMemory — system intelligence that learns from outputs."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import mycelium_fractal_net as mfn
from mycelium_fractal_net.core.diagnostic_memory import (
    CalibratedThresholds,
    DiagnosticMemory,
    PredictiveRule,
)
from mycelium_fractal_net.core.unified_engine import UnifiedEngine


@pytest.fixture
def memory_with_data() -> DiagnosticMemory:
    """Memory populated with 30 observations."""
    mem = DiagnosticMemory()
    engine = UnifiedEngine()
    for seed in range(30):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=seed))
        report = engine.analyze(seq)
        mem.observe(report)
    return mem


# ── BASIC OPERATIONS ─────────────────────────────────────────────────────────


def test_observe_and_size() -> None:
    mem = DiagnosticMemory()
    assert mem.size == 0
    engine = UnifiedEngine()
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    report = engine.analyze(seq)
    mem.observe(report)
    assert mem.size == 1


def test_observe_dict() -> None:
    """Can observe raw dict, not just SystemReport."""
    mem = DiagnosticMemory()
    mem.observe({"severity": "info", "hurst_exponent": 1.5, "delta_alpha": 2.0})
    assert mem.size == 1


def test_capacity_eviction() -> None:
    mem = DiagnosticMemory(capacity=5)
    for i in range(10):
        mem.observe({"i": i, "hurst_exponent": float(i)})
    assert mem.size == 5


# ── CORRELATION MATRIX ───────────────────────────────────────────────────────


def test_correlation_matrix(memory_with_data: DiagnosticMemory) -> None:
    corr = memory_with_data.correlation_matrix()
    assert len(corr) > 0
    # Self-correlation should be ~1.0
    for key in corr:
        assert abs(corr[key][key] - 1.0) < 0.01 or corr[key][key] == 0.0


def test_correlation_matrix_too_few() -> None:
    mem = DiagnosticMemory()
    mem.observe({"hurst_exponent": 1.0})
    assert mem.correlation_matrix() == {}


# ── PREDICTIVE RULES ─────────────────────────────────────────────────────────


def test_extract_rules(memory_with_data: DiagnosticMemory) -> None:
    rules = memory_with_data.extract_rules(min_confidence=0.5, min_support=5)
    # Should find at least some rules from 30 observations
    assert isinstance(rules, list)
    for rule in rules:
        assert isinstance(rule, PredictiveRule)
        assert 0.0 <= rule.confidence <= 1.0
        assert rule.support >= 5


def test_rule_matches() -> None:
    rule = PredictiveRule(
        condition_key="hurst_exponent",
        condition_op=">",
        condition_threshold=0.85,
        outcome_key="severity",
        outcome_value="critical",
        confidence=0.9,
        support=20,
        mean_lag=0.0,
    )
    assert rule.matches({"hurst_exponent": 1.5})
    assert not rule.matches({"hurst_exponent": 0.5})
    assert not rule.matches({"other_key": 1.0})


def test_rule_describe() -> None:
    rule = PredictiveRule(
        condition_key="chi_invariant",
        condition_op="<",
        condition_threshold=0.3,
        outcome_key="severity",
        outcome_value="critical",
        confidence=0.94,
        support=15,
        mean_lag=8.0,
    )
    desc = rule.describe()
    assert "chi_invariant" in desc
    assert "0.94" in desc


def test_rule_to_dict() -> None:
    rule = PredictiveRule(
        condition_key="x",
        condition_op=">",
        condition_threshold=1.0,
        outcome_key="y",
        outcome_value="z",
        confidence=0.8,
        support=10,
        mean_lag=5.0,
    )
    d = rule.to_dict()
    json.dumps(d)
    assert "condition" in d
    assert "confidence" in d


# ── THRESHOLD CALIBRATION ────────────────────────────────────────────────────


def test_calibrate_thresholds(memory_with_data: DiagnosticMemory) -> None:
    t = memory_with_data.calibrate_thresholds()
    assert isinstance(t, CalibratedThresholds)
    assert t.n_observations == 30
    assert t.hurst_critical > 0.0
    assert t.delta_alpha_genuine >= 0.0


def test_calibrate_too_few() -> None:
    mem = DiagnosticMemory()
    for i in range(5):
        mem.observe({"hurst_exponent": float(i)})
    t = mem.calibrate_thresholds()
    assert t.hurst_critical == 0.85  # default, not calibrated


# ── PREDICT ──────────────────────────────────────────────────────────────────


def test_predict(memory_with_data: DiagnosticMemory) -> None:
    memory_with_data.extract_rules(min_confidence=0.5, min_support=5)
    seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=99))
    engine = UnifiedEngine()
    report = engine.analyze(seq)
    predictions = memory_with_data.predict(report)
    assert isinstance(predictions, list)
    # Each prediction is a string description
    for p in predictions:
        assert isinstance(p, str)


# ── SAVE / LOAD ──────────────────────────────────────────────────────────────


def test_save_load(memory_with_data: DiagnosticMemory) -> None:
    memory_with_data.extract_rules(min_confidence=0.5, min_support=5)
    memory_with_data.calibrate_thresholds()

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    memory_with_data.save(path)
    assert path.exists()
    content = json.loads(path.read_text())
    assert content["n_observations"] == 30

    mem2 = DiagnosticMemory()
    mem2.load(path)
    assert mem2.size > 0

    path.unlink()


# ── ENGINE LEARN ─────────────────────────────────────────────────────────────


def test_engine_learn() -> None:
    """UnifiedEngine.learn() runs N simulations and extracts intelligence."""
    engine = UnifiedEngine()
    result = engine.learn(n_seeds=10, grid_size=8, steps=10)
    assert result["n_observations"] == 10
    assert "rules" in result
    assert "thresholds" in result
    assert "top_correlations" in result


# ── STATUS ───────────────────────────────────────────────────────────────────


def test_status(memory_with_data: DiagnosticMemory) -> None:
    s = memory_with_data.status()
    assert s["observations"] == 30
    json.dumps(s)
