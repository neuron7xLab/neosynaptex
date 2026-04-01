"""
Chaos Engineering Tests: Resource Contention Simulation

Tests system behavior under CPU starvation and thread contention conditions.
Verifies graceful degradation and resource management per REL-003.

These tests are designed to run on a schedule (not on every PR)
as they may be resource-intensive.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig


def create_fast_llm():
    """Create a fast LLM for testing resource contention."""

    def fast_llm(prompt: str, max_tokens: int = 100) -> str:
        return f"Response to: {prompt[:50]}..."

    return fast_llm


def create_fake_embedder(dim: int = 384):
    """Create a thread-safe fake embedding function."""

    def fake_embedder(text: str) -> np.ndarray:
        text_hash = abs(hash(text))
        local_rng = np.random.RandomState(text_hash % (2**31))
        vec = local_rng.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec

    return fake_embedder


class TestCPUStarvationChaos:
    """Test system behavior under CPU starvation conditions."""

    @pytest.mark.chaos
    def test_high_cpu_load_handling(self):
        """Test that system handles high CPU load gracefully.

        Scenario:
        1. Create background threads doing CPU-intensive work
        2. Make requests to engine concurrently
        3. Verify requests complete (possibly with degraded latency)
        4. Verify no deadlocks or crashes
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=10.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        stop_event = threading.Event()
        cpu_load_count = [0]

        def cpu_heavy_worker():
            """Simulate CPU-heavy work."""
            while not stop_event.is_set():
                # CPU-intensive calculation
                _ = [i * i for i in range(10000)]
                cpu_load_count[0] += 1
                if cpu_load_count[0] % 100 == 0:
                    time.sleep(0.001)  # Yield occasionally

        # Start background CPU load
        cpu_threads = []
        for _ in range(4):
            t = threading.Thread(target=cpu_heavy_worker, daemon=True)
            t.start()
            cpu_threads.append(t)

        results = []
        try:
            # Make requests under CPU pressure
            for i in range(10):
                start = time.time()
                result = engine.generate(
                    prompt=f"CPU pressure test {i}",
                    moral_value=0.8,
                    max_tokens=50,
                )
                elapsed = time.time() - start
                results.append((result, elapsed))
        finally:
            stop_event.set()
            for t in cpu_threads:
                t.join(timeout=1.0)

        # Verify all requests completed
        assert len(results) == 10

        # Verify results are valid (not crashed)
        for result, elapsed in results:
            assert isinstance(result, dict)
            assert elapsed < 10.0  # Should complete within timeout

    @pytest.mark.chaos
    def test_thread_pool_exhaustion(self):
        """Test behavior when thread pool is heavily contested.

        Scenario:
        1. Create many concurrent requests exceeding pool size
        2. Verify bulkhead pattern works correctly
        3. Verify no deadlocks
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
            enable_bulkhead=True,
            bulkhead_llm_limit=3,  # Small limit
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        lock = threading.Lock()

        def worker(idx: int) -> dict:
            result = engine.generate(
                prompt=f"Exhaustion test {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with lock:
                results.append((idx, result))
            return result

        # Request more than pool can handle simultaneously
        N = 20
        with ThreadPoolExecutor(max_workers=N) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]
            for future in as_completed(futures, timeout=60.0):
                try:
                    future.result()
                except Exception:
                    pass  # Some may be rejected

        # All should complete or be rejected gracefully
        assert len(results) == N
        for idx, result in results:
            assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_lock_contention_handling(self):
        """Test handling of heavy lock contention.

        Scenario:
        1. Make rapid sequential requests to stress internal locks
        2. Verify no deadlocks occur
        3. Verify state remains consistent
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Rapid sequential requests
        results = []
        for i in range(50):
            result = engine.generate(
                prompt=f"Lock contention test {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            results.append(result)

        # All should complete
        assert len(results) == 50
        for result in results:
            assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_concurrent_memory_access(self):
        """Test concurrent access to shared memory structures.

        Scenario:
        1. Multiple threads access memory simultaneously
        2. Verify thread safety
        3. Verify no corruption
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        errors = []
        lock = threading.Lock()

        def memory_worker(idx: int) -> None:
            try:
                for j in range(5):
                    result = engine.generate(
                        prompt=f"Memory access test {idx}-{j}",
                        moral_value=0.8,
                        max_tokens=50,
                    )
                    # Verify result structure
                    if not isinstance(result, dict):
                        with lock:
                            errors.append(f"Invalid result type at {idx}-{j}")
            except Exception as e:
                with lock:
                    errors.append(f"Exception at {idx}: {e}")

        threads = []
        for i in range(10):
            t = threading.Thread(target=memory_worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join(timeout=30.0)

        # No errors should have occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestDeadlockPrevention:
    """Test that system prevents deadlocks under various conditions."""

    @pytest.mark.chaos
    def test_no_deadlock_under_rapid_requests(self):
        """Verify no deadlock under rapid request bursts.

        Scenario:
        1. Send rapid burst of requests
        2. All should complete within timeout
        3. No thread should hang indefinitely
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        completed = []
        timeout_seconds = 30.0

        def rapid_worker(idx: int):
            result = engine.generate(
                prompt=f"Rapid request {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            completed.append((idx, result))

        threads = []
        start_time = time.time()

        for i in range(30):
            t = threading.Thread(target=rapid_worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            remaining = timeout_seconds - (time.time() - start_time)
            if remaining > 0:
                t.join(timeout=remaining)
            if t.is_alive():
                pytest.fail("Thread hung - possible deadlock detected")

        # All should have completed
        assert len(completed) == 30
