"""
Property-based tests for CognitiveRhythm invariants.

Tests formal invariants defined in docs/FORMAL_INVARIANTS.md for the
wake/sleep cognitive rhythm system.

Invariants covered:
- INV-WS-S1: Duration Positivity
- INV-WS-S2: Phase Validity (phase ∈ {"wake", "sleep"})
- INV-WS-S3: Counter Non-Negativity
- INV-WS-L1: Eventual Phase Transition
- INV-WS-L2: Step Progress
- INV-WS-M1: Cycle Periodicity
- INV-WS-M2: Phase Alternation
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm

# Fixed seed for deterministic property tests
RHYTHM_TEST_SEED = 42


# ============================================================================
# Test Strategies
# ============================================================================


@st.composite
def duration_strategy(draw):
    """Generate valid positive durations for wake/sleep."""
    return draw(st.integers(min_value=1, max_value=100))


@st.composite
def step_count_strategy(draw):
    """Generate step counts for rhythm testing."""
    return draw(st.integers(min_value=1, max_value=200))


# ============================================================================
# Safety Invariants
# ============================================================================


@settings(max_examples=50, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_duration_positivity(wake_duration, sleep_duration):
    """
    INV-WS-S1: Duration Positivity
    Wake and sleep durations MUST be positive.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    assert rhythm.wake_duration > 0, f"Wake duration not positive: {rhythm.wake_duration}"
    assert rhythm.sleep_duration > 0, f"Sleep duration not positive: {rhythm.sleep_duration}"
    assert rhythm.wake_duration == wake_duration, "Wake duration not stored correctly"
    assert rhythm.sleep_duration == sleep_duration, "Sleep duration not stored correctly"


def test_rhythm_invalid_durations_rejected():
    """
    INV-WS-S1: Invalid durations (zero or negative) MUST be rejected.
    """
    with pytest.raises(ValueError, match="positive"):
        CognitiveRhythm(wake_duration=0, sleep_duration=3)

    with pytest.raises(ValueError, match="positive"):
        CognitiveRhythm(wake_duration=8, sleep_duration=0)

    with pytest.raises(ValueError, match="positive"):
        CognitiveRhythm(wake_duration=-1, sleep_duration=3)

    with pytest.raises(ValueError, match="positive"):
        CognitiveRhythm(wake_duration=8, sleep_duration=-1)


@settings(max_examples=50, deadline=None)
@given(
    wake_duration=duration_strategy(),
    sleep_duration=duration_strategy(),
    num_steps=step_count_strategy(),
)
def test_rhythm_phase_validity(wake_duration, sleep_duration, num_steps):
    """
    INV-WS-S2: Phase Validity
    Phase MUST be either "wake" or "sleep" at all times.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    valid_phases = {"wake", "sleep"}

    # Check initial phase
    assert rhythm.phase in valid_phases, f"Invalid initial phase: {rhythm.phase}"
    assert (
        rhythm.get_current_phase() in valid_phases
    ), f"Invalid get_current_phase: {rhythm.get_current_phase()}"

    # Check phase after each step
    for i in range(num_steps):
        rhythm.step()

        assert rhythm.phase in valid_phases, f"Invalid phase after step {i+1}: {rhythm.phase}"
        assert (
            rhythm.get_current_phase() in valid_phases
        ), f"get_current_phase invalid after step {i+1}: {rhythm.get_current_phase()}"


@settings(max_examples=50, deadline=None)
@given(
    wake_duration=duration_strategy(),
    sleep_duration=duration_strategy(),
    num_steps=step_count_strategy(),
)
def test_rhythm_counter_non_negativity(wake_duration, sleep_duration, num_steps):
    """
    INV-WS-S3: Counter Non-Negativity
    Counter MUST never go negative.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Check initial counter (should be wake_duration)
    assert rhythm.counter >= 0, f"Initial counter negative: {rhythm.counter}"

    # Check counter after each step
    for i in range(num_steps):
        rhythm.step()

        # Counter should reset when phase changes, never go negative
        assert rhythm.counter >= 0, f"Counter negative after step {i+1}: {rhythm.counter}"


# ============================================================================
# Liveness Invariants
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_eventual_phase_transition(wake_duration, sleep_duration):
    """
    INV-WS-L1: Eventual Phase Transition
    System MUST eventually transition between phases.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    initial_phase = rhythm.phase
    max_steps = wake_duration + sleep_duration + 1

    # Step until phase changes
    phase_changed = False
    for _ in range(max_steps):
        rhythm.step()
        if rhythm.phase != initial_phase:
            phase_changed = True
            break

    assert phase_changed, f"Phase never changed from {initial_phase} after {max_steps} steps"


@settings(max_examples=50, deadline=None)
@given(
    wake_duration=duration_strategy(),
    sleep_duration=duration_strategy(),
    num_steps=step_count_strategy(),
)
def test_rhythm_step_progress(wake_duration, sleep_duration, num_steps):
    """
    INV-WS-L2: Step Progress
    Each step() call decrements counter or transitions phase.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    for i in range(num_steps):
        counter_before = rhythm.counter
        phase_before = rhythm.phase

        rhythm.step()

        counter_after = rhythm.counter
        phase_after = rhythm.phase

        # Either counter decreased OR phase changed
        counter_decreased = counter_after == counter_before - 1
        phase_changed = phase_after != phase_before

        # When counter reaches 0, phase changes and counter resets
        if counter_before == 1:
            assert phase_changed, f"Phase should change when counter was 1 (step {i+1})"
        else:
            assert (
                counter_decreased or phase_changed
            ), f"Step {i+1} made no progress: counter {counter_before}->{counter_after}, phase {phase_before}->{phase_after}"


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_is_wake_is_sleep_consistency(wake_duration, sleep_duration):
    """
    INV-WS-S2 consistency: is_wake() and is_sleep() must be mutually exclusive.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    cycle_length = wake_duration + sleep_duration

    for _ in range(cycle_length * 3):  # Test through 3 full cycles
        # Exactly one must be true
        assert (
            rhythm.is_wake() != rhythm.is_sleep()
        ), f"is_wake={rhythm.is_wake()}, is_sleep={rhythm.is_sleep()} - not mutually exclusive"

        # Must match phase attribute
        if rhythm.is_wake():
            assert rhythm.phase == "wake"
        else:
            assert rhythm.phase == "sleep"

        rhythm.step()


# ============================================================================
# Metamorphic Invariants
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_cycle_periodicity(wake_duration, sleep_duration):
    """
    INV-WS-M1: Cycle Periodicity
    Complete cycle duration equals wake_duration + sleep_duration.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    expected_cycle = wake_duration + sleep_duration

    # Count steps to complete one full cycle (wake -> sleep -> wake)
    steps = 0
    initial_phase = rhythm.phase
    phase_changes = 0

    # We need to see: initial phase -> other phase -> initial phase again
    while phase_changes < 2:
        rhythm.step()
        steps += 1

        if rhythm.phase != initial_phase and phase_changes == 0:
            phase_changes = 1
        elif rhythm.phase == initial_phase and phase_changes == 1:
            phase_changes = 2

        # Safety: prevent infinite loop
        if steps > expected_cycle * 2:
            break

    assert (
        steps == expected_cycle
    ), f"Cycle duration {steps} != expected {expected_cycle} (wake={wake_duration}, sleep={sleep_duration})"


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_phase_alternation(wake_duration, sleep_duration):
    """
    INV-WS-M2: Phase Alternation
    Phases strictly alternate (wake -> sleep -> wake -> ...).
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    cycle_length = wake_duration + sleep_duration
    num_steps = cycle_length * 5  # Test through 5 cycles

    phase_history = [rhythm.phase]

    for _ in range(num_steps):
        rhythm.step()

        current_phase = rhythm.phase
        last_recorded = phase_history[-1]

        # Only record when phase changes
        if current_phase != last_recorded:
            phase_history.append(current_phase)

    # Verify alternation: no two consecutive identical phases in history
    for i in range(len(phase_history) - 1):
        assert (
            phase_history[i] != phase_history[i + 1]
        ), f"Phase repetition at index {i}: {phase_history}"


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_wake_duration_exact(wake_duration, sleep_duration):
    """
    Verify that wake phase lasts exactly wake_duration steps.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Start in wake phase
    assert rhythm.phase == "wake", "Initial phase should be wake"

    wake_steps = 0
    while rhythm.phase == "wake":
        wake_steps += 1
        rhythm.step()

        # Safety: prevent infinite loop
        if wake_steps > wake_duration + 1:
            break

    assert (
        wake_steps == wake_duration
    ), f"Wake phase lasted {wake_steps} steps, expected {wake_duration}"


@settings(max_examples=30, deadline=None)
@given(wake_duration=duration_strategy(), sleep_duration=duration_strategy())
def test_rhythm_sleep_duration_exact(wake_duration, sleep_duration):
    """
    Verify that sleep phase lasts exactly sleep_duration steps.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Step through wake phase
    while rhythm.phase == "wake":
        rhythm.step()

    # Now in sleep phase
    assert rhythm.phase == "sleep", "Should be in sleep phase after wake"

    sleep_steps = 0
    while rhythm.phase == "sleep":
        sleep_steps += 1
        rhythm.step()

        # Safety: prevent infinite loop
        if sleep_steps > sleep_duration + 1:
            break

    assert (
        sleep_steps == sleep_duration
    ), f"Sleep phase lasted {sleep_steps} steps, expected {sleep_duration}"


# ============================================================================
# Serialization Tests
# ============================================================================


@settings(max_examples=30, deadline=None)
@given(
    wake_duration=duration_strategy(),
    sleep_duration=duration_strategy(),
    num_steps=st.integers(min_value=0, max_value=50),
)
def test_rhythm_to_dict_complete(wake_duration, sleep_duration, num_steps):
    """
    Test that to_dict returns complete and accurate state.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Take some steps
    for _ in range(num_steps):
        rhythm.step()

    state_dict = rhythm.to_dict()

    # Check required keys
    assert "wake_duration" in state_dict, "Missing wake_duration"
    assert "sleep_duration" in state_dict, "Missing sleep_duration"
    assert "phase" in state_dict, "Missing phase"
    assert "counter" in state_dict, "Missing counter"

    # Check values match instance attributes
    assert state_dict["wake_duration"] == rhythm.wake_duration
    assert state_dict["sleep_duration"] == rhythm.sleep_duration
    assert state_dict["phase"] == rhythm.phase
    assert state_dict["counter"] == rhythm.counter


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.parametrize(
    "wake,sleep",
    [
        (1, 1),  # Minimum valid durations
        (1, 10),  # Asymmetric (short wake)
        (10, 1),  # Asymmetric (short sleep)
        (100, 100),  # Large equal durations
    ],
)
def test_rhythm_edge_case_durations(wake, sleep):
    """Test rhythm with various edge case durations."""
    rhythm = CognitiveRhythm(wake_duration=wake, sleep_duration=sleep)

    # Should complete at least one full cycle without error
    total_steps = (wake + sleep) * 2
    for _ in range(total_steps):
        rhythm.step()

    # Verify state is valid after many steps
    assert rhythm.phase in {"wake", "sleep"}
    assert rhythm.counter >= 0


def test_rhythm_rapid_cycling():
    """Test behavior with minimum durations (1,1) for rapid cycling."""
    rhythm = CognitiveRhythm(wake_duration=1, sleep_duration=1)

    # Each step should cause phase transition
    phases = []
    for _ in range(10):
        phases.append(rhythm.phase)
        rhythm.step()

    # Should see alternating pattern
    expected = ["wake", "sleep", "wake", "sleep", "wake", "sleep", "wake", "sleep", "wake", "sleep"]
    assert phases == expected, f"Rapid cycling failed: {phases}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
