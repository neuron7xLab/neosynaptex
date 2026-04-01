"""Smoke tests for PhaseTransitionDetector.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests phase detection and transition tracking for criticality.

References
----------
docs/SPEC.md#P0-4
"""

from __future__ import annotations

import pytest

from bnsyn.criticality import CriticalPhase, PhaseTransition, PhaseTransitionDetector


def test_detector_creation() -> None:
    """Test PhaseTransitionDetector initialization."""
    detector = PhaseTransitionDetector()
    assert detector.current_phase() == CriticalPhase.UNKNOWN

    # invalid thresholds
    with pytest.raises(ValueError, match="subcritical_threshold must be less than"):
        PhaseTransitionDetector(subcritical_threshold=1.1, supercritical_threshold=1.0)

    with pytest.raises(ValueError, match="history_size must be positive"):
        PhaseTransitionDetector(history_size=0)


def test_phase_classification() -> None:
    """Test phase classification from sigma values."""
    detector = PhaseTransitionDetector(
        subcritical_threshold=0.95,
        supercritical_threshold=1.05,
    )

    # subcritical
    new_phase = detector.observe(sigma=0.8, step=0)
    assert detector.current_phase() == CriticalPhase.SUBCRITICAL
    assert new_phase is None  # no transition yet

    # stay subcritical
    new_phase = detector.observe(sigma=0.9, step=1)
    assert new_phase is None

    # transition to critical
    new_phase = detector.observe(sigma=1.0, step=2)
    assert new_phase == CriticalPhase.CRITICAL
    assert detector.current_phase() == CriticalPhase.CRITICAL

    # transition to supercritical
    new_phase = detector.observe(sigma=1.1, step=3)
    assert new_phase == CriticalPhase.SUPERCRITICAL
    assert detector.current_phase() == CriticalPhase.SUPERCRITICAL


def test_transition_recording() -> None:
    """Test transition event recording."""
    detector = PhaseTransitionDetector()

    # create a sequence that causes transitions
    sigmas = [0.8, 0.85, 0.9, 1.0, 1.05, 1.1]
    for i, sigma in enumerate(sigmas):
        detector.observe(sigma, step=i)

    transitions = detector.get_transitions()
    assert len(transitions) >= 1  # at least one transition

    # check transition structure
    if len(transitions) > 0:
        t = transitions[0]
        assert isinstance(t, PhaseTransition)
        assert t.step >= 0
        assert isinstance(t.from_phase, CriticalPhase)
        assert isinstance(t.to_phase, CriticalPhase)
        assert t.sharpness >= 0.0


def test_transition_callbacks() -> None:
    """Test transition callbacks."""
    detector = PhaseTransitionDetector()

    transitions_received = []

    def callback(t: PhaseTransition) -> None:
        transitions_received.append(t)

    detector.on_transition(callback)

    # trigger transitions
    detector.observe(sigma=0.8, step=0)
    detector.observe(sigma=1.1, step=1)  # subcritical -> supercritical

    assert len(transitions_received) == 1
    assert transitions_received[0].from_phase == CriticalPhase.SUBCRITICAL
    assert transitions_received[0].to_phase == CriticalPhase.SUPERCRITICAL


def test_sigma_derivative() -> None:
    """Test sigma derivative computation."""
    detector = PhaseTransitionDetector()

    # not enough history
    deriv = detector.sigma_derivative()
    assert deriv is None

    # add observations
    detector.observe(sigma=0.8, step=0)
    detector.observe(sigma=0.9, step=10)

    deriv = detector.sigma_derivative()
    assert deriv is not None
    assert deriv > 0  # sigma increasing


def test_time_in_phase() -> None:
    """Test time in phase tracking."""
    detector = PhaseTransitionDetector()

    detector.observe(sigma=0.8, step=0)
    detector.observe(sigma=0.85, step=5)
    detector.observe(sigma=0.9, step=10)

    # stayed in subcritical phase
    time_in = detector.time_in_phase(step=10)
    assert time_in == 10  # entered at step 0

    # transition to critical
    detector.observe(sigma=1.0, step=15)
    time_in = detector.time_in_phase(step=20)
    assert time_in == 5  # entered at step 15


def test_history_tracking() -> None:
    """Test sigma and phase history."""
    detector = PhaseTransitionDetector(history_size=5)

    for i in range(10):
        detector.observe(sigma=0.8 + i * 0.05, step=i)

    sigma_hist = detector.get_sigma_history()
    phase_hist = detector.get_phase_history()

    # history capped at 5
    assert len(sigma_hist) <= 5
    assert len(phase_hist) <= 5

    # most recent is last
    assert sigma_hist[-1][0] == 9


def test_determinism() -> None:
    """Test deterministic behavior."""
    sigma_sequence = [0.8, 0.9, 1.0, 1.05, 1.1, 1.0, 0.95, 0.9]

    # First run
    detector1 = PhaseTransitionDetector()
    for i, sigma in enumerate(sigma_sequence):
        detector1.observe(sigma, step=i)
    transitions1 = detector1.get_transitions()

    # Second run
    detector2 = PhaseTransitionDetector()
    for i, sigma in enumerate(sigma_sequence):
        detector2.observe(sigma, step=i)
    transitions2 = detector2.get_transitions()

    # Should produce identical results
    assert len(transitions1) == len(transitions2)
    for t1, t2 in zip(transitions1, transitions2):
        assert t1.step == t2.step
        assert t1.from_phase == t2.from_phase
        assert t1.to_phase == t2.to_phase
        assert t1.sigma_before == pytest.approx(t2.sigma_before)
        assert t1.sigma_after == pytest.approx(t2.sigma_after)
