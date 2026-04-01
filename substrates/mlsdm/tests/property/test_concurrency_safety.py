"""
Concurrency Tests for Memory Operations.

This test suite validates thread safety and race condition prevention
in the core memory components (PELM, QILM, MultiLevelSynapticMemory).
"""

import threading
from queue import Queue

import numpy as np
import pytest


class TestPELMConcurrency:
    """Concurrency tests for PhaseEntangledLatticeMemory."""

    @pytest.mark.security
    def test_concurrent_entangle_retrieve_isolation(self):
        """
        Test that concurrent entangle and retrieve operations maintain isolation.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=500)
        errors: Queue = Queue()

        def entangle_worker(worker_id: int, iterations: int) -> None:
            """Worker that adds vectors."""
            try:
                for i in range(iterations):
                    vector = [float(worker_id * 1000 + i)] * 10
                    phase = (worker_id * 10 + i) % 100 / 100.0
                    pelm.entangle(vector, phase)
            except Exception as e:
                errors.put(("entangle", worker_id, str(e)))

        def retrieve_worker(worker_id: int, iterations: int) -> None:
            """Worker that retrieves vectors."""
            try:
                for i in range(iterations):
                    query = [float(i)] * 10
                    phase = i % 100 / 100.0
                    results = pelm.retrieve(query, phase, phase_tolerance=0.2)
                    # Should return a list (possibly empty)
                    assert isinstance(results, list)
            except Exception as e:
                errors.put(("retrieve", worker_id, str(e)))

        # Create mixed workers
        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=entangle_worker, args=(i, 50)))
            threads.append(threading.Thread(target=retrieve_worker, args=(i, 50)))

        # Run all threads
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for errors
        assert errors.empty(), f"Concurrency errors: {list(errors.queue)}"

        # State should be consistent
        assert not pelm.detect_corruption()
        assert 0 <= pelm.size <= pelm.capacity

    @pytest.mark.security
    def test_concurrent_capacity_overflow(self):
        """
        Test behavior when concurrent writes exceed capacity.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        small_capacity = 50
        pelm = PhaseEntangledLatticeMemory(dimension=5, capacity=small_capacity)
        errors: Queue = Queue()

        def writer(worker_id: int, count: int) -> None:
            try:
                for i in range(count):
                    vector = [float(worker_id), float(i)] + [0.0] * 3
                    pelm.entangle(vector, 0.5)
            except Exception as e:
                errors.put((worker_id, str(e)))

        # Launch more writes than capacity
        num_workers = 5
        writes_per_worker = 30  # Total: 150 > capacity 50

        threads = [
            threading.Thread(target=writer, args=(i, writes_per_worker)) for i in range(num_workers)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not have errors (overflow is handled by wrapping)
        assert errors.empty(), f"Overflow errors: {list(errors.queue)}"

        # Size should be capped at capacity
        assert pelm.size == small_capacity
        assert not pelm.detect_corruption()

    @pytest.mark.security
    def test_concurrent_corruption_recovery(self):
        """
        Test that concurrent operations don't interfere with corruption recovery.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=5, capacity=100)
        errors: Queue = Queue()
        lock = threading.Lock()
        operations_done = 0
        progress = threading.Condition()

        def writer(worker_id: int, count: int) -> None:
            nonlocal operations_done
            for i in range(count):
                try:
                    vector = [float(worker_id + i)] * 5
                    pelm.entangle(vector, 0.5)
                    with progress:
                        operations_done += 1
                        progress.notify_all()
                except Exception as e:
                    errors.put((worker_id, str(e)))

        def corrupter() -> None:
            """Periodically corrupt and let auto-recovery handle it."""
            for threshold in (10, 40, 70):
                with progress:
                    assert progress.wait_for(
                        lambda t=threshold: operations_done >= t, timeout=2.0
                    )
                with lock:
                    pelm.pointer = 9999  # Corrupt

        threads = [threading.Thread(target=writer, args=(i, 30)) for i in range(3)]
        threads.append(threading.Thread(target=corrupter))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final state should be recovered
        if pelm.detect_corruption():
            pelm.auto_recover()

        assert not pelm.detect_corruption()


class TestMultiLevelMemoryConcurrency:
    """Concurrency tests for MultiLevelSynapticMemory."""

    @pytest.mark.security
    def test_concurrent_level_updates(self):
        """
        Test concurrent updates across memory levels.
        """
        from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory

        memory = MultiLevelSynapticMemory(dimension=10)
        errors: Queue = Queue()

        def update_worker(worker_id: int, iterations: int) -> None:
            np.random.seed(worker_id)
            try:
                for _ in range(iterations):
                    vector = np.random.randn(10).astype(np.float32)
                    vector = vector / np.linalg.norm(vector)
                    memory.update(vector)
            except Exception as e:
                errors.put((worker_id, str(e)))

        threads = [threading.Thread(target=update_worker, args=(i, 50)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors.empty(), f"Concurrent errors: {list(errors.queue)}"

    @pytest.mark.security
    def test_concurrent_state_access(self):
        """
        Test that concurrent state access is safe.
        """
        from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory

        memory = MultiLevelSynapticMemory(dimension=5)
        errors: Queue = Queue()

        # Initialize with some data
        for _ in range(10):
            vec = np.random.randn(5).astype(np.float32)
            memory.update(vec / np.linalg.norm(vec))

        def state_reader(worker_id: int, iterations: int) -> None:
            try:
                for _ in range(iterations):
                    l1, l2, l3 = memory.get_state()
                    # Should always return valid arrays
                    assert l1.shape == (5,)
                    assert l2.shape == (5,)
                    assert l3.shape == (5,)
            except Exception as e:
                errors.put((worker_id, str(e)))

        def update_worker(worker_id: int, iterations: int) -> None:
            np.random.seed(worker_id)
            try:
                for _ in range(iterations):
                    vec = np.random.randn(5).astype(np.float32)
                    memory.update(vec / np.linalg.norm(vec))
            except Exception as e:
                errors.put((worker_id, str(e)))

        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=state_reader, args=(i, 20)))
            threads.append(threading.Thread(target=update_worker, args=(i + 10, 20)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors.empty(), f"Concurrent errors: {list(errors.queue)}"


class TestCognitiveControllerConcurrency:
    """Concurrency tests for CognitiveController."""

    @pytest.mark.security
    def test_concurrent_event_processing(self):
        """
        Test concurrent event processing doesn't corrupt state.
        """
        from mlsdm.core.cognitive_controller import CognitiveController

        controller = CognitiveController(dim=10)
        errors: Queue = Queue()
        results: Queue = Queue()

        def process_worker(worker_id: int, count: int) -> None:
            np.random.seed(worker_id)
            try:
                for i in range(count):
                    vector = np.random.randn(10).astype(np.float32)
                    vector = vector / np.linalg.norm(vector)
                    moral_value = 0.5 + (np.random.random() - 0.5) * 0.4
                    state = controller.process_event(vector, moral_value)
                    results.put((worker_id, i, state["rejected"]))
            except Exception as e:
                errors.put((worker_id, str(e)))

        threads = [threading.Thread(target=process_worker, args=(i, 20)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors.empty(), f"Concurrent errors: {list(errors.queue)}"

        # Should have processed all events
        assert results.qsize() == 100


class TestRateLimiterConcurrency:
    """Concurrency tests for rate limiter."""

    @pytest.mark.security
    def test_concurrent_rate_limiting_accuracy(self):
        """
        Test that rate limiter accurately tracks across concurrent requests.
        """
        from mlsdm.security.rate_limit import RateLimiter

        # 10 requests per 60 second window
        limiter = RateLimiter(requests_per_window=10, window_seconds=60)

        allowed_count = [0]
        blocked_count = [0]
        lock = threading.Lock()

        def requester(client_id: str, count: int) -> None:
            for _ in range(count):
                result = limiter.is_allowed(client_id)
                with lock:
                    if result:
                        allowed_count[0] += 1
                    else:
                        blocked_count[0] += 1

        # Many concurrent requests from same client
        threads = [threading.Thread(target=requester, args=("client1", 20)) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total requests: 100
        # Initial capacity: 10
        # Some should be blocked (exact count depends on timing)
        total = allowed_count[0] + blocked_count[0]
        assert total == 100, f"Total count mismatch: {total}"
        assert blocked_count[0] > 0, "Should have blocked some requests"


class TestStressConditions:
    """Stress tests under adverse conditions."""

    @pytest.mark.slow
    @pytest.mark.security
    def test_pelm_stress_high_contention(self):
        """
        Stress test PELM under high contention.
        """
        from mlsdm.memory import PhaseEntangledLatticeMemory

        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=1000)
        errors: Queue = Queue()
        operations_completed = [0]
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            np.random.seed(worker_id)
            for i in range(100):
                try:
                    op = np.random.choice(["entangle", "retrieve"])
                    if op == "entangle":
                        vec = np.random.randn(10).tolist()
                        phase = np.random.random()
                        pelm.entangle(vec, phase)
                    else:
                        query = np.random.randn(10).tolist()
                        phase = np.random.random()
                        pelm.retrieve(query, phase, phase_tolerance=0.3)

                    with lock:
                        operations_completed[0] += 1
                except Exception as e:
                    errors.put((worker_id, i, str(e)))

        # 10 concurrent workers, each doing 100 ops
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors.empty(), f"Stress test errors: {list(errors.queue)}"
        assert operations_completed[0] == 1000
        assert not pelm.detect_corruption()

    @pytest.mark.slow
    @pytest.mark.security
    def test_moral_filter_stress_rapid_adaptation(self):
        """
        Stress test moral filter with rapid adaptations.
        """
        from mlsdm.cognition.moral_filter_v2 import MoralFilterV2

        moral = MoralFilterV2(initial_threshold=0.5)
        errors: Queue = Queue()

        def adapter(worker_id: int) -> None:
            np.random.seed(worker_id)
            try:
                for _ in range(500):
                    # Rapid alternation
                    moral.adapt(np.random.random() > 0.5)
            except Exception as e:
                errors.put((worker_id, str(e)))

        threads = [threading.Thread(target=adapter, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors.empty()
        # Threshold should remain bounded
        assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
