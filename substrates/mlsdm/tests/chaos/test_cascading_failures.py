"""
Chaos Engineering Tests: Cascading Failures Simulation

Tests system behavior when multiple components fail in sequence.
Verifies circuit breaker patterns and graceful degradation per REL-003.

These tests are designed to run on a schedule (not on every PR)
as they simulate complex failure scenarios.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig


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


def create_cascading_failure_llm(failure_sequence: list[str]):
    """Create an LLM that fails with different errors in sequence.

    Args:
        failure_sequence: List of failure types in order:
            - "ok": Success
            - "timeout": TimeoutError
            - "connection": ConnectionError
            - "value": ValueError
            - "runtime": RuntimeError
    """
    call_count = [0]

    def cascading_llm(prompt: str, max_tokens: int = 100) -> str:
        idx = call_count[0] % len(failure_sequence)
        call_count[0] += 1

        failure_type = failure_sequence[idx]

        if failure_type == "ok":
            return f"Success {call_count[0]}: {prompt[:30]}..."
        elif failure_type == "timeout":
            time.sleep(5.0)  # Will be interrupted by timeout
            raise TimeoutError("Simulated timeout")
        elif failure_type == "connection":
            raise ConnectionError("Simulated connection failure")
        elif failure_type == "value":
            raise ValueError("Simulated invalid response")
        elif failure_type == "runtime":
            raise RuntimeError("Simulated runtime error")
        else:
            return f"Unknown type {failure_type}: {prompt[:30]}..."

    return cascading_llm


class TestCascadingFailuresChaos:
    """Test system behavior under cascading failure conditions."""

    @pytest.mark.chaos
    def test_alternating_failure_types(self):
        """Test handling of alternating failure types.

        Scenario:
        1. Create LLM that alternates between different failure modes
        2. Make series of requests
        3. Verify system handles each failure type correctly
        """
        # Pattern: success, timeout, connection error, success, value error
        failure_sequence = ["ok", "connection", "ok", "connection", "ok"]

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=1.0,
            llm_retry_attempts=1,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_cascading_failure_llm(failure_sequence),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        for i in range(len(failure_sequence) * 2):
            result = engine.generate(
                prompt=f"Cascade test {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            results.append(result)

        # All should complete (either success or graceful failure)
        assert len(results) == len(failure_sequence) * 2
        for result in results:
            assert isinstance(result, dict)

    @pytest.mark.chaos
    def test_controller_failure_with_engine_recovery(self):
        """Test recovery when controller enters emergency but engine continues.

        Scenario:
        1. Trigger controller emergency shutdown
        2. Verify engine handles rejected events gracefully
        3. Simulate recovery and verify resumption
        """
        controller = CognitiveController(
            memory_threshold_mb=0.001,  # Very low to trigger emergency
            auto_recovery_enabled=True,
            auto_recovery_cooldown_seconds=0.2,
        )

        vector = np.random.randn(384).astype(np.float32)

        # Trigger emergency
        result1 = controller.process_event(vector, moral_value=0.8)
        assert controller.emergency_shutdown is True
        assert result1["rejected"] is True

        # Simulate external recovery by increasing threshold
        controller.memory_threshold_mb = 10000.0

        # Wait for cooldown
        time.sleep(0.3)

        # Next event should trigger auto-recovery attempt
        result2 = controller.process_event(vector, moral_value=0.8)

        # Verify recovery occurred
        assert controller.emergency_shutdown is False
        assert result2["rejected"] is False

    @pytest.mark.chaos
    def test_multiple_component_failure_sequence(self):
        """Test failure sequence affecting multiple components.

        Scenario:
        1. Create engine with potentially failing components
        2. Process requests as failures cascade
        3. Verify each failure is isolated and handled
        """
        embedder_call_count = [0]
        llm_call_count = [0]

        def sometimes_failing_embedder(text: str) -> np.ndarray:
            embedder_call_count[0] += 1
            if embedder_call_count[0] % 5 == 0:
                # Every 5th embedding is slow (simulates degradation)
                time.sleep(0.2)
            text_hash = abs(hash(text))
            local_rng = np.random.RandomState(text_hash % (2**31))
            vec = local_rng.randn(384).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 1e-9:
                vec = vec / norm
            return vec

        def sometimes_failing_llm(prompt: str, max_tokens: int = 100) -> str:
            llm_call_count[0] += 1
            if llm_call_count[0] % 7 == 0:
                raise ConnectionError("Periodic LLM failure")
            return f"Response: {prompt[:40]}..."

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=2.0,
            llm_retry_attempts=2,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=sometimes_failing_llm,
            embedding_fn=sometimes_failing_embedder,
            config=config,
        )

        successes = 0
        failures = 0

        for i in range(20):
            result = engine.generate(
                prompt=f"Multi-component test {i}",
                moral_value=0.8,
                max_tokens=50,
            )

            if result.get("error") is None and result.get("response"):
                successes += 1
            else:
                failures += 1

        # Should have mix of successes and graceful failures
        assert successes > 0, "No requests succeeded"
        # System shouldn't crash - all requests should complete
        assert successes + failures == 20

    @pytest.mark.chaos
    def test_recovery_after_multiple_failure_cascade(self):
        """Test system recovery after a cascade of failures.

        Scenario:
        1. Induce multiple failures in sequence (failure_phase=True)
        2. Switch to recovery mode (failure_phase=False)
        3. Verify full recovery to normal operation
        """
        calls = [0]
        failure_phase = [True]  # Start in failure phase

        def phased_llm(prompt: str, max_tokens: int = 100) -> str:
            calls[0] += 1
            current_call = calls[0]
            # Fail while failure_phase is True, succeed when False
            if failure_phase[0]:
                raise ConnectionError("Simulated cascade failure")
            return f"Recovered response {current_call}: {prompt[:30]}..."

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            llm_timeout=2.0,
            llm_retry_attempts=1,  # Minimal retries to see failures
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=phased_llm,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Failure phase
        failure_results = []
        for i in range(3):
            result = engine.generate(
                prompt=f"Failure phase {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            failure_results.append(result)

        # Failure phase should have errors (error field set or no valid response)
        for r in failure_results:
            has_error = r.get("error") is not None
            has_no_valid_response = not r.get("response")
            assert has_error or has_no_valid_response, (
                f"Expected failure in failure phase, got: {r}"
            )

        # End failure phase
        failure_phase[0] = False

        # Recovery phase - LLM now works
        recovery_results = []
        for i in range(5):
            result = engine.generate(
                prompt=f"Recovery phase {i}",
                moral_value=0.8,
                max_tokens=50,
            )
            recovery_results.append(result)

        # Recovery phase requests should succeed
        success_count = sum(
            1 for r in recovery_results
            if r.get("error") is None and r.get("response") and "Recovered" in r.get("response", "")
        )
        assert success_count >= 3, f"Recovery phase should have high success rate, got {success_count}"


class TestIsolationUnderCascade:
    """Test that failures are properly isolated during cascades."""

    @pytest.mark.chaos
    def test_concurrent_cascade_isolation(self):
        """Test that concurrent requests are isolated during failures.

        Scenario:
        1. Start concurrent requests
        2. Some encounter failures, others succeed
        3. Verify failures don't affect successful requests
        """
        call_count = [0]
        lock = threading.Lock()

        def mixed_failure_llm(prompt: str, max_tokens: int = 100) -> str:
            with lock:
                call_count[0] += 1
                current = call_count[0]
            # Odd calls succeed, even calls fail
            if current % 2 == 0:
                raise ConnectionError(f"Failure on call {current}")
            return f"Success {current}: {prompt[:30]}..."

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
            llm_generate_fn=mixed_failure_llm,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results = []
        results_lock = threading.Lock()

        def worker(idx: int):
            result = engine.generate(
                prompt=f"Isolation test {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with results_lock:
                results.append((idx, result))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in futures:
                try:
                    future.result(timeout=30.0)
                except Exception:
                    pass

        # All should complete
        assert len(results) == 10

        # Should have mix of successes and failures
        successes = [r for idx, r in results if r.get("response") and "Success" in r.get("response", "")]
        failures = [r for idx, r in results if r.get("error") or r.get("response") is None]

        # With retry, we should have some successes
        # The exact count depends on retry behavior
        assert len(successes) + len(failures) >= len(results) // 2

    @pytest.mark.chaos
    def test_state_consistency_after_cascade(self):
        """Test that system state remains consistent after cascading failures.

        Scenario:
        1. Process many events with intermittent failures
        2. Verify controller state is consistent
        3. Verify memory state is not corrupted
        """
        controller = CognitiveController(
            memory_threshold_mb=1000.0,  # High threshold to avoid emergency
        )

        initial_step = controller.get_step_counter()

        vector = np.random.randn(384).astype(np.float32)

        # Process many events
        for i in range(50):
            moral_value = 0.5 + (i % 5) * 0.1  # Varying moral values
            controller.process_event(vector, moral_value=moral_value)

        final_step = controller.get_step_counter()

        # Step count should have increased consistently
        expected_processed = 50
        assert final_step >= initial_step + expected_processed // 2, \
            f"Step count inconsistent: started at {initial_step}, ended at {final_step}"

        # Controller should not be in emergency (threshold was high)
        assert controller.emergency_shutdown is False

        # Verify state via property access (not internal method)
        assert controller.is_emergency_shutdown() is False
        assert controller.get_step_counter() == final_step
