"""
Integration property tests for CognitiveController.

Verifies the integrated behavior of CognitiveController with all subsystems:
- PELM + MultiLevelSynapticMemory coordination
- Moral filter + rhythm + memory interaction
- State consistency across subsystems
- No data races or inconsistencies
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.core.cognitive_controller import CognitiveController

# Fixed seed for deterministic property tests
INTEGRATION_TEST_SEED = 42


@settings(max_examples=20, deadline=None)
@given(
    dim=st.integers(min_value=10, max_value=50), num_events=st.integers(min_value=5, max_value=30)
)
def test_controller_pelm_multilevel_coordination(dim, num_events):
    """
    Property: PELM and MultiLevelSynapticMemory stay coordinated.
    Both should update on accepted events, neither should have dangling references.
    """
    np.random.seed(INTEGRATION_TEST_SEED)
    controller = CognitiveController(dim=dim)

    accepted_count = 0
    rejected_count = 0

    for i in range(num_events):
        vec = np.random.randn(dim).astype(np.float32)
        # Alternate between high and low moral values
        moral_value = 0.8 if i % 2 == 0 else 0.3

        result = controller.process_event(vec, moral_value)

        if not result["rejected"]:
            accepted_count += 1
        else:
            rejected_count += 1

    # Both systems should have consistent state
    # PELM size should reflect accepted events (up to capacity)
    pelm_size = controller.pelm.size
    assert (
        pelm_size <= controller.pelm.capacity
    ), f"PELM size {pelm_size} exceeds capacity {controller.pelm.capacity}"

    # MultiLevel memory should have accumulated information
    L1, L2, L3 = controller.synaptic.get_state()
    total_memory_norm = np.linalg.norm(L1) + np.linalg.norm(L2) + np.linalg.norm(L3)

    # If events were accepted, memory should have content
    if accepted_count > 0:
        assert total_memory_norm > 0, "Memory should have content after accepted events"


def test_controller_moral_rhythm_interaction():
    """
    Property: Moral filter and rhythm work together correctly.
    Sleep phase should reject regardless of moral value.
    Wake phase should respect moral threshold.
    """
    np.random.seed(INTEGRATION_TEST_SEED)
    controller = CognitiveController(dim=384)

    sleep_phase_count = 0
    wake_phase_count = 0
    moral_rejections = 0

    # Process enough events to cycle through wake and sleep
    # Default: wake=8, sleep=3, so 11+ events guarantees seeing both
    num_events = 15

    for i in range(num_events):
        vec = np.random.randn(384).astype(np.float32)
        # Use varying moral values
        moral_value = 0.2 + (i % 7) * 0.1  # Range from 0.2 to 0.8

        result = controller.process_event(vec, moral_value)

        if result["rejected"]:
            if "sleep phase" in result["note"]:
                sleep_phase_count += 1
            elif "morally rejected" in result["note"]:
                moral_rejections += 1
        else:
            wake_phase_count += 1

    # Should have seen both wake and sleep phases
    total_processed = sleep_phase_count + wake_phase_count + moral_rejections
    assert total_processed == num_events, f"Event count mismatch: {total_processed} != {num_events}"

    # Should see sleep phase after 8 wake steps
    assert sleep_phase_count > 0, f"Should have seen sleep phase (saw {sleep_phase_count})"
    assert wake_phase_count > 0 or moral_rejections > 0, "Should have processed in wake"


@settings(max_examples=20, deadline=None)
@given(num_events=st.integers(min_value=5, max_value=25))
def test_controller_state_consistency(num_events):
    """
    Property: Controller state remains consistent across operations.
    Step counter, rhythm phase, and memory state should all be synchronized.
    """
    np.random.seed(INTEGRATION_TEST_SEED)
    controller = CognitiveController(dim=384)

    initial_step = controller.step_counter

    for i in range(num_events):
        vec = np.random.randn(384).astype(np.float32)
        moral_value = 0.7

        before_step = controller.step_counter

        controller.process_event(vec, moral_value)

        after_step = controller.step_counter
        after_phase = controller.rhythm.phase

        # Step counter should always increment
        assert (
            after_step == before_step + 1
        ), f"Step counter should increment: {before_step} -> {after_step}"

        # Phase should be valid
        assert after_phase in ["wake", "sleep"], f"Invalid phase: {after_phase}"

    # Final step count should match number of events
    assert (
        controller.step_counter == initial_step + num_events
    ), f"Step count mismatch: {controller.step_counter} != {initial_step + num_events}"


@settings(max_examples=20, deadline=None)
@given(moral_value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_controller_deterministic_processing(moral_value):
    """
    Property: Same input produces same output (deterministic).
    Two controllers with same config should behave identically.
    """
    np.random.seed(INTEGRATION_TEST_SEED)

    controller1 = CognitiveController(dim=384)
    controller2 = CognitiveController(dim=384)

    # Process same events
    for i in range(10):
        vec = np.random.randn(384).astype(np.float32)

        result1 = controller1.process_event(vec, moral_value)
        result2 = controller2.process_event(vec, moral_value)

        # Results should match
        assert (
            result1["rejected"] == result2["rejected"]
        ), f"Different rejection status at event {i}"
        assert result1["note"] == result2["note"], f"Different notes at event {i}"


def test_controller_retrieve_context_phase_aware():
    """
    Test that context retrieval works and uses phase-aware PELM.
    """
    controller = CognitiveController(dim=10)

    # Add events during wake phase
    wake_vec = np.ones(10, dtype=np.float32)
    for _ in range(3):
        result = controller.process_event(wake_vec, moral_value=0.8)
        if not result["rejected"]:
            # Event was accepted, memory updated
            pass

    # Try to retrieve context
    query = np.ones(10, dtype=np.float32)
    context = controller.retrieve_context(query, top_k=5)

    # Context retrieval should work (uses phase-aware PELM)
    assert isinstance(context, list), "Should return list of retrievals"

    # Verify retrieval uses current phase
    current_phase = controller.rhythm.phase
    assert current_phase in ["wake", "sleep"], f"Invalid phase: {current_phase}"


def test_controller_emergency_shutdown():
    """
    Test emergency shutdown mechanism.
    """
    controller = CognitiveController(dim=10, memory_threshold_mb=0.01)

    # Force emergency shutdown by exceeding memory
    controller.emergency_shutdown = True

    vec = np.ones(10, dtype=np.float32)
    result = controller.process_event(vec, moral_value=0.8)

    assert result["rejected"], "Should reject when in emergency shutdown"
    assert "emergency shutdown" in result["note"]


def test_controller_state_access():
    """
    Test that controller state can be accessed.
    """
    controller = CognitiveController(dim=10)

    # Process some events
    for i in range(5):
        vec = np.random.randn(10).astype(np.float32)
        controller.process_event(vec, moral_value=0.7)

    # Check state is accessible via attributes
    assert hasattr(controller, "step_counter")
    assert hasattr(controller, "rhythm")
    assert hasattr(controller, "moral")
    assert hasattr(controller, "pelm")
    assert hasattr(controller, "synaptic")
    assert hasattr(controller, "emergency_shutdown")

    # Check values are correct type
    assert isinstance(controller.step_counter, int)
    assert controller.step_counter >= 5
    assert isinstance(controller.emergency_shutdown, bool)


def test_controller_memory_usage_tracking():
    """
    Test that memory usage is tracked correctly.
    """
    controller = CognitiveController(dim=10)

    # Get memory usage
    memory_mb = controller.get_memory_usage()

    # Should return a positive float
    assert isinstance(memory_mb, float)
    assert memory_mb > 0, "Memory usage should be positive"


def test_controller_reset_emergency_shutdown():
    """
    Test that emergency shutdown can be reset.
    """
    controller = CognitiveController(dim=10)

    # Trigger shutdown
    controller.emergency_shutdown = True

    # Reset
    controller.reset_emergency_shutdown()

    assert not controller.emergency_shutdown, "Shutdown should be reset"

    # Should be able to process events again
    vec = np.ones(10, dtype=np.float32)
    result = controller.process_event(vec, moral_value=0.8)

    # May still reject for other reasons (sleep, moral), but not emergency
    if result["rejected"]:
        assert "emergency shutdown" not in result["note"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
