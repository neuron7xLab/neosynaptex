"""
E2E Core Happy Path Tests for MLSDM.

This module contains the core happy path E2E test, refactored from
tests/integration/test_end_to_end.py with minimal changes.
It validates the basic flow through the CognitiveController.
"""

import numpy as np
import pytest

# Fixed seed for reproducible tests
_SEED = 42


def _make_vector(dim: int = 384) -> np.ndarray:
    """Create a normalized vector with fixed seed for reproducibility."""
    np.random.seed(_SEED)
    vec = np.random.randn(dim).astype(np.float32)
    return vec / np.linalg.norm(vec)


class TestE2ECoreHappyPath:
    """Core E2E happy path tests - basic cognitive controller flow."""

    def test_basic_flow_normal_acceptance(self) -> None:
        """
        Test that normal events are accepted through the cognitive controller.

        Validates:
        - CognitiveController initializes correctly
        - Normal events with high moral value are accepted
        - State contains expected fields
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=384)
        vec = _make_vector(384)

        state = controller.process_event(vec, moral_value=0.9)

        assert state["rejected"] is False
        assert "step" in state
        assert "phase" in state

    def test_basic_flow_moral_rejection(self) -> None:
        """
        Test that events with low moral value are rejected.

        Validates:
        - Low moral value triggers rejection
        - Rejection state is properly recorded
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=384)
        vec = _make_vector(384)

        state = controller.process_event(vec, moral_value=0.1)

        assert state["rejected"] is True

    def test_basic_flow_sleep_phase(self) -> None:
        """
        Test that system enters sleep phase after wake duration.

        Validates:
        - System transitions from wake to sleep phase
        - Sleep phase events are handled appropriately
        - Note contains sleep phase indication
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=384)
        vec = _make_vector(384)

        # Step enough times to enter sleep phase (default wake_duration=8)
        for _ in range(8):
            controller.rhythm_step()

        assert controller.rhythm.is_wake() is False, "Should be in sleep phase"

        state = controller.process_event(vec, moral_value=0.9)
        assert "sleep" in state["note"]

    def test_wake_sleep_cycle_alternation(self) -> None:
        """
        Test complete wake/sleep cycle alternation.

        Validates:
        - Wake phase transitions to sleep phase
        - Sleep phase transitions back to wake phase
        - Cycle continues correctly
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=384)

        # Verify initial wake state
        assert controller.rhythm.is_wake() is True

        # Transition to sleep (step wake_duration times)
        for _ in range(8):
            controller.rhythm_step()
        assert controller.rhythm.is_wake() is False
        assert controller.rhythm.is_sleep() is True

        # Transition back to wake (step sleep_duration times)
        for _ in range(3):
            controller.rhythm_step()
        assert controller.rhythm.is_wake() is True
        assert controller.rhythm.is_sleep() is False

    def test_multiple_events_processed(self) -> None:
        """
        Test that multiple events can be processed in sequence.

        Validates:
        - Controller handles multiple events
        - Each event produces valid state
        - Step counter increments
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=384)
        vec = _make_vector(384)

        states = []
        for _ in range(5):
            state = controller.process_event(vec, moral_value=0.8)
            states.append(state)

        # Verify we got states for all events
        assert len(states) == 5

        # Verify step increments
        steps = [s["step"] for s in states]
        assert steps == [1, 2, 3, 4, 5]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
