"""Tests for critical bug fixes in cognitive memory system."""
import threading

import numpy as np

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory


class TestMoralValueValidation:
    """Test moral_value validation in process_event()."""

    def test_rejects_moral_value_above_1(self):
        """Test that moral_value > 1.0 is rejected."""
        controller = CognitiveController(dim=384)
        event = np.random.randn(384).astype(np.float32)

        # Should reject moral_value > 1.0
        result = controller.process_event(event, moral_value=1.5)

        assert result["rejected"] is True
        assert "invalid moral_value" in result["note"]
        assert "1.5" in result["note"]

    def test_rejects_moral_value_below_0(self):
        """Test that moral_value < 0.0 is rejected."""
        controller = CognitiveController(dim=384)
        event = np.random.randn(384).astype(np.float32)

        # Should reject moral_value < 0.0
        result = controller.process_event(event, moral_value=-0.5)

        assert result["rejected"] is True
        assert "invalid moral_value" in result["note"]
        assert "-0.5" in result["note"]

    def test_accepts_valid_moral_values(self):
        """Test that valid moral_value in [0.0, 1.0] is accepted."""
        controller = CognitiveController(dim=384)
        event = np.random.randn(384).astype(np.float32)

        # Should accept moral_value = 0.0
        result = controller.process_event(event, moral_value=0.0)
        # May be rejected for other reasons (moral threshold), but not for invalid value
        if result["rejected"]:
            assert "invalid moral_value" not in result["note"]

        # Should accept moral_value = 1.0
        result = controller.process_event(event, moral_value=1.0)
        # May be rejected for other reasons, but not for invalid value
        if result["rejected"]:
            assert "invalid moral_value" not in result["note"]

        # Should accept moral_value = 0.5
        result = controller.process_event(event, moral_value=0.5)
        if result["rejected"]:
            assert "invalid moral_value" not in result["note"]


class TestMoralFilterV2ThreadSafety:
    """Test thread-safety of MoralFilterV2."""

    def test_concurrent_adapt_calls(self):
        """Test that concurrent adapt() calls don't cause race conditions."""
        moral_filter = MoralFilterV2(initial_threshold=0.50)
        num_threads = 10
        calls_per_thread = 100

        def worker():
            for i in range(calls_per_thread):
                # Alternate between accept and reject
                moral_filter.adapt(accepted=(i % 2 == 0))

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify threshold is still within valid range
        assert 0.30 <= moral_filter.threshold <= 0.90
        assert 0.0 <= moral_filter.ema_accept_rate <= 1.0

    def test_concurrent_state_reads(self):
        """Test that concurrent get_state() calls return consistent data."""
        moral_filter = MoralFilterV2(initial_threshold=0.50)
        results = []

        def reader():
            for _ in range(50):
                state = moral_filter.get_state()
                results.append(state)
                # Verify state consistency
                assert 0.30 <= state["threshold"] <= 0.90
                assert 0.0 <= state["ema"] <= 1.0

        def writer():
            for i in range(50):
                moral_filter.adapt(accepted=(i % 3 == 0))

        # Run readers and writers concurrently
        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All results should be valid
        for state in results:
            assert 0.30 <= state["threshold"] <= 0.90
            assert 0.0 <= state["ema"] <= 1.0


class TestMemoryOverheadCalculation:
    """Test memory_usage_bytes() calculation."""

    def test_memory_overhead_multiplier(self):
        """Test that memory overhead multiplier is correctly applied."""
        dimension = 384
        synapse = MultiLevelSynapticMemory(dimension=dimension)

        # Calculate expected size using the same constants as the implementation
        FLOAT32_BYTES = 4
        NUM_ARRAYS = 3  # L1, L2, L3
        METADATA_OVERHEAD = 512  # From implementation
        OLD_MULTIPLIER = 1.15
        NEW_MULTIPLIER = 1.4

        memory_bytes = synapse.memory_usage_bytes()

        # Should be > 5KB (raw arrays + metadata)
        assert memory_bytes > 5000

        # Should be < 10KB (with reasonable overhead)
        assert memory_bytes < 10000

        # Should reflect 1.4x multiplier (not old 1.15x)
        raw_array_bytes = dimension * FLOAT32_BYTES * NUM_ARRAYS
        expected_with_old_multiplier = int((raw_array_bytes + METADATA_OVERHEAD) * OLD_MULTIPLIER)
        expected_with_new_multiplier = int((raw_array_bytes + METADATA_OVERHEAD) * NEW_MULTIPLIER)

        # Should be closer to new multiplier than old
        diff_to_new = abs(memory_bytes - expected_with_new_multiplier)
        diff_to_old = abs(memory_bytes - expected_with_old_multiplier)

        assert diff_to_new < diff_to_old, (
            f"Expected memory_bytes ({memory_bytes}) to be closer to "
            f"new multiplier ({expected_with_new_multiplier}) than "
            f"old multiplier ({expected_with_old_multiplier})"
        )


class TestMoralRejectionDoesNotStore:
    """Test that morally rejected events don't update memory (Bug #1 verification)."""

    # Tolerance for L1 norm change due to natural decay between process_event calls.
    # This accounts for the decay factor applied during event processing even when
    # the event is rejected (step counter increments, causing internal state updates).
    L1_DECAY_TOLERANCE = 0.1

    def test_moral_rejection_no_memory_update(self):
        """Verify that rejected events don't update synaptic memory."""
        controller = CognitiveController(dim=384)
        event = np.random.randn(384).astype(np.float32)

        # Get initial memory state via synaptic memory directly
        initial_l1, _, _ = controller.synaptic.state()
        initial_l1_norm = float(np.linalg.norm(initial_l1))
        initial_pelm_used = controller.pelm.get_state_stats()["used"]

        # Process event with very low moral value (should be rejected)
        result = controller.process_event(event, moral_value=0.0)

        # Verify rejection
        assert result["rejected"] is True
        assert result["note"] == "morally rejected"

        # Get new memory state
        new_l1, _, _ = controller.synaptic.state()
        new_l1_norm = float(np.linalg.norm(new_l1))
        new_pelm_used = controller.pelm.get_state_stats()["used"]

        # Memory should not have changed (except for natural decay)
        # L1 norm should be same or less (due to decay), not increased significantly
        assert new_l1_norm <= initial_l1_norm + self.L1_DECAY_TOLERANCE, (
            f"L1 norm increased after moral rejection: "
            f"{initial_l1_norm} -> {new_l1_norm}"
        )

        # PELM size should not have increased
        assert new_pelm_used == initial_pelm_used, (
            f"PELM size increased after moral rejection: "
            f"{initial_pelm_used} -> {new_pelm_used}"
        )
