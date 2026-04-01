"""
Chaos Engineering Tests: Slow LLM Simulation

Tests system behavior when LLM responses are slow or delayed.
Verifies timeout handling and graceful degradation per REL-003 and REL-004.

These tests are designed to run on a schedule (not on every PR)
as they may be time-intensive.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig


def create_slow_llm(delay_seconds: float = 1.0):
    """Create an LLM that simulates slow responses.

    Args:
        delay_seconds: Time to delay before returning response
    """

    def slow_llm(prompt: str, max_tokens: int = 100) -> str:
        time.sleep(delay_seconds)
        return f"Delayed response to: {prompt[:50]}..."

    return slow_llm


def create_variable_slow_llm(min_delay: float = 0.1, max_delay: float = 2.0):
    """Create an LLM with variable response times.

    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    call_count = [0]

    def variable_llm(prompt: str, max_tokens: int = 100) -> str:
        call_count[0] += 1
        # Gradually increase delay to simulate degradation
        delay = min(min_delay + (call_count[0] * 0.1), max_delay)
        time.sleep(delay)
        return f"Response {call_count[0]} to: {prompt[:30]}..."

    return variable_llm


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


class TestSlowLLMChaos:
    """Test system behavior with slow LLM responses."""

    @pytest.mark.chaos
    def test_slow_llm_completes_within_timeout(self):
        """Test that slow LLM responses complete when within timeout.

        Scenario:
        1. Create engine with slow LLM (but within timeout)
        2. Make request
        3. Verify request completes successfully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,  # 5 second timeout
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_slow_llm(delay_seconds=0.5),  # 500ms delay
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        result = engine.generate(
            prompt="Test slow LLM",
            moral_value=0.8,
            max_tokens=50,
        )

        # Should complete successfully despite delay
        assert result.get("error") is None
        assert result.get("response") is not None
        assert "Delayed response" in result["response"]

    @pytest.mark.chaos
    def test_very_slow_llm_timeout_handling(self):
        """Test graceful handling of LLM timeout.

        Scenario:
        1. Create engine with very slow LLM (exceeds timeout)
        2. Make request with short timeout
        3. Verify timeout is handled gracefully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=0.5,  # Short timeout
            llm_retry_attempts=1,  # Don't retry
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_slow_llm(delay_seconds=2.0),  # Too slow
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        result = engine.generate(
            prompt="Test timeout",
            moral_value=0.8,
            max_tokens=50,
        )

        # Should handle timeout gracefully
        # The exact behavior depends on engine implementation
        # but should not crash
        assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_concurrent_slow_requests(self):
        """Test system under concurrent slow requests.

        Scenario:
        1. Create engine with moderately slow LLM
        2. Make multiple concurrent requests
        3. Verify all complete or timeout gracefully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
            enable_bulkhead=True,
            bulkhead_llm_limit=3,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_slow_llm(delay_seconds=0.5),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            result = engine.generate(
                prompt=f"Concurrent request {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with lock:
                results.append(result)

        N = 5
        with ThreadPoolExecutor(max_workers=N) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]
            for future in futures:
                try:
                    future.result(timeout=30.0)
                except Exception:
                    pass  # Graceful handling

        # All requests should have completed (success or rejection)
        assert len(results) == N
        for result in results:
            assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_degrading_llm_performance(self):
        """Test system behavior as LLM performance degrades over time.

        Scenario:
        1. Create engine with LLM that gets slower over time
        2. Make series of requests
        3. Verify system handles degradation gracefully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=3.0,  # 3 second timeout
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_variable_slow_llm(min_delay=0.1, max_delay=1.5),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Track request timings
        timings = []
        successes = 0
        failures = 0

        for i in range(10):
            start = time.time()
            result = engine.generate(
                prompt=f"Degrading performance test {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            elapsed = time.time() - start
            timings.append(elapsed)

            if result.get("error") is None and result.get("response"):
                successes += 1
            else:
                failures += 1

        # Should have some successes (at least early requests)
        assert successes > 0, "No requests succeeded"

        # Later requests should take longer than earlier ones
        if len(timings) >= 4:
            early_avg = sum(timings[:3]) / 3
            late_avg = sum(timings[-3:]) / 3
            # Expect late requests to be slower (degradation)
            assert late_avg >= early_avg * 0.8, "Expected degradation not observed"

    @pytest.mark.chaos
    def test_intermittent_slow_responses(self):
        """Test handling of intermittently slow LLM.

        Scenario:
        1. Create LLM that is sometimes fast, sometimes slow
        2. Make series of requests
        3. Verify system handles variable latency
        """
        call_count = [0]

        def intermittent_llm(prompt: str, max_tokens: int = 100) -> str:
            call_count[0] += 1
            # Every 3rd call is slow
            if call_count[0] % 3 == 0:
                time.sleep(0.5)  # Slow
            else:
                time.sleep(0.05)  # Fast
            return f"Response {call_count[0]}: {prompt[:20]}..."

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=2.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=intermittent_llm,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        fast_times = []
        slow_times = []

        for i in range(9):
            start = time.time()
            result = engine.generate(
                prompt=f"Intermittent test {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            elapsed = time.time() - start

            if (i + 1) % 3 == 0:
                slow_times.append(elapsed)
            else:
                fast_times.append(elapsed)

            # All should complete
            assert result.get("response") is not None or result.get("error") is not None

        # Slow times should be notably longer than fast times
        if fast_times and slow_times:
            avg_fast = sum(fast_times) / len(fast_times)
            avg_slow = sum(slow_times) / len(slow_times)
            assert avg_slow > avg_fast, "Slow responses should be slower"
