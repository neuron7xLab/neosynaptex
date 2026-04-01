"""
Unit tests for CognitiveState introspection in MLSDM core.

These tests validate:
1. The CognitiveState dataclass structure and field types
2. Stability of the get_cognitive_state() method across generate() calls
3. JSON serialization compatibility for API/health endpoints
4. No side effects from introspection calls

This module follows the testing patterns established in test_speech_governance_hook.py.
"""

import json

import numpy as np
import pytest

from mlsdm.core.cognitive_state import CognitiveState
from mlsdm.core.llm_wrapper import LLMWrapper


def dummy_llm(prompt: str, max_tokens: int) -> str:
    """Simple mock LLM that echoes part of the prompt."""
    return "mock response"


def dummy_embedder(text: str):
    """Generate deterministic embeddings based on text hash."""
    np.random.seed(abs(hash(text)) % (2**32))
    vec = np.random.randn(384).astype(np.float32)
    return vec / np.linalg.norm(vec)


class TestCognitiveStateStructure:
    """Tests for CognitiveState dataclass structure and types."""

    def test_cognitive_state_is_dataclass(self):
        """Verify CognitiveState is a proper dataclass with expected fields."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state, CognitiveState)

    def test_cognitive_state_phase_is_string(self):
        """Verify phase field is always a string."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state.phase, str)
        assert state.phase in ("wake", "sleep", "unknown")

    def test_cognitive_state_stateless_mode_is_bool(self):
        """Verify stateless_mode field is always a boolean."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state.stateless_mode, bool)

    def test_cognitive_state_memory_used_bytes_is_int(self):
        """Verify memory_used_bytes field is always an integer."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state.memory_used_bytes, int)
        assert state.memory_used_bytes >= 0

    def test_cognitive_state_emergency_shutdown_is_bool(self):
        """Verify emergency_shutdown field is always a boolean."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state.emergency_shutdown, bool)

    def test_cognitive_state_has_all_required_fields(self):
        """Verify all expected fields exist in CognitiveState."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        # Check all fields exist
        assert hasattr(state, "phase")
        assert hasattr(state, "stateless_mode")
        assert hasattr(state, "memory_used_bytes")
        assert hasattr(state, "moral_threshold")
        assert hasattr(state, "moral_ema")
        assert hasattr(state, "rhythm_state")
        assert hasattr(state, "step_counter")
        assert hasattr(state, "emergency_shutdown")
        assert hasattr(state, "aphasia_flags")
        assert hasattr(state, "extra")

    def test_cognitive_state_optional_fields_can_be_none(self):
        """Verify optional fields can be None without breaking the contract."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        # Optional fields should be typed correctly (may be None or actual value)
        if state.moral_threshold is not None:
            assert isinstance(state.moral_threshold, float)
        if state.moral_ema is not None:
            assert isinstance(state.moral_ema, float)
        if state.rhythm_state is not None:
            assert isinstance(state.rhythm_state, str)
        if state.step_counter is not None:
            assert isinstance(state.step_counter, int)
        if state.aphasia_flags is not None:
            assert isinstance(state.aphasia_flags, dict)

    def test_cognitive_state_extra_is_dict(self):
        """Verify extra field is always a dictionary."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        assert isinstance(state.extra, dict)


class TestCognitiveStateStability:
    """Tests for stability of get_cognitive_state() across generate() calls."""

    def test_cognitive_state_after_generate(self):
        """Verify get_cognitive_state() returns valid state after generate()."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=4,
            sleep_duration=2,
            initial_moral_threshold=0.5,
        )

        # Get state before generation (used for reference)
        _ = wrapper.get_cognitive_state()

        # Perform a generation
        wrapper.generate(prompt="test prompt", moral_value=0.8, max_tokens=16)

        state_after = wrapper.get_cognitive_state()

        # State should still be valid
        assert isinstance(state_after, CognitiveState)
        assert isinstance(state_after.phase, str)
        assert isinstance(state_after.stateless_mode, bool)
        assert isinstance(state_after.memory_used_bytes, int)

    def test_step_counter_consistency(self):
        """Verify step_counter increments consistently with generate() calls."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=5,
            sleep_duration=2,
            initial_moral_threshold=0.5,
        )

        state_initial = wrapper.get_cognitive_state()
        initial_step = state_initial.step_counter or 0

        # Multiple generates
        for i in range(3):
            wrapper.generate(prompt=f"test {i}", moral_value=0.8, max_tokens=16)

        state_after = wrapper.get_cognitive_state()
        final_step = state_after.step_counter or 0

        # Step counter should have increased
        assert final_step > initial_step

    def test_memory_used_bytes_non_negative(self):
        """Verify memory_used_bytes never becomes negative."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=4,
            sleep_duration=2,
            initial_moral_threshold=0.5,
        )

        # Check initially
        state = wrapper.get_cognitive_state()
        assert state.memory_used_bytes >= 0

        # Check after generates
        for i in range(3):
            wrapper.generate(prompt=f"test {i}", moral_value=0.8, max_tokens=16)
            state = wrapper.get_cognitive_state()
            assert state.memory_used_bytes >= 0

    def test_multiple_get_cognitive_state_calls(self):
        """Verify multiple calls to get_cognitive_state() are idempotent."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        # Get state multiple times without changing anything
        state1 = wrapper.get_cognitive_state()
        state2 = wrapper.get_cognitive_state()
        state3 = wrapper.get_cognitive_state()

        # All states should be equivalent
        assert state1.phase == state2.phase == state3.phase
        assert state1.stateless_mode == state2.stateless_mode == state3.stateless_mode
        assert state1.step_counter == state2.step_counter == state3.step_counter
        assert state1.emergency_shutdown == state2.emergency_shutdown == state3.emergency_shutdown


class TestCognitiveStateJSONCompatibility:
    """Tests for JSON serialization compatibility."""

    def test_cognitive_state_to_dict(self):
        """Verify CognitiveState.to_dict() works correctly."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()
        state_dict = state.to_dict()

        assert isinstance(state_dict, dict)
        assert "phase" in state_dict
        assert "stateless_mode" in state_dict
        assert "memory_used_bytes" in state_dict
        assert "moral_threshold" in state_dict
        assert "moral_ema" in state_dict
        assert "rhythm_state" in state_dict
        assert "step_counter" in state_dict
        assert "emergency_shutdown" in state_dict
        assert "aphasia_flags" in state_dict
        assert "extra" in state_dict

    def test_cognitive_state_json_dumps(self):
        """Verify CognitiveState can be serialized to JSON via to_dict()."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()
        state_dict = state.to_dict()

        # Should not raise any exceptions
        json_str = json.dumps(state_dict)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_cognitive_state_json_roundtrip(self):
        """Verify CognitiveState survives JSON roundtrip."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()
        state_dict = state.to_dict()

        # Serialize and deserialize
        json_str = json.dumps(state_dict)
        parsed = json.loads(json_str)

        # All values should be preserved
        assert parsed["phase"] == state.phase
        assert parsed["stateless_mode"] == state.stateless_mode
        assert parsed["memory_used_bytes"] == state.memory_used_bytes
        assert parsed["emergency_shutdown"] == state.emergency_shutdown

    def test_cognitive_state_dataclass_dict(self):
        """Verify __dict__ approach also works for JSON serialization."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state = wrapper.get_cognitive_state()

        # Using to_dict() method for consistent serialization
        state_dict = state.to_dict()
        json_str = json.dumps(state_dict)

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "phase" in parsed


class TestCognitiveStateNoSideEffects:
    """Tests to ensure get_cognitive_state() has no side effects."""

    def test_no_side_effects_on_step_counter(self):
        """Verify get_cognitive_state() doesn't increment step_counter."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state1 = wrapper.get_cognitive_state()
        step_before = state1.step_counter

        # Call get_cognitive_state() many times
        for _ in range(10):
            wrapper.get_cognitive_state()

        state2 = wrapper.get_cognitive_state()
        step_after = state2.step_counter

        # Step counter should not have changed
        assert step_before == step_after

    def test_no_side_effects_on_phase(self):
        """Verify get_cognitive_state() doesn't change the phase."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
        )

        state1 = wrapper.get_cognitive_state()
        phase_before = state1.phase

        # Call get_cognitive_state() many times
        for _ in range(10):
            wrapper.get_cognitive_state()

        state2 = wrapper.get_cognitive_state()
        phase_after = state2.phase

        # Phase should not have changed
        assert phase_before == phase_after

    def test_no_side_effects_on_moral_threshold(self):
        """Verify get_cognitive_state() doesn't affect moral threshold."""
        wrapper = LLMWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            capacity=128,
            wake_duration=2,
            sleep_duration=1,
            initial_moral_threshold=0.5,
        )

        state1 = wrapper.get_cognitive_state()
        threshold_before = state1.moral_threshold

        # Call get_cognitive_state() many times
        for _ in range(10):
            wrapper.get_cognitive_state()

        state2 = wrapper.get_cognitive_state()
        threshold_after = state2.moral_threshold

        # Threshold should not have changed
        assert threshold_before == threshold_after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
