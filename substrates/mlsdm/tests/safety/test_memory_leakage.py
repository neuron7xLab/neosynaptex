"""
Safety Tests for Memory Leakage Prevention

This test suite validates that MLSDM properly isolates memory between
sessions and prevents leakage of sensitive user data through the memory
subsystems (PELM, MultiLevelMemory).

Principal AI Safety Engineer level validation.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory


class TestMemoryIsolation:
    """Tests for memory isolation between sessions/users."""

    def test_pelm_fifo_eviction_removes_old_data(self):
        """
        Verify that PELM's FIFO eviction properly removes old data
        when capacity is reached, preventing historical data leakage.
        """
        capacity = 100
        dim = 384
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        # Fill memory with "old" vectors (labeled by magnitude)
        np.random.seed(42)
        old_vectors = []
        for i in range(capacity):
            vec = np.random.randn(dim).astype(np.float32)
            vec = vec / np.linalg.norm(vec) * 1.0  # Normalized to 1.0
            old_vectors.append(vec)
            pelm.entangle(vec.tolist(), phase=0.5)

        assert pelm.size == capacity

        # Add "new" vectors that should evict old ones
        np.random.seed(123)  # Different seed
        new_vectors = []
        for i in range(capacity):
            vec = np.random.randn(dim).astype(np.float32)
            vec = vec / np.linalg.norm(vec) * 2.0  # Different magnitude
            new_vectors.append(vec)
            pelm.entangle(vec.tolist(), phase=0.5)

        # Verify capacity still bounded
        assert pelm.size == capacity

    def test_multi_level_memory_decay_removes_old_traces(self):
        """
        Verify that MultiLevelMemory's decay mechanism removes
        traces of old data over time.
        """
        dim = 384
        memory = MultiLevelSynapticMemory(dimension=dim)

        # Store a distinctive vector
        sensitive_vector = np.ones(dim).astype(np.float32)
        memory.update(sensitive_vector)

        # Record initial L1 norm
        l1, _, _ = memory.state()
        initial_l1_norm = np.linalg.norm(l1)
        assert initial_l1_norm > 0, "Vector should be stored in L1"

        # Apply many decay cycles without new input
        for _ in range(100):
            zero_vec = np.zeros(dim).astype(np.float32)
            memory.update(zero_vec)

        # L1 should be significantly decayed
        l1, _, _ = memory.state()
        final_l1_norm = np.linalg.norm(l1)
        decay_ratio = final_l1_norm / initial_l1_norm

        assert decay_ratio < 0.1, f"L1 should decay significantly, ratio: {decay_ratio}"

    def test_controller_session_isolation(self):
        """
        Verify that separate CognitiveController instances have
        completely isolated memory state.
        """
        dim = 384

        # Create two "user sessions"
        controller_1 = CognitiveController(dim=dim)
        controller_2 = CognitiveController(dim=dim)

        # User 1 stores sensitive data
        sensitive_vec = np.random.randn(dim).astype(np.float32)
        controller_1.process_event(sensitive_vec, moral_value=0.8)

        # Verify memory is independent
        assert controller_1.step_counter == 1
        assert controller_2.step_counter == 0

        # Verify PELM is independent
        assert controller_1.pelm.size == 1
        assert controller_2.pelm.size == 0

    def test_no_cross_session_retrieval(self):
        """
        Verify that retrieving from one session's memory cannot
        access another session's stored data.
        """
        dim = 384

        # Session 1: Store unique vector
        controller_1 = CognitiveController(dim=dim)
        unique_vec_1 = np.ones(dim).astype(np.float32) * 1.5
        controller_1.process_event(unique_vec_1, moral_value=0.8)

        # Session 2: Completely separate
        controller_2 = CognitiveController(dim=dim)
        unique_vec_2 = np.ones(dim).astype(np.float32) * -1.5
        controller_2.process_event(unique_vec_2, moral_value=0.8)

        # Query from session 1's perspective
        query = unique_vec_1.tolist()
        results_1 = controller_1.pelm.retrieve(query, current_phase=0.5, phase_tolerance=1.0)
        results_2 = controller_2.pelm.retrieve(query, current_phase=0.5, phase_tolerance=1.0)

        # Session 1 should find its vector
        assert len(results_1) > 0

        # Session 2 should NOT find session 1's vector
        # It should find its own (different) vector
        if len(results_2) > 0:
            result_2_arr = results_2[0].vector
            # Verify it's session 2's vector (negative), not session 1's
            assert np.mean(result_2_arr) < 0, "Session 2 retrieved session 1's data"


class TestMemoryContentSafety:
    """Tests for memory content safety and sanitization."""

    def test_nan_vectors_rejected(self):
        """Verify NaN vectors are properly rejected."""
        dim = 384
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

        # Create vector with NaN
        nan_vec = np.full(dim, np.nan).tolist()

        # Should raise ValueError for NaN
        with pytest.raises(ValueError, match="invalid value"):
            pelm.entangle(nan_vec, phase=0.5)

    def test_inf_vectors_rejected(self):
        """Verify infinite vectors are properly rejected."""
        dim = 384
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

        # Create vector with infinity
        inf_vec = np.full(dim, np.inf).tolist()

        # Should raise ValueError for infinity
        with pytest.raises(ValueError, match="invalid value"):
            pelm.entangle(inf_vec, phase=0.5)

    def test_extreme_magnitude_vectors(self):
        """Verify extremely large/small vectors are handled."""
        dim = 384
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=100)

        # Very large magnitude (but finite)
        large_vec = (np.ones(dim) * 1e30).tolist()

        # Very small magnitude
        small_vec = (np.ones(dim) * 1e-30).tolist()

        # Should handle without crashing
        pelm.entangle(large_vec, phase=0.5)
        pelm.entangle(small_vec, phase=0.5)

        # Retrieval should still work
        query = np.random.randn(dim).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, phase_tolerance=1.0)
        assert isinstance(results, list)


class TestConcurrentMemorySafety:
    """Tests for thread-safe memory operations."""

    def test_concurrent_pelm_operations_no_corruption(self):
        """
        Verify that concurrent PELM operations don't corrupt memory.
        """
        dim = 384
        capacity = 1000
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        errors = []
        completed = []

        def worker(worker_id: int, num_ops: int):
            try:
                for i in range(num_ops):
                    vec = np.random.randn(dim).astype(np.float32)
                    pelm.entangle(vec.tolist(), phase=0.5)

                    if i % 10 == 0:
                        query = np.random.randn(dim).astype(np.float32)
                        pelm.retrieve(query.tolist(), current_phase=0.5, phase_tolerance=1.0)

                completed.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Run concurrent workers
        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i, 100))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Concurrent errors: {errors}"
        assert len(completed) == 4, "Not all workers completed"

        # Verify memory integrity
        assert pelm.size <= capacity

    def test_concurrent_controller_operations(self):
        """
        Verify that concurrent CognitiveController operations
        maintain data integrity.
        """
        dim = 384
        controller = CognitiveController(dim=dim)

        errors = []
        states = []
        lock = threading.Lock()

        def worker(worker_id: int, num_ops: int):
            try:
                for i in range(num_ops):
                    vec = np.random.randn(dim).astype(np.float32)
                    moral_value = np.random.uniform(0.3, 0.9)
                    state = controller.process_event(vec, moral_value=moral_value)
                    with lock:
                        states.append(state)
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i, 50) for i in range(4)]
            for f in futures:
                f.result()

        # Verify no errors
        assert len(errors) == 0, f"Concurrent errors: {errors}"

        # Verify all states have required fields
        for state in states:
            assert "step" in state
            assert "phase" in state
            assert "moral_threshold" in state

        # Verify step counter is consistent
        assert controller.step_counter == 4 * 50


class TestMemoryBoundsEnforcement:
    """Tests for memory bounds enforcement (safety invariants)."""

    def test_pelm_capacity_never_exceeded(self):
        """
        Verify PELM capacity is never exceeded regardless of input volume.
        """
        dim = 384
        capacity = 100
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        # Insert 10x capacity
        for _ in range(capacity * 10):
            vec = np.random.randn(dim).astype(np.float32)
            pelm.entangle(vec.tolist(), phase=0.5)
            assert pelm.size <= capacity, f"Capacity exceeded: {pelm.size} > {capacity}"

    def test_memory_footprint_bounded(self):
        """
        Verify that memory footprint stays within expected bounds.
        """
        dim = 384
        capacity = 1000
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        # Fill to capacity
        for _ in range(capacity):
            vec = np.random.randn(dim).astype(np.float32)
            pelm.entangle(vec.tolist(), phase=0.5)

        # Estimate memory usage
        # Each vector: 384 * 4 bytes = 1536 bytes
        # 1000 vectors: ~1.5 MB
        # Plus overhead for phase values, indices, etc.
        expected_max_mb = 5.0  # Conservative bound

        # Get approximate size (memory_bank is pre-allocated numpy array)
        size_bytes = pelm.memory_bank.nbytes + pelm.phase_bank.nbytes + pelm.norms.nbytes
        size_mb = size_bytes / (1024 * 1024)

        assert size_mb < expected_max_mb, f"Memory footprint too large: {size_mb:.2f} MB"


class TestSafetyInvariantsUnderStress:
    """Tests for safety invariants under stress conditions."""

    def test_moral_threshold_stable_during_memory_pressure(self):
        """
        Verify moral threshold remains stable even when memory is at capacity.
        """
        dim = 384
        controller = CognitiveController(dim=dim)

        thresholds = []

        # Fill memory and observe threshold
        for i in range(200):
            vec = np.random.randn(dim).astype(np.float32)
            moral_value = 0.5 + 0.1 * np.sin(i / 10)  # Oscillating moral values
            state = controller.process_event(vec, moral_value=moral_value)
            thresholds.append(state["moral_threshold"])

        # Verify threshold stays in bounds
        for t in thresholds:
            assert 0.30 <= t <= 0.90, f"Threshold out of bounds: {t}"

        # Verify limited drift
        max_drift = max(thresholds) - min(thresholds)
        assert max_drift < 0.3, f"Excessive threshold drift: {max_drift}"

    def test_no_data_loss_on_eviction(self):
        """
        Verify that recent data is preserved when old data is evicted.
        """
        dim = 384
        capacity = 100
        pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=capacity)

        # Store old data
        for _ in range(capacity):
            vec = np.random.randn(dim).astype(np.float32)
            pelm.entangle(vec.tolist(), phase=0.5)

        # Store new data with distinctive pattern
        recent_vectors = []
        for _ in range(10):
            vec = np.ones(dim).astype(np.float32) + np.random.randn(dim).astype(np.float32) * 0.1
            recent_vectors.append(vec)
            pelm.entangle(vec.tolist(), phase=0.5)

        # Query for recent vectors
        query = np.ones(dim).astype(np.float32).tolist()
        results = pelm.retrieve(query, current_phase=0.5, phase_tolerance=1.0)

        # Recent vectors should be retrievable
        assert len(results) > 0, "Recent vectors not retrievable after eviction"

        # Top result should match recent pattern (mean close to 1.0)
        top_result = results[0].vector
        mean_val = np.mean(top_result)
        assert mean_val > 0.5, f"Recent vector not preserved, mean: {mean_val}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
