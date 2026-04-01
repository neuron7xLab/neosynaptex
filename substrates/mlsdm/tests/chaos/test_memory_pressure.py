"""
Chaos Engineering Tests: Memory Pressure

Tests system behavior under memory pressure conditions.
Verifies graceful degradation and recovery per REL-003.

These tests are designed to run on a schedule (not on every PR)
as they may be resource-intensive.
"""

import gc
import time

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController


class TestMemoryPressureChaos:
    """Test system behavior under memory pressure."""

    @pytest.mark.chaos
    def test_emergency_shutdown_on_memory_pressure(self):
        """Test that system enters emergency shutdown under memory pressure.

        Scenario:
        1. Create controller with low memory threshold
        2. Simulate memory pressure by processing many events
        3. Verify controller enters emergency shutdown gracefully
        4. Verify subsequent requests are rejected with proper error
        """
        # Use very low threshold to trigger emergency quickly
        controller = CognitiveController(
            memory_threshold_mb=0.001,  # Very low threshold
        )
        vector = np.random.randn(384).astype(np.float32)

        # Process event to trigger emergency
        result = controller.process_event(vector, moral_value=0.8)

        # Verify emergency shutdown was triggered
        assert controller.emergency_shutdown is True
        assert result["rejected"] is True
        assert "emergency shutdown" in result["note"]

        # Verify subsequent requests are also rejected gracefully
        result2 = controller.process_event(vector, moral_value=0.8)
        assert result2["rejected"] is True
        assert result2["note"] == "emergency shutdown"

    @pytest.mark.chaos
    def test_recovery_after_memory_pressure_relief(self):
        """Test that system recovers after memory pressure is relieved.

        Scenario:
        1. Trigger emergency shutdown due to memory pressure
        2. Simulate pressure relief by increasing threshold
        3. Wait for cooldown period
        4. Verify system auto-recovers and resumes normal operation
        """
        controller = CognitiveController(
            memory_threshold_mb=0.001,
            auto_recovery_enabled=True,
            auto_recovery_cooldown_seconds=0.1,  # Short cooldown for testing
        )
        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True

        # Simulate pressure relief
        controller.memory_threshold_mb = 10000.0

        # Wait for time-based cooldown
        time.sleep(0.15)

        # Process event - should trigger recovery
        controller.process_event(vector, moral_value=0.8)

        # Verify recovery
        assert controller.emergency_shutdown is False

    @pytest.mark.chaos
    def test_graceful_degradation_under_sustained_pressure(self):
        """Test graceful degradation under sustained memory pressure.

        Scenario:
        1. Create controller and process many events
        2. Monitor system behavior as memory grows
        3. Verify system doesn't crash but enters controlled states
        """
        controller = CognitiveController(
            memory_threshold_mb=100.0,  # Reasonable threshold
        )

        events_processed = 0
        emergency_entered = False

        # Process many events, simulating sustained load
        for i in range(500):
            vector = np.random.randn(384).astype(np.float32)
            result = controller.process_event(vector, moral_value=0.7)

            if result["rejected"]:
                # Check if it's an emergency shutdown
                if "emergency shutdown" in result["note"]:
                    emergency_entered = True
                    break
            else:
                events_processed += 1

            # Periodic GC to prevent test memory issues
            if i % 100 == 0:
                gc.collect()

        # System should have processed events OR entered emergency gracefully
        assert events_processed > 0 or emergency_entered
        # No exceptions should have been raised (we would have failed already)

    @pytest.mark.chaos
    def test_large_vector_allocation_handling(self):
        """Test handling of large vector allocations.

        Scenario:
        1. Allocate large arrays to simulate memory pressure
        2. Process events during memory pressure
        3. Verify system handles pressure gracefully
        4. Clean up and verify recovery
        """
        controller = CognitiveController()
        vector = np.random.randn(384).astype(np.float32)

        # Process some events normally first
        for _ in range(10):
            result = controller.process_event(vector, moral_value=0.8)
            if not result["rejected"]:
                assert "note" in result

        # Allocate large arrays to create memory pressure
        large_arrays = []
        try:
            # Allocate ~100MB of data
            for _ in range(10):
                large_arrays.append(np.random.randn(1024, 1024).astype(np.float64))

            # Process more events during memory pressure
            for _ in range(5):
                result = controller.process_event(vector, moral_value=0.8)
                # Should either process or reject gracefully
                assert "rejected" in result
                assert "note" in result

        finally:
            # Clean up large arrays
            large_arrays.clear()
            gc.collect()

        # System should still be functional after cleanup
        result = controller.process_event(vector, moral_value=0.8)
        assert "rejected" in result

    @pytest.mark.chaos
    def test_memory_usage_tracking_accuracy(self):
        """Test that memory usage is tracked accurately under pressure.

        Scenario:
        1. Record initial memory usage
        2. Process many events
        3. Verify memory tracking stays reasonable
        """
        controller = CognitiveController()

        initial_memory = controller.get_memory_usage()
        assert initial_memory > 0

        # Process events
        for i in range(100):
            vector = np.random.randn(384).astype(np.float32)
            controller.process_event(vector, moral_value=0.7)

            if i % 25 == 0:
                gc.collect()

        final_memory = controller.get_memory_usage()

        # Memory should be tracked and reasonable
        assert final_memory > 0
        # Memory growth should be bounded (not infinite)
        memory_growth = final_memory - initial_memory
        assert memory_growth < 500, f"Excessive memory growth: {memory_growth} MB"
