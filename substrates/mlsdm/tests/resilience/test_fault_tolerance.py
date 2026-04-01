"""
Resilience and Fault Tolerance Tests for MLSDM.

This test suite validates the system's behavior under adverse conditions:
- Network failures and timeouts
- Memory pressure scenarios
- Unusual/edge-case input data
- Recovery from transient errors
- Graceful degradation under stress

These tests address the production readiness requirements for fault tolerance.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import numpy as np
import pytest

from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.memory import PhaseEntangledLatticeMemory

# ============================================================================
# Test Fixtures
# ============================================================================


def create_stub_llm():
    """Create a deterministic stub LLM function."""

    def stub_llm(prompt: str, max_tokens: int) -> str:
        return f"Response to: {prompt[:30]}"

    return stub_llm


def create_stub_embedder(dim: int = 384):
    """Create a deterministic stub embedding function."""

    def stub_embed(text: str) -> np.ndarray:
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            vec = np.zeros(dim, dtype=np.float32)
            vec[0] = 1.0
        else:
            vec = vec / norm
        return vec

    return stub_embed


# ============================================================================
# Network Failure Resilience Tests
# ============================================================================


class TestNetworkFailureResilience:
    """Tests for resilience against network failures."""

    @pytest.mark.security
    def test_intermittent_network_failure_recovery(self):
        """
        Test recovery from intermittent network failures.

        Simulates a scenario where network fails 3 times then recovers.
        System should eventually succeed with retry logic.
        """
        failure_count = [0]
        max_failures = 3

        def flaky_llm(prompt: str, max_tokens: int) -> str:
            failure_count[0] += 1
            if failure_count[0] <= max_failures:
                raise ConnectionError(f"Network error {failure_count[0]}")
            return "Success after recovery"

        wrapper = LLMWrapper(
            llm_generate_fn=flaky_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=5,
            llm_timeout=30.0,
        )

        result = wrapper.generate(prompt="Test network recovery", moral_value=0.9)

        assert result["accepted"] is True
        assert "Success after recovery" in result["response"]
        assert failure_count[0] == max_failures + 1

    @pytest.mark.security
    def test_permanent_network_failure_graceful(self):
        """
        Test graceful handling of permanent network failure.

        When network is down, system should return structured error response.
        """

        def always_failing_llm(prompt: str, max_tokens: int) -> str:
            raise ConnectionError("Network permanently unavailable")

        wrapper = LLMWrapper(
            llm_generate_fn=always_failing_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=2,
        )

        result = wrapper.generate(prompt="Test permanent failure", moral_value=0.9)

        # Should return structured response, not raise exception
        assert result["accepted"] is False
        assert "generation failed" in result["note"]
        assert result["phase"] is not None  # Metadata still present

    @pytest.mark.security
    def test_embedding_service_timeout(self):
        """
        Test handling of embedding service timeout.
        """

        def slow_embedding(text: str) -> np.ndarray:
            time.sleep(0.5)  # Simulate slow response
            return np.random.randn(384).astype(np.float32)

        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=slow_embedding,
        )

        # Should handle slow embedding gracefully
        result = wrapper.generate(prompt="Test timeout", moral_value=0.9)

        # Either succeeds (if no strict timeout) or fails gracefully
        assert "response" in result or "note" in result
        assert "accepted" in result

    @pytest.mark.security
    def test_partial_network_recovery(self):
        """
        Test system behavior during partial network recovery.

        Simulates pattern: fail, succeed, fail, succeed
        """
        call_count = [0]

        def intermittent_llm(prompt: str, max_tokens: int) -> str:
            call_count[0] += 1
            if call_count[0] % 2 == 1:  # Odd calls fail
                raise ConnectionError("Intermittent failure")
            return f"Success on call {call_count[0]}"

        wrapper = LLMWrapper(
            llm_generate_fn=intermittent_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=3,
        )

        result = wrapper.generate(prompt="Test partial recovery", moral_value=0.9)

        assert result["accepted"] is True
        assert "Success" in result["response"]


# ============================================================================
# Memory Pressure Resilience Tests
# ============================================================================


class TestMemoryPressureResilience:
    """Tests for resilience under memory pressure."""

    @pytest.mark.security
    def test_memory_at_capacity_still_works(self):
        """
        Test that system works correctly when memory is at capacity.
        """
        controller = CognitiveController(dim=384)
        pelm_capacity = controller.pelm.capacity

        # Fill memory to capacity
        for i in range(pelm_capacity + 100):  # Overflow
            vec = np.random.randn(384).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            controller.process_event(vec, moral_value=0.8)

        # Verify capacity constraint
        assert controller.pelm.size <= pelm_capacity

        # System should still work
        new_vec = np.random.randn(384).astype(np.float32)
        new_vec = new_vec / np.linalg.norm(new_vec)
        result = controller.process_event(new_vec, moral_value=0.8)

        assert "step" in result
        assert "rejected" in result

    @pytest.mark.security
    def test_rapid_memory_allocation_deallocation(self):
        """
        Test memory stability under rapid allocation/deallocation.
        """
        pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=100)

        # Rapid cycle of entangle/retrieve operations
        for i in range(500):
            vec = np.random.randn(384).astype(np.float32).tolist()
            phase = (i % 10) / 10.0
            pelm.entangle(vec, phase=phase)

            if i % 10 == 0 and pelm.size > 0:
                query = np.random.randn(384).astype(np.float32).tolist()
                pelm.retrieve(query, current_phase=phase, phase_tolerance=0.3, top_k=5)

        # Memory should not be corrupted
        assert not pelm.detect_corruption()
        assert pelm.size <= pelm.capacity

    @pytest.mark.security
    def test_memory_recovery_after_corruption_attempt(self):
        """
        Test that memory recovers from corruption attempts.
        """
        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

        # Add some data
        for i in range(50):
            vec = [float(i)] * 10
            pelm.entangle(vec, phase=0.5)

        # Simulate corruption (manually corrupt pointer)
        pelm.pointer = 9999  # Invalid pointer

        # Detection should work
        assert pelm.detect_corruption()

        # Recovery should work
        assert pelm.auto_recover()
        assert not pelm.detect_corruption()


# ============================================================================
# Unusual Input Data Resilience Tests
# ============================================================================


class TestUnusualInputResilience:
    """Tests for resilience against unusual input data."""

    @pytest.mark.security
    @pytest.mark.parametrize(
        "edge_value",
        [
            0.0,  # Minimum moral value
            1.0,  # Maximum moral value
            0.5,  # Middle value
            0.001,  # Near-zero
            0.999,  # Near-one
        ],
    )
    def test_edge_case_moral_values(self, edge_value: float):
        """
        Test handling of edge-case moral values.
        """
        moral = MoralFilterV2(initial_threshold=0.5)

        # Should not crash on edge values
        result = moral.evaluate(edge_value)
        assert isinstance(result, bool)

        # Adaptation should work
        moral.adapt(result)
        assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
        assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD

    @pytest.mark.security
    def test_empty_prompt_handling(self):
        """
        Test handling of empty or near-empty prompts.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        # Single character - minimal valid prompt
        result = wrapper.generate(prompt="x", moral_value=0.8)
        assert "accepted" in result

    @pytest.mark.security
    def test_very_long_prompt_handling(self):
        """
        Test handling of very long prompts.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        long_prompt = "Test prompt. " * 500  # ~6500 characters
        result = wrapper.generate(prompt=long_prompt, moral_value=0.8)

        assert "accepted" in result
        assert "response" in result

    @pytest.mark.security
    def test_unicode_prompt_handling(self):
        """
        Test handling of prompts with various Unicode characters.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        unicode_prompts = [
            "日本語テスト",  # Japanese
            "тест кириллицы",  # Cyrillic
            "🧠🔧💻",  # Emojis
            "مرحبا",  # Arabic
            "mixed αβγ characters δε",  # Greek
        ]

        for prompt in unicode_prompts:
            result = wrapper.generate(prompt=prompt, moral_value=0.8)
            assert "accepted" in result

    @pytest.mark.security
    def test_special_character_prompts(self):
        """
        Test handling of prompts with special characters.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        special_prompts = [
            "Test with newlines\n\n\nand tabs\t\t\t",
            "Test with <html> tags </html>",
            "Test with 'quotes' and \"double quotes\"",
            "Test with backslash \\ and forward slash /",
            "Test with pipe | and ampersand &",
        ]

        for prompt in special_prompts:
            result = wrapper.generate(prompt=prompt, moral_value=0.8)
            assert "accepted" in result


# ============================================================================
# Concurrent Stress Tests
# ============================================================================


class TestConcurrentStressResilience:
    """Tests for resilience under concurrent stress."""

    @pytest.mark.security
    @pytest.mark.slow
    def test_concurrent_requests_no_data_corruption(self):
        """
        Test that concurrent requests don't corrupt shared state.
        """
        controller = CognitiveController(dim=384)
        errors: Queue = Queue()
        results: Queue = Queue()

        def worker(worker_id: int, iterations: int) -> None:
            np.random.seed(worker_id)
            for i in range(iterations):
                try:
                    vec = np.random.randn(384).astype(np.float32)
                    vec = vec / np.linalg.norm(vec)
                    moral_value = 0.5 + np.random.random() * 0.4

                    result = controller.process_event(vec, moral_value)

                    # Validate result structure
                    assert "step" in result
                    assert "rejected" in result
                    assert "moral_threshold" in result

                    results.put(result)
                except Exception as e:
                    errors.put((worker_id, i, str(e)))

        # Launch concurrent workers
        num_workers = 8
        iterations_per_worker = 50

        threads = [
            threading.Thread(target=worker, args=(i, iterations_per_worker))
            for i in range(num_workers)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for errors
        assert errors.empty(), f"Errors occurred: {list(errors.queue)}"

        # Verify expected number of results
        assert results.qsize() == num_workers * iterations_per_worker

        # Verify memory integrity
        assert not controller.pelm.detect_corruption()

    @pytest.mark.security
    @pytest.mark.slow
    def test_burst_traffic_handling(self):
        """
        Test handling of burst traffic (many requests at once).
        """
        config = NeuroEngineConfig(
            dim=384,
            capacity=1000,
            enable_fslgs=False,
            enable_metrics=False,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
            config=config,
        )

        num_requests = 100
        results: list = []
        errors: list = []

        def burst_request(idx: int) -> None:
            try:
                result = engine.generate(
                    prompt=f"Burst request {idx}",
                    moral_value=0.8,
                    max_tokens=50,
                )
                results.append(result)
            except Exception as e:
                errors.append((idx, str(e)))

        # Execute all requests in parallel
        with ThreadPoolExecutor(max_workers=20) as executor:
            list(executor.map(burst_request, range(num_requests)))

        # Should handle all requests
        assert len(errors) == 0, f"Errors during burst: {errors}"
        assert len(results) == num_requests

        # All should have valid structure
        for result in results:
            assert "response" in result or "error" in result


# ============================================================================
# Graceful Degradation Tests
# ============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation under failure conditions."""

    @pytest.mark.security
    def test_stateless_mode_fallback(self):
        """
        Test fallback to stateless mode on memory failures.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        # Force stateless mode
        wrapper.stateless_mode = True
        wrapper.qilm_failure_count = 3

        result = wrapper.generate(prompt="Test stateless", moral_value=0.9)

        assert result["accepted"] is True
        assert result["stateless_mode"] is True
        assert "stateless" in result["note"].lower()

    @pytest.mark.security
    def test_circuit_breaker_protection(self):
        """
        Test circuit breaker protects against cascading failures.
        """
        failure_count = [0]

        def always_failing_embedding(text: str) -> np.ndarray:
            failure_count[0] += 1
            raise RuntimeError("Embedding service down")

        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=always_failing_embedding,
        )

        # Trigger multiple failures
        for _ in range(10):
            result = wrapper.generate(prompt="Test", moral_value=0.9)
            assert result["accepted"] is False

        # Circuit breaker should be open
        state = wrapper.get_state()
        assert state["reliability"]["circuit_breaker_state"] == "open"

    @pytest.mark.security
    def test_moral_filter_bounds_never_violated(self):
        """
        Test that moral filter bounds are never violated under stress.
        """
        moral = MoralFilterV2(initial_threshold=0.5)

        # Random extreme inputs
        np.random.seed(42)
        for _ in range(1000):
            # Mix of valid and boundary values
            value = np.random.choice([0.0, 0.1, 0.5, 0.9, 1.0, np.random.random()])
            result = moral.evaluate(value)
            moral.adapt(result)

            # Bounds must hold
            assert moral.threshold >= MoralFilterV2.MIN_THRESHOLD
            assert moral.threshold <= MoralFilterV2.MAX_THRESHOLD


# ============================================================================
# Recovery Tests
# ============================================================================


class TestRecoveryMechanisms:
    """Tests for recovery mechanisms after failures."""

    @pytest.mark.security
    def test_reset_clears_failure_state(self):
        """
        Test that reset clears all failure states.
        """
        wrapper = LLMWrapper(
            llm_generate_fn=create_stub_llm(),
            embedding_fn=create_stub_embedder(),
        )

        # Simulate failure state
        wrapper.stateless_mode = True
        wrapper.qilm_failure_count = 5
        wrapper.embedding_failure_count = 3
        wrapper.llm_failure_count = 2

        # Reset
        wrapper.reset()

        state = wrapper.get_state()
        assert state["reliability"]["stateless_mode"] is False
        assert state["reliability"]["qilm_failure_count"] == 0
        assert state["reliability"]["embedding_failure_count"] == 0
        assert state["reliability"]["llm_failure_count"] == 0

    @pytest.mark.security
    def test_controller_reset_clears_emergency_state(self):
        """
        Test that controller reset clears emergency shutdown state.
        """
        controller = CognitiveController(dim=384)

        # Trigger emergency shutdown
        controller.emergency_shutdown = True
        controller._emergency_reason = "Test emergency"

        # Reset emergency shutdown
        controller.reset_emergency_shutdown()

        assert controller.emergency_shutdown is False
        assert controller._emergency_reason is None

    @pytest.mark.security
    def test_pelm_auto_recovery_works(self):
        """
        Test that PELM auto-recovery mechanism works.
        """
        pelm = PhaseEntangledLatticeMemory(dimension=10, capacity=100)

        # Add data
        for i in range(50):
            vec = [float(i)] * 10
            pelm.entangle(vec, phase=0.5)

        # Corrupt state
        pelm.pointer = 99999

        # Verify corruption detected
        assert pelm.detect_corruption()

        # Recovery should work
        pelm.auto_recover()

        # Should be recovered
        assert not pelm.detect_corruption()
        assert 0 <= pelm.pointer < pelm.capacity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
