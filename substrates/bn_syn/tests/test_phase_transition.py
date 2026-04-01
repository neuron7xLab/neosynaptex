"""Smoke tests for phase transition detector.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests critical phase classification and transition detection.

References
----------
docs/SPEC.md#P0-4
"""

from __future__ import annotations

import pytest

from bnsyn.criticality import CriticalPhase, PhaseTransition, PhaseTransitionDetector


def test_phase_classification() -> None:
    """Test phase classification boundaries."""
    detector = PhaseTransitionDetector(
        subcritical_threshold=0.95,
        supercritical_threshold=1.05,
    )

    # subcritical
    phase = detector._classify_phase(0.8)
    assert phase == CriticalPhase.SUBCRITICAL

    # critical
    phase = detector._classify_phase(1.0)
    assert phase == CriticalPhase.CRITICAL

    # supercritical
    phase = detector._classify_phase(1.2)
    assert phase == CriticalPhase.SUPERCRITICAL


def test_detector_initialization() -> None:
    """Test detector initialization and validation."""
    detector = PhaseTransitionDetector()
    assert detector.subcritical_threshold == 0.95
    assert detector.supercritical_threshold == 1.05
    assert detector.current_phase() == CriticalPhase.UNKNOWN

    # invalid thresholds
    with pytest.raises(ValueError, match="subcritical_threshold must be less than"):
        PhaseTransitionDetector(subcritical_threshold=1.1, supercritical_threshold=1.0)


def test_transition_detection() -> None:
    """Test transition detection."""
    detector = PhaseTransitionDetector(
        subcritical_threshold=0.95,
        supercritical_threshold=1.05,
    )

    # start subcritical
    detector.observe(sigma=0.8, step=0)
    assert detector.current_phase() == CriticalPhase.SUBCRITICAL

    # stay subcritical
    detector.observe(sigma=0.85, step=1)
    assert detector.current_phase() == CriticalPhase.SUBCRITICAL

    # transition to critical
    new_phase = detector.observe(sigma=1.0, step=2)
    assert new_phase == CriticalPhase.CRITICAL
    assert detector.current_phase() == CriticalPhase.CRITICAL

    # transition to supercritical
    new_phase = detector.observe(sigma=1.15, step=3)
    assert new_phase == CriticalPhase.SUPERCRITICAL
    assert detector.current_phase() == CriticalPhase.SUPERCRITICAL

    # check transitions recorded
    transitions = detector.get_transitions()
    assert len(transitions) == 2
    assert transitions[0].from_phase == CriticalPhase.SUBCRITICAL
    assert transitions[0].to_phase == CriticalPhase.CRITICAL
    assert transitions[1].from_phase == CriticalPhase.CRITICAL
    assert transitions[1].to_phase == CriticalPhase.SUPERCRITICAL


def test_transition_callbacks() -> None:
    """Test transition callback mechanism."""
    detector = PhaseTransitionDetector()

    transitions_observed: list[PhaseTransition] = []

    def on_transition(t: PhaseTransition) -> None:
        transitions_observed.append(t)

    detector.on_transition(on_transition)

    # trigger transitions
    detector.observe(sigma=0.8, step=0)
    detector.observe(sigma=1.0, step=1)
    detector.observe(sigma=1.2, step=2)

    assert len(transitions_observed) == 2
    assert transitions_observed[0].to_phase == CriticalPhase.CRITICAL
    assert transitions_observed[1].to_phase == CriticalPhase.SUPERCRITICAL


def test_sigma_derivative() -> None:
    """Test sigma derivative calculation."""
    detector = PhaseTransitionDetector()

    # insufficient history
    assert detector.sigma_derivative() is None

    # add observations
    detector.observe(sigma=0.8, step=0)
    detector.observe(sigma=0.85, step=1)
    detector.observe(sigma=0.9, step=2)
    detector.observe(sigma=0.95, step=3)
    detector.observe(sigma=1.0, step=4)

    deriv = detector.sigma_derivative()
    assert deriv is not None
    assert deriv > 0  # increasing sigma


def test_time_in_phase() -> None:
    """Test time in phase tracking."""
    detector = PhaseTransitionDetector()

    detector.observe(sigma=0.8, step=0)
    assert detector.time_in_phase(step=0) == 0
    assert detector.time_in_phase(step=5) == 5

    # transition to critical
    detector.observe(sigma=1.0, step=10)
    assert detector.time_in_phase(step=10) == 0
    assert detector.time_in_phase(step=15) == 5


def test_history_size_limit() -> None:
    """Test history size limit enforcement."""
    detector = PhaseTransitionDetector(history_size=10)

    # add more observations than history size
    for i in range(20):
        detector.observe(sigma=0.8 + i * 0.01, step=i)

    history = detector.get_sigma_history()
    assert len(history) == 10  # limited to history_size


def test_determinism() -> None:
    """Test deterministic behavior with same inputs."""
    detector1 = PhaseTransitionDetector()
    detector2 = PhaseTransitionDetector()

    sigmas = [0.8, 0.85, 0.9, 1.0, 1.05, 1.1, 1.15, 1.2]

    for i, sigma in enumerate(sigmas):
        detector1.observe(sigma=sigma, step=i)
        detector2.observe(sigma=sigma, step=i)

    # transitions should be identical
    t1 = detector1.get_transitions()
    t2 = detector2.get_transitions()

    assert len(t1) == len(t2)
    for i in range(len(t1)):
        assert t1[i].step == t2[i].step
        assert t1[i].from_phase == t2[i].from_phase
        assert t1[i].to_phase == t2[i].to_phase
