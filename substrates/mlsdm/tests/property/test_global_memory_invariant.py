"""
Property-based tests for Global Memory Invariant (CORE-04).

Tests the formal invariant:
    INV_GLOBAL_MEM: ∀t, memory_usage_bytes(t) ≤ MAX_MEMORY_BYTES (default 1.4 GB)

This module tests:
- Scenario A: Normal operation keeps memory within bounds
- Scenario B: Forced emergency shutdown when limit exceeded
"""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

# ============================================================================
# Test Constants - Using small values for CI-friendly tests
# ============================================================================

# Small dimensions to keep tests fast and memory-light
TEST_DIM_MIN = 8
TEST_DIM_MAX = 32
TEST_CAPACITY_MIN = 10
TEST_CAPACITY_MAX = 50

# Default 1.4 GB limit
DEFAULT_MAX_MEMORY_BYTES = int(1.4 * 1024**3)


# ============================================================================
# Strategies for Property-Based Tests
# ============================================================================


@st.composite
def vector_strategy(draw: st.DrawFn, dim: int = 16) -> np.ndarray:
    """Generate a random vector of specified dimension."""
    values = draw(
        st.lists(
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            min_size=dim,
            max_size=dim,
        )
    )
    return np.array(values, dtype=np.float32)


@st.composite
def moral_value_strategy(draw: st.DrawFn) -> float:
    """Generate a valid moral value in [0, 1]."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@st.composite
def event_sequence_strategy(
    draw: st.DrawFn, dim: int = 16, min_events: int = 5, max_events: int = 20
) -> list[tuple[np.ndarray, float]]:
    """Generate a sequence of (vector, moral_value) events."""
    num_events = draw(st.integers(min_value=min_events, max_value=max_events))
    events = []
    for _ in range(num_events):
        vec = draw(vector_strategy(dim=dim))
        moral = draw(moral_value_strategy())
        events.append((vec, moral))
    return events


# ============================================================================
# Unit Tests: Individual Components memory_usage_bytes()
# ============================================================================


class TestPELMMemoryUsage:
    """Tests for PELM.memory_usage_bytes() method."""

    def test_memory_usage_bytes_returns_int(self) -> None:
        """memory_usage_bytes() should return an integer."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        usage = pelm.memory_usage_bytes()
        assert isinstance(usage, int)

    def test_memory_usage_bytes_positive(self) -> None:
        """memory_usage_bytes() should return a positive value."""
        pelm = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        usage = pelm.memory_usage_bytes()
        assert usage > 0

    def test_memory_usage_scales_with_capacity(self) -> None:
        """Larger capacity should use more memory."""
        pelm_small = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        pelm_large = PhaseEntangledLatticeMemory(dimension=16, capacity=1000)
        assert pelm_large.memory_usage_bytes() > pelm_small.memory_usage_bytes()

    def test_memory_usage_scales_with_dimension(self) -> None:
        """Larger dimension should use more memory."""
        pelm_small = PhaseEntangledLatticeMemory(dimension=16, capacity=100)
        pelm_large = PhaseEntangledLatticeMemory(dimension=128, capacity=100)
        assert pelm_large.memory_usage_bytes() > pelm_small.memory_usage_bytes()

    @settings(max_examples=20, deadline=None)
    @given(
        dim=st.integers(min_value=TEST_DIM_MIN, max_value=TEST_DIM_MAX),
        capacity=st.integers(min_value=TEST_CAPACITY_MIN, max_value=TEST_CAPACITY_MAX),
    )
    def test_memory_usage_conservative_estimate(self, dim: int, capacity: int) -> None:
        """memory_usage_bytes() should be at least as large as raw array bytes."""
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        # Minimum memory: just the arrays
        raw_arrays = pelm.memory_bank.nbytes + pelm.phase_bank.nbytes + pelm.norms.nbytes

        usage = pelm.memory_usage_bytes()
        assert usage >= raw_arrays, f"memory_usage_bytes ({usage}) < raw arrays ({raw_arrays})"


class TestMultiLevelSynapticMemoryUsage:
    """Tests for MultiLevelSynapticMemory.memory_usage_bytes() method."""

    def test_memory_usage_bytes_returns_int(self) -> None:
        """memory_usage_bytes() should return an integer."""
        synaptic = MultiLevelSynapticMemory(dimension=16)
        usage = synaptic.memory_usage_bytes()
        assert isinstance(usage, int)

    def test_memory_usage_bytes_positive(self) -> None:
        """memory_usage_bytes() should return a positive value."""
        synaptic = MultiLevelSynapticMemory(dimension=16)
        usage = synaptic.memory_usage_bytes()
        assert usage > 0

    def test_memory_usage_scales_with_dimension(self) -> None:
        """Larger dimension should use more memory."""
        synaptic_small = MultiLevelSynapticMemory(dimension=16)
        synaptic_large = MultiLevelSynapticMemory(dimension=128)
        assert synaptic_large.memory_usage_bytes() > synaptic_small.memory_usage_bytes()

    @settings(max_examples=20, deadline=None)
    @given(dim=st.integers(min_value=TEST_DIM_MIN, max_value=TEST_DIM_MAX))
    def test_memory_usage_conservative_estimate(self, dim: int) -> None:
        """memory_usage_bytes() should be at least as large as raw array bytes."""
        synaptic = MultiLevelSynapticMemory(dimension=dim)

        # Minimum memory: just the L1/L2/L3 arrays
        raw_arrays = synaptic.l1.nbytes + synaptic.l2.nbytes + synaptic.l3.nbytes

        usage = synaptic.memory_usage_bytes()
        assert usage >= raw_arrays, f"memory_usage_bytes ({usage}) < raw arrays ({raw_arrays})"


class TestCognitiveControllerMemoryUsage:
    """Tests for CognitiveController.memory_usage_bytes() method."""

    def test_memory_usage_bytes_returns_int(self) -> None:
        """memory_usage_bytes() should return an integer."""
        controller = CognitiveController(dim=16)
        usage = controller.memory_usage_bytes()
        assert isinstance(usage, int)

    def test_memory_usage_bytes_positive(self) -> None:
        """memory_usage_bytes() should return a positive value."""
        controller = CognitiveController(dim=16)
        usage = controller.memory_usage_bytes()
        assert usage > 0

    def test_memory_usage_aggregates_components(self) -> None:
        """memory_usage_bytes() should aggregate PELM + synaptic."""
        controller = CognitiveController(dim=16)

        pelm_usage = controller.pelm.memory_usage_bytes()
        synaptic_usage = controller.synaptic.memory_usage_bytes()

        total_usage = controller.memory_usage_bytes()

        # Total should be at least sum of components
        assert total_usage >= pelm_usage + synaptic_usage

    def test_max_memory_bytes_default(self) -> None:
        """max_memory_bytes should default to 1.4 GB."""
        controller = CognitiveController(dim=16)
        assert controller.max_memory_bytes == DEFAULT_MAX_MEMORY_BYTES

    def test_max_memory_bytes_override(self) -> None:
        """max_memory_bytes can be overridden."""
        custom_limit = 1024 * 1024  # 1 MB
        controller = CognitiveController(dim=16, max_memory_bytes=custom_limit)
        assert controller.max_memory_bytes == custom_limit


# ============================================================================
# Scenario A: Normal Operation Within Bounds
# ============================================================================


class TestScenarioA_NormalOperation:
    """
    Scenario A: Normal operation should keep memory within bounds.

    Under realistic configurations and normal load, the controller should:
    - Always have memory_usage_bytes() <= max_memory_bytes
    - Never trigger emergency_shutdown due to memory
    """

    @settings(max_examples=30, deadline=None)
    @given(
        dim=st.integers(min_value=TEST_DIM_MIN, max_value=TEST_DIM_MAX),
        num_events=st.integers(min_value=5, max_value=30),
    )
    def test_memory_within_bounds_normal_load(self, dim: int, num_events: int) -> None:
        """
        INV_GLOBAL_MEM: memory_usage_bytes() <= max_memory_bytes under normal load.
        """
        # Use default 1.4 GB limit (generous for small test data)
        controller = CognitiveController(dim=dim)

        for i in range(num_events):
            vec = np.random.randn(dim).astype(np.float32)
            moral_value = 0.7  # High enough to be accepted

            controller.process_event(vec, moral_value)

            # Check invariant after each event
            current_usage = controller.memory_usage_bytes()
            max_allowed = controller.max_memory_bytes

            assert (
                current_usage <= max_allowed
            ), f"Memory usage {current_usage} exceeds limit {max_allowed} at event {i+1}"

    @settings(max_examples=20, deadline=None)
    @given(events=event_sequence_strategy(dim=16, min_events=10, max_events=30))
    def test_no_emergency_shutdown_normal_operation(
        self, events: list[tuple[np.ndarray, float]]
    ) -> None:
        """
        Under normal operation, emergency_shutdown should not be triggered
        by memory limit (may still trigger for other reasons).
        """
        controller = CognitiveController(dim=16)

        for vec, moral_value in events:
            result = controller.process_event(vec, moral_value)

            # If emergency shutdown triggered, it should NOT be due to memory
            if result["rejected"] and "emergency shutdown" in result["note"]:
                # Should not be memory-related with default 1.4 GB limit
                assert (
                    "global memory limit" not in result["note"]
                ), "Memory limit triggered under normal operation"

    def test_memory_usage_stable_after_many_events(self) -> None:
        """
        Memory usage should stabilize (not grow unbounded) after many events.
        PELM has fixed capacity, so memory should plateau.
        """
        controller = CognitiveController(dim=16)

        # Process many events to fill PELM
        for i in range(100):
            vec = np.random.randn(16).astype(np.float32)
            controller.process_event(vec, moral_value=0.8)

        usage_at_100 = controller.memory_usage_bytes()

        # Process more events
        for i in range(100):
            vec = np.random.randn(16).astype(np.float32)
            controller.process_event(vec, moral_value=0.8)

        usage_at_200 = controller.memory_usage_bytes()

        # Memory should not have grown significantly (PELM wraps around)
        # Allow small tolerance for any dynamic structures
        growth_tolerance = 0.1  # 10%
        assert usage_at_200 <= usage_at_100 * (
            1 + growth_tolerance
        ), f"Memory grew unexpectedly: {usage_at_100} -> {usage_at_200}"


# ============================================================================
# Scenario B: Forced Emergency Shutdown
# ============================================================================


class TestScenarioB_ForcedEmergencyShutdown:
    """
    Scenario B: Emergency shutdown when memory limit is exceeded.

    With a very low max_memory_bytes, the controller should:
    - Trigger emergency_shutdown when limit is exceeded
    - Prevent further memory growth after shutdown
    - Record the reason correctly
    """

    def test_emergency_shutdown_on_memory_limit(self) -> None:
        """
        Controller should enter emergency_shutdown when memory limit exceeded.
        """
        # Use a tiny memory limit that will be exceeded immediately
        tiny_limit = 1024  # 1 KB - way below actual usage
        controller = CognitiveController(dim=16, max_memory_bytes=tiny_limit)

        # Initial usage exceeds limit (PELM alone is > 1KB)
        initial_usage = controller.memory_usage_bytes()
        assert (
            initial_usage > tiny_limit
        ), "Test setup requires initial memory usage to exceed tiny limit"

        # Process an event - should trigger shutdown
        vec = np.random.randn(16).astype(np.float32)
        controller.process_event(vec, moral_value=0.8)

        # Should be in emergency shutdown
        assert controller.emergency_shutdown, "Controller should be in emergency_shutdown"

    def test_memory_usage_no_growth_after_shutdown(self) -> None:
        """
        INV-GMEM-BLOCK: After emergency_shutdown, memory should not grow.
        """
        # Small limit to trigger shutdown after a few events
        small_limit = 50 * 1024  # 50 KB
        controller = CognitiveController(dim=16, max_memory_bytes=small_limit)

        # Process events until shutdown
        for i in range(100):
            vec = np.random.randn(16).astype(np.float32)
            controller.process_event(vec, moral_value=0.8)

            if controller.emergency_shutdown:
                break

        # Capture memory usage at shutdown
        usage_at_shutdown = controller.memory_usage_bytes()

        # Try to process more events
        for i in range(50):
            vec = np.random.randn(16).astype(np.float32)
            result = controller.process_event(vec, moral_value=0.8)

            # Should be rejected
            assert result["rejected"], "Events after shutdown should be rejected"

            # Memory should not grow
            current_usage = controller.memory_usage_bytes()
            assert (
                current_usage <= usage_at_shutdown
            ), f"Memory grew after shutdown: {usage_at_shutdown} -> {current_usage}"

    def test_shutdown_reason_is_recorded(self) -> None:
        """
        INV-GMEM-REASON: Emergency shutdown reason should be recorded.
        """
        tiny_limit = 1024  # 1 KB
        controller = CognitiveController(dim=16, max_memory_bytes=tiny_limit)

        # Process an event to trigger shutdown
        vec = np.random.randn(16).astype(np.float32)
        controller.process_event(vec, moral_value=0.8)

        # Reason should be recorded
        assert (
            controller._emergency_reason == "memory_limit_exceeded"
        ), f"Wrong shutdown reason: {controller._emergency_reason}"

    @settings(max_examples=20, deadline=None)
    @given(num_events=st.integers(min_value=10, max_value=50))
    def test_shutdown_is_persistent(self, num_events: int) -> None:
        """
        Once in emergency_shutdown, controller stays there until manual reset.
        """
        tiny_limit = 1024  # 1 KB
        controller = CognitiveController(dim=16, max_memory_bytes=tiny_limit)

        shutdowns_seen = 0

        for i in range(num_events):
            vec = np.random.randn(16).astype(np.float32)
            result = controller.process_event(vec, moral_value=0.8)

            if controller.emergency_shutdown:
                shutdowns_seen += 1
                # Should stay in shutdown
                assert result["rejected"], "Events should be rejected in emergency shutdown"

        # Should have been in shutdown for most events
        assert shutdowns_seen > 0, "Should have entered emergency_shutdown"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Edge case tests for memory invariant."""

    def test_zero_events_memory_positive(self) -> None:
        """Even with no events, memory usage should be positive (allocated arrays)."""
        controller = CognitiveController(dim=16)
        assert controller.memory_usage_bytes() > 0

    def test_large_dimension_within_bounds(self) -> None:
        """Large dimension should still be within 1.4 GB limit."""
        controller = CognitiveController(dim=384)  # Typical embedding dim

        usage = controller.memory_usage_bytes()
        limit = controller.max_memory_bytes

        assert usage < limit, f"Default config uses {usage} bytes, exceeds {limit} limit"

    def test_reset_clears_emergency_reason(self) -> None:
        """reset_emergency_shutdown() should clear the reason."""
        controller = CognitiveController(dim=16, max_memory_bytes=1024)

        # Trigger shutdown
        vec = np.random.randn(16).astype(np.float32)
        controller.process_event(vec, moral_value=0.8)

        assert controller.emergency_shutdown
        assert controller._emergency_reason is not None

        # Reset
        controller.reset_emergency_shutdown()

        assert not controller.emergency_shutdown
        assert controller._emergency_reason is None


# ============================================================================
# Integration Tests
# ============================================================================


class TestGlobalMemoryIntegration:
    """Integration tests for global memory invariant across components."""

    @settings(max_examples=10, deadline=None)
    @given(dim=st.integers(min_value=TEST_DIM_MIN, max_value=TEST_DIM_MAX))
    def test_component_sum_matches_total(self, dim: int) -> None:
        """
        Controller memory usage should be approximately sum of components.
        """
        controller = CognitiveController(dim=dim)

        pelm = controller.pelm.memory_usage_bytes()
        synaptic = controller.synaptic.memory_usage_bytes()
        total = controller.memory_usage_bytes()

        # Total should be sum of components plus controller overhead
        component_sum = pelm + synaptic
        controller_overhead = total - component_sum

        # Overhead should be small (a few KB at most)
        assert controller_overhead >= 0, "Overhead cannot be negative"
        assert (
            controller_overhead < 10 * 1024
        ), f"Unexpectedly high controller overhead: {controller_overhead} bytes"

    def test_memory_reporting_consistent(self) -> None:
        """
        Memory usage should be consistent across repeated calls.
        """
        controller = CognitiveController(dim=16)

        usage1 = controller.memory_usage_bytes()
        usage2 = controller.memory_usage_bytes()
        usage3 = controller.memory_usage_bytes()

        assert (
            usage1 == usage2 == usage3
        ), f"Inconsistent memory reports: {usage1}, {usage2}, {usage3}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
