"""Tests for bio/persuasion.py — active inference + intervention + persuadability."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.bio.persuasion import (
    FieldActiveInference,
    FreeEnergyResult,
    InterventionClassifier,
    InterventionLevel,
    PersuadabilityAnalyzer,
    PersuadabilityResult,
)


@pytest.fixture
def target_field() -> np.ndarray:
    return np.random.default_rng(42).standard_normal((8, 8))


# === FieldActiveInference ===


def test_free_energy_basic(target_field: np.ndarray) -> None:
    fai = FieldActiveInference(target_field)
    result = fai.compute_free_energy(target_field)
    assert isinstance(result, FreeEnergyResult)
    # At target: accuracy high, complexity low, free energy low
    assert result.accuracy <= 0.0  # MSE-based, ≤0 by construction
    # Free energy can be negative at exact target (accuracy dominates)
    assert np.isfinite(result.free_energy)


def test_free_energy_at_target_minimal(target_field: np.ndarray) -> None:
    """Free energy at exact target should be near-minimal."""
    fai = FieldActiveInference(target_field)
    fe_at_target = fai.compute_free_energy(target_field).free_energy
    # Random field should have higher free energy
    random_field = np.random.default_rng(99).standard_normal((8, 8))
    fe_random = fai.compute_free_energy(random_field).free_energy
    assert fe_at_target < fe_random


def test_free_energy_with_prediction(target_field: np.ndarray) -> None:
    fai = FieldActiveInference(target_field)
    current = target_field + 0.1
    predicted = target_field + 0.05  # Moving toward target
    result = fai.compute_free_energy(current, predicted)
    assert result.pragmatic_value >= 0.0
    assert result.expected_free_energy != 0.0


def test_free_energy_to_dict(target_field: np.ndarray) -> None:
    fai = FieldActiveInference(target_field)
    result = fai.compute_free_energy(target_field)
    d = result.to_dict()
    assert "free_energy" in d
    assert "accuracy" in d
    assert "complexity" in d
    assert d["field_shape"] == [8, 8]


def test_free_energy_no_nan(target_field: np.ndarray) -> None:
    fai = FieldActiveInference(target_field)
    noisy = target_field + np.random.default_rng(0).standard_normal((8, 8)) * 5
    result = fai.compute_free_energy(noisy)
    assert np.isfinite(result.free_energy)
    assert np.isfinite(result.accuracy)
    assert np.isfinite(result.complexity)


# === InterventionClassifier ===


def test_classify_force() -> None:
    classifier = InterventionClassifier(force_threshold=0.5)
    before = np.zeros((4, 4))
    after = np.ones((4, 4))  # Large change
    level = classifier.classify(before, after)
    assert level == InterventionLevel.FORCE


def test_classify_setpoint() -> None:
    classifier = InterventionClassifier()
    before = np.zeros((4, 4))
    after = np.full((4, 4), 0.2)  # Mean shift but below force
    level = classifier.classify(before, after)
    assert level == InterventionLevel.SETPOINT


def test_classify_persuade() -> None:
    """Tiny, structure-preserving change → PERSUADE."""
    classifier = InterventionClassifier()
    rng = np.random.default_rng(0)
    before = rng.standard_normal((8, 8))
    after = before + rng.standard_normal((8, 8)) * 1e-4
    level = classifier.classify(before, after)
    assert level == InterventionLevel.PERSUADE


def test_classify_with_detail() -> None:
    classifier = InterventionClassifier()
    before = np.zeros((4, 4))
    after = np.ones((4, 4))
    detail = classifier.classify_with_detail(before, after)
    assert "level" in detail
    assert "max_change" in detail
    assert "rms_change" in detail
    assert detail["level"] == "FORCE"


def test_intervention_levels_ordered() -> None:
    assert InterventionLevel.FORCE < InterventionLevel.SETPOINT
    assert InterventionLevel.SETPOINT < InterventionLevel.SIGNAL
    assert InterventionLevel.SIGNAL < InterventionLevel.PERSUADE


# === PersuadabilityAnalyzer ===


def test_persuadability_basic() -> None:
    n = 5
    A = -0.1 * np.eye(n)  # Stable system
    B = np.eye(n)  # Full control
    analyzer = PersuadabilityAnalyzer(horizon=1.0, n_integration_steps=20)
    result = analyzer.compute(A, B)
    assert isinstance(result, PersuadabilityResult)
    assert 0.0 <= result.persuadability_score <= 1.0
    assert result.controllability_rank >= 1
    assert result.total_modes == n


def test_persuadability_full_controllable() -> None:
    """Stable + full input → fully controllable → PERSUADE level."""
    n = 4
    A = -np.eye(n)
    B = np.eye(n)
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.compute(A, B)
    assert result.controllability_rank == n
    assert result.intervention_level == InterventionLevel.PERSUADE


def test_persuadability_uncontrollable() -> None:
    """Zero input → uncontrollable → FORCE level."""
    n = 4
    A = -np.eye(n)
    B = np.zeros((n, 1))
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.compute(A, B)
    assert result.controllability_rank == 0
    assert result.intervention_level == InterventionLevel.FORCE


def test_persuadability_partial_control() -> None:
    """Single input column → partial controllability."""
    n = 4
    A = -0.5 * np.eye(n)
    B = np.zeros((n, 1))
    B[0, 0] = 1.0
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.compute(A, B)
    assert 0 < result.controllability_rank <= n


def test_persuadability_to_dict() -> None:
    A = -np.eye(3)
    B = np.eye(3)
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.compute(A, B)
    d = result.to_dict()
    assert "persuadability_score" in d
    assert "intervention_level" in d
    assert d["intervention_level"] == "PERSUADE"


def test_persuadability_gramian_symmetric() -> None:
    """Gramian must be symmetric positive semidefinite."""
    n = 4
    A = np.random.default_rng(0).standard_normal((n, n)) * 0.1
    A = A - 2 * np.eye(n)  # Make stable
    B = np.random.default_rng(1).standard_normal((n, 2))
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.compute(A, B)
    # Gramian trace should be positive for non-zero B
    assert result.gramian_trace > 0


def test_from_field_history() -> None:
    rng = np.random.default_rng(42)
    T, N = 30, 6
    base = rng.standard_normal((N, N))
    history = np.empty((T, N, N))
    for t in range(T):
        history[t] = base * (0.95**t) + rng.standard_normal((N, N)) * 0.01
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.from_field_history(history, n_modes=5)
    assert isinstance(result, PersuadabilityResult)
    assert 0.0 <= result.persuadability_score <= 1.0


def test_from_field_history_short() -> None:
    """Very short history (2 frames) should still work."""
    history = np.random.default_rng(0).standard_normal((2, 4, 4))
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.from_field_history(history, n_modes=2)
    assert isinstance(result, PersuadabilityResult)


def test_from_field_history_single_frame() -> None:
    """Single frame → degenerate but safe."""
    history = np.random.default_rng(0).standard_normal((1, 4, 4))
    analyzer = PersuadabilityAnalyzer()
    result = analyzer.from_field_history(history, n_modes=2)
    assert result.persuadability_score == 0.5  # Default for degenerate
    assert result.intervention_level == InterventionLevel.FORCE
