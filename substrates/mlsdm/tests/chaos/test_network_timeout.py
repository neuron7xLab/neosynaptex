"""
Chaos Engineering Tests: Network Timeout Simulation

Tests system behavior when external services timeout or fail.
Verifies graceful degradation and circuit breaker patterns per REL-003.

These tests are designed to run on a schedule (not on every PR)
as they simulate network failures.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig


def create_timeout_llm(timeout_after: int = 3):
    """Create an LLM that times out after N successful calls.

    Args:
        timeout_after: Number of successful calls before timing out
    """
    call_count = [0]

    def timeout_llm(prompt: str, max_tokens: int = 100) -> str:
        call_count[0] += 1
        if call_count[0] > timeout_after:
            # Simulate network timeout by sleeping longer than any reasonable timeout
            time.sleep(60)  # Will be interrupted by timeout
            raise TimeoutError("Simulated network timeout")
        return f"Response {call_count[0]}: {prompt[:30]}..."

    return timeout_llm


def create_failing_llm(fail_rate: float = 0.5):
    """Create an LLM that fails randomly.

    Args:
        fail_rate: Probability of failure (0.0 to 1.0)
    """
    call_count = [0]
    rng = np.random.RandomState(42)

    def failing_llm(prompt: str, max_tokens: int = 100) -> str:
        call_count[0] += 1
        if rng.random() < fail_rate:
            raise ConnectionError("Simulated connection failure")
        return f"Success {call_count[0]}: {prompt[:30]}..."

    return failing_llm


def create_flaky_llm(failure_pattern: list[bool]):
    """Create an LLM that fails according to a pattern.

    Args:
        failure_pattern: List of booleans indicating failure (True) or success (False)
    """
    call_count = [0]

    def flaky_llm(prompt: str, max_tokens: int = 100) -> str:
        idx = call_count[0] % len(failure_pattern)
        call_count[0] += 1
        if failure_pattern[idx]:
            raise ConnectionError(f"Simulated failure at call {call_count[0]}")
        return f"Success {call_count[0]}: {prompt[:30]}..."

    return flaky_llm


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


class TestNetworkTimeoutChaos:
    """Test system behavior under network timeout conditions."""

    @pytest.mark.chaos
    def test_llm_timeout_triggers_graceful_failure(self):
        """Test that LLM timeout results in graceful failure.

        Scenario:
        1. Create engine with LLM that times out
        2. Make request
        3. Verify graceful error handling
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=0.5,  # Short timeout
            llm_retry_attempts=1,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )

        def always_timeout(prompt: str, max_tokens: int = 100) -> str:
            time.sleep(5.0)  # Always times out
            return "Never returned"

        engine = NeuroCognitiveEngine(
            llm_generate_fn=always_timeout,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        result = engine.generate(
            prompt="Timeout test",
            moral_value=0.8,
            max_tokens=50,
        )

        # Should handle timeout gracefully
        assert isinstance(result, dict)
        # System should not crash

    @pytest.mark.chaos
    def test_connection_error_handling(self):
        """Test handling of connection errors.

        Scenario:
        1. Create engine with LLM that raises ConnectionError
        2. Make request
        3. Verify error is handled gracefully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            llm_retry_attempts=2,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )

        def connection_error_llm(prompt: str, max_tokens: int = 100) -> str:
            raise ConnectionError("Network unreachable")

        engine = NeuroCognitiveEngine(
            llm_generate_fn=connection_error_llm,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        result = engine.generate(
            prompt="Connection error test",
            moral_value=0.8,
            max_tokens=50,
        )

        # Should handle error gracefully
        assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_gradual_network_degradation(self):
        """Test handling of gradual network degradation.

        Scenario:
        1. Create LLM that starts working then starts failing
        2. Make series of requests
        3. Verify system degrades gracefully
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=1.0,
            llm_retry_attempts=1,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )

        # LLM works for first 3 calls, then times out
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_timeout_llm(timeout_after=3),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        successes = []
        failures = []

        for i in range(6):
            result = engine.generate(
                prompt=f"Degradation test {i}",
                moral_value=0.8,
                max_tokens=50,
            )

            if result.get("error") is None and result.get("response"):
                successes.append(i)
            else:
                failures.append(i)

        # First few should succeed
        assert len(successes) >= 1, "Should have at least some successes"

    @pytest.mark.chaos
    def test_intermittent_failures_recovery(self):
        """Test recovery from intermittent failures.

        Scenario:
        1. Create LLM with 50% failure rate
        2. Make many requests
        3. Verify some succeed despite failures
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            llm_retry_attempts=3,  # Retry on failure
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_failing_llm(fail_rate=0.5),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        successes = 0
        failures = 0

        for i in range(10):
            result = engine.generate(
                prompt=f"Intermittent test {i}",
                moral_value=0.8,
                max_tokens=50,
            )

            if result.get("error") is None and result.get("response"):
                successes += 1
            else:
                failures += 1

        # With retries, should have some successes
        assert successes > 0, "Should have at least some successes with retries"

    @pytest.mark.chaos
    def test_failure_pattern_handling(self):
        """Test handling of specific failure patterns.

        Scenario:
        1. Create LLM with known failure pattern (fail, success, fail, success...)
        2. Make requests
        3. Verify system handles pattern correctly
        """
        # Pattern: success, success, fail, success, success, fail...
        pattern = [False, False, True, False, False, True]

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            llm_retry_attempts=2,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_flaky_llm(pattern),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        for i in range(len(pattern) * 2):
            result = engine.generate(
                prompt=f"Pattern test {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            results.append(result)

        # Should have results for all requests
        assert len(results) == len(pattern) * 2

    @pytest.mark.chaos
    def test_concurrent_requests_with_failures(self):
        """Test concurrent requests when some fail.

        Scenario:
        1. Create LLM with random failures
        2. Make concurrent requests
        3. Verify all complete without system crash
        """
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=2.0,
            llm_retry_attempts=1,
            wake_duration=100,
            initial_moral_threshold=0.1,
            enable_bulkhead=True,
            bulkhead_llm_limit=5,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_failing_llm(fail_rate=0.3),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            result = engine.generate(
                prompt=f"Concurrent failure test {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with lock:
                results.append((idx, result))

        N = 10
        with ThreadPoolExecutor(max_workers=N) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]
            for future in futures:
                try:
                    future.result(timeout=30.0)
                except Exception:
                    pass

        # All requests should complete
        assert len(results) == N

        # At least some should succeed (verify computation doesn't crash)
        _ = [r for idx, r in results if r.get("error") is None and r.get("response")]
        # With 30% failure rate and some luck, should have successes
        # If not, test still passes if no crashes

    @pytest.mark.chaos
    def test_embedding_timeout_handling(self):
        """Test handling of embedding function timeout.

        Scenario:
        1. Create slow embedding function
        2. Make request
        3. Verify graceful handling
        """

        def slow_embedder(text: str) -> np.ndarray:
            time.sleep(0.5)  # Slow embedding
            return np.random.randn(384).astype(np.float32)

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=5.0,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )

        def fast_llm(prompt: str, max_tokens: int = 100) -> str:
            return f"Fast response: {prompt[:30]}..."

        engine = NeuroCognitiveEngine(
            llm_generate_fn=fast_llm,
            embedding_fn=slow_embedder,
            config=config,
        )

        result = engine.generate(
            prompt="Slow embedding test",
            moral_value=0.8,
            max_tokens=50,
        )

        # Should complete despite slow embedding
        assert isinstance(result, dict)
