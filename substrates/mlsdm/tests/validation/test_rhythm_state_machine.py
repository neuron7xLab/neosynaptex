"""
State machine tests for CognitiveRhythm lifecycle.

Verifies that wake/sleep phase transitions follow expected state machine
and that the rhythm cannot be bypassed or corrupted.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.rhythm.cognitive_rhythm import CognitiveRhythm


def test_rhythm_initial_state() -> None:
    """Test that rhythm starts in wake phase with correct counter.

    Verifies initial state is wake with counter equal to wake_duration.
    """
    rhythm = CognitiveRhythm(wake_duration=8, sleep_duration=3)

    assert rhythm.phase == "wake"
    assert rhythm.counter == 8
    assert rhythm.is_wake()
    assert not rhythm.is_sleep()


def test_rhythm_wake_to_sleep_transition() -> None:
    """Test transition from wake to sleep after wake_duration steps.

    Verifies phase transitions to sleep after wake_duration steps.
    """
    wake_duration = 5
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=3)

    # Step through wake phase
    for i in range(wake_duration):
        assert rhythm.is_wake(), f"Should be wake at step {i}"
        rhythm.step()

    # After wake_duration steps, should transition to sleep
    assert rhythm.is_sleep(), "Should transition to sleep after wake_duration"
    assert rhythm.phase == "sleep"
    assert rhythm.counter == 3


def test_rhythm_sleep_to_wake_transition() -> None:
    """Test transition from sleep back to wake after sleep_duration steps.

    Verifies phase transitions back to wake after sleep_duration steps.
    """
    wake_duration = 8
    sleep_duration = 3
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Step through wake phase
    for _ in range(wake_duration):
        rhythm.step()

    # Now in sleep phase
    assert rhythm.is_sleep()

    # Step through sleep phase
    for i in range(sleep_duration):
        assert rhythm.is_sleep(), f"Should be sleep at step {i}"
        rhythm.step()

    # After sleep_duration steps, should transition back to wake
    assert rhythm.is_wake(), "Should transition back to wake after sleep_duration"
    assert rhythm.phase == "wake"
    assert rhythm.counter == wake_duration


def test_rhythm_full_cycle() -> None:
    """Test complete wake→sleep→wake cycle maintains invariants.

    Verifies phase pattern matches expected wake/sleep sequence.
    """
    wake_duration = 4
    sleep_duration = 2
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    total_steps = (wake_duration + sleep_duration) * 3  # 3 full cycles
    phase_log: list[str] = []

    for step in range(total_steps):
        phase_log.append(rhythm.phase)
        rhythm.step()

    # Verify pattern: wake (4x) then sleep (2x), repeated
    expected_pattern = ["wake"] * wake_duration + ["sleep"] * sleep_duration
    expected_full = expected_pattern * 3

    assert phase_log == expected_full, f"Phase pattern mismatch: {phase_log}"


def test_rhythm_counter_decrements_correctly() -> None:
    """Test that counter decrements properly in each phase.

    Verifies counter values decrease correctly during wake and sleep phases.
    """
    rhythm = CognitiveRhythm(wake_duration=5, sleep_duration=3)

    # Track counter values during wake phase
    wake_counters: list[int] = []
    for _ in range(5):
        wake_counters.append(rhythm.counter)
        rhythm.step()

    # Should decrement from 5 to 1
    assert wake_counters == [5, 4, 3, 2, 1], f"Wake counters wrong: {wake_counters}"

    # Track counter values during sleep phase
    sleep_counters: list[int] = []
    for _ in range(3):
        sleep_counters.append(rhythm.counter)
        rhythm.step()

    # Should decrement from 3 to 1
    assert sleep_counters == [3, 2, 1], f"Sleep counters wrong: {sleep_counters}"


def test_rhythm_phase_boundaries() -> None:
    """Test that phase transitions happen exactly at counter=0.

    Verifies transitions occur at correct boundary points.
    """
    rhythm = CognitiveRhythm(wake_duration=3, sleep_duration=2)

    # Step to counter=1 in wake
    rhythm.step()
    rhythm.step()
    assert rhythm.counter == 1
    assert rhythm.is_wake()

    # One more step should transition to sleep
    rhythm.step()
    assert rhythm.counter == 2  # Reset to sleep_duration
    assert rhythm.is_sleep()


def test_rhythm_to_dict_serialization() -> None:
    """Test that rhythm state can be serialized correctly.

    Verifies to_dict returns expected state values.
    """
    rhythm = CognitiveRhythm(wake_duration=8, sleep_duration=3)

    state = rhythm.to_dict()

    assert state["wake_duration"] == 8
    assert state["sleep_duration"] == 3
    assert state["phase"] == "wake"
    assert state["counter"] == 8


def test_rhythm_invalid_durations() -> None:
    """Test that invalid durations raise appropriate errors.

    Verifies ValueError is raised for invalid duration values.
    """
    with pytest.raises(ValueError, match="Durations must be positive"):
        CognitiveRhythm(wake_duration=0, sleep_duration=3)

    with pytest.raises(ValueError, match="Durations must be positive"):
        CognitiveRhythm(wake_duration=8, sleep_duration=0)

    with pytest.raises(ValueError, match="Durations must be positive"):
        CognitiveRhythm(wake_duration=-1, sleep_duration=3)


@settings(max_examples=50, deadline=None)
@given(
    wake_duration=st.integers(min_value=1, max_value=20),
    sleep_duration=st.integers(min_value=1, max_value=20),
    num_cycles=st.integers(min_value=1, max_value=10),
)
def test_rhythm_property_cycle_consistency(
    wake_duration: int, sleep_duration: int, num_cycles: int
) -> None:
    """Property test: After N complete cycles, rhythm returns to initial state.

    Verifies rhythm is cyclic and returns to initial state after complete cycles.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    # Record initial state
    initial_phase = rhythm.phase
    initial_counter = rhythm.counter

    # Execute N complete cycles
    steps_per_cycle = wake_duration + sleep_duration
    total_steps = steps_per_cycle * num_cycles

    for _ in range(total_steps):
        rhythm.step()

    # Should return to initial state
    assert (
        rhythm.phase == initial_phase
    ), f"Phase mismatch after {num_cycles} cycles: {rhythm.phase} != {initial_phase}"
    assert (
        rhythm.counter == initial_counter
    ), f"Counter mismatch after {num_cycles} cycles: {rhythm.counter} != {initial_counter}"


@settings(max_examples=50, deadline=None)
@given(
    wake_duration=st.integers(min_value=1, max_value=20),
    sleep_duration=st.integers(min_value=1, max_value=20),
    steps=st.integers(min_value=0, max_value=100),
)
def test_rhythm_property_counter_bounds(
    wake_duration: int, sleep_duration: int, steps: int
) -> None:
    """Property test: Counter always stays within valid bounds.

    Verifies counter is always positive and within duration limits.
    """
    rhythm = CognitiveRhythm(wake_duration=wake_duration, sleep_duration=sleep_duration)

    for _ in range(steps):
        # Counter should always be positive and within duration bounds
        assert rhythm.counter > 0, f"Counter should be positive, got {rhythm.counter}"

        if rhythm.phase == "wake":
            assert (
                rhythm.counter <= wake_duration
            ), f"Wake counter {rhythm.counter} exceeds duration {wake_duration}"
        else:
            assert (
                rhythm.counter <= sleep_duration
            ), f"Sleep counter {rhythm.counter} exceeds duration {sleep_duration}"

        rhythm.step()


def test_rhythm_deterministic_behavior() -> None:
    """Test that rhythm behavior is deterministic given same inputs.

    Verifies two rhythms with same parameters produce same state sequence.
    """
    rhythm1 = CognitiveRhythm(wake_duration=5, sleep_duration=3)
    rhythm2 = CognitiveRhythm(wake_duration=5, sleep_duration=3)

    for _ in range(20):
        assert rhythm1.phase == rhythm2.phase
        assert rhythm1.counter == rhythm2.counter
        rhythm1.step()
        rhythm2.step()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
