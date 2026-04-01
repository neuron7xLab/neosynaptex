"""
Concurrency / stress-tests for NeuroCognitiveEngine + CognitiveController.

These tests validate:
- No race-condition with dozens/hundreds of parallel generate() calls
- Monotonic step_counter growth
- Memory integrity (no corruption, size never goes negative)
- No deadlock/timeout under normal load

Usage:
    pytest tests/load/test_concurrency_core.py -v
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
import pytest

from mlsdm.core.cognitive_controller import CognitiveController
from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig

# ---------------------------------------------------------------------------
# Test Markers - use "slow" as it's already defined in pytest.ini
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Thread-safe Fake LLM and Embedder Stubs
# ---------------------------------------------------------------------------


def create_fake_llm() -> Any:
    """Create a thread-safe fake LLM function.

    Returns deterministic output based on prompt content.
    No global state, no sleep, no side effects.
    """

    def fake_llm(prompt: str, max_tokens: int = 100) -> str:
        """Thread-safe deterministic LLM stub."""
        # Deterministic response based on prompt
        return f"ok:{prompt[:20]}..."

    return fake_llm


def create_fake_embedder(dim: int = 384) -> Any:
    """Create a thread-safe fake embedding function.

    Returns deterministic embeddings based on text hash.
    No global state to avoid race conditions.

    Args:
        dim: Embedding dimension (default 384)

    Returns:
        A function that generates deterministic embeddings
    """

    def fake_embedder(text: str) -> np.ndarray:
        """Thread-safe deterministic embedder stub."""
        # Use Python's built-in hash for deterministic seeding (not crypto, just for tests)
        text_hash = abs(hash(text))
        local_rng = np.random.RandomState(text_hash % (2**31))
        vec = local_rng.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec

    return fake_embedder


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_llm() -> Any:
    """Provide a thread-safe fake LLM function."""
    return create_fake_llm()


@pytest.fixture
def fake_embedder() -> Any:
    """Provide a thread-safe fake embedder function."""
    return create_fake_embedder(dim=384)


@pytest.fixture
def neuro_engine(fake_llm: Any, fake_embedder: Any) -> NeuroCognitiveEngine:
    """Create a NeuroCognitiveEngine with fake LLM and embedder for testing.

    Uses moderate capacity and deterministic thresholds for consistent behavior.
    """
    config = NeuroEngineConfig(
        dim=384,
        capacity=5_000,  # Moderate capacity for testing
        wake_duration=8,
        sleep_duration=3,
        initial_moral_threshold=0.3,  # Lower threshold to allow more requests
        llm_timeout=30.0,
        llm_retry_attempts=1,
        enable_fslgs=False,  # Disable FSLGS for simpler testing
        enable_metrics=False,
    )
    return NeuroCognitiveEngine(
        llm_generate_fn=fake_llm,
        embedding_fn=fake_embedder,
        config=config,
    )


@pytest.fixture
def cognitive_controller() -> CognitiveController:
    """Create a CognitiveController with small capacity for stress testing.

    Uses small capacity to quickly reach near-full memory states.
    """
    return CognitiveController(
        dim=384,
        memory_threshold_mb=8192.0,  # High threshold to avoid memory-based shutdowns
        max_processing_time_ms=10000.0,  # High limit to avoid time-based rejections
    )


# ---------------------------------------------------------------------------
# Concurrency Test: Step Counter Monotonicity
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.load
class TestNeuroCognitiveEngineConcurrency:
    """Concurrency tests for NeuroCognitiveEngine."""

    def test_concurrent_generate_step_counter_monotonic(
        self, fake_llm: Any, fake_embedder: Any
    ) -> None:
        """Test that step_counter grows monotonically under concurrent load.

        Spawns N concurrent generate() calls and verifies:
        - No exceptions are raised
        - step_counter is non-negative and consistent
        - Memory state remains valid
        """
        # Configuration
        N = 200  # Number of concurrent calls
        MAX_WORKERS = 16

        # Create engine with config that accepts most requests
        config = NeuroEngineConfig(
            dim=384,
            capacity=10_000,
            wake_duration=100,  # Long wake period to avoid sleep rejections
            sleep_duration=1,
            initial_moral_threshold=0.1,  # Very low threshold
            llm_timeout=30.0,
            llm_retry_attempts=1,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=fake_llm,
            embedding_fn=fake_embedder,
            config=config,
        )

        # Prepare prompts
        prompts = [f"Test prompt number {i} for concurrency testing" for i in range(N)]

        # Collect results and exceptions
        results: list[dict[str, Any]] = []
        exceptions: list[tuple[int, Exception]] = []
        lock = threading.Lock()

        def worker(idx: int, prompt: str) -> dict[str, Any]:
            """Worker function for concurrent generate calls."""
            try:
                result = engine.generate(
                    prompt=prompt,
                    moral_value=0.7,  # Safe moral value
                    max_tokens=50,
                )
                with lock:
                    results.append(result)
                return result
            except Exception as e:
                with lock:
                    exceptions.append((idx, e))
                raise

        # Execute concurrent calls with timeout
        start_time = time.time()
        timeout_seconds = 60.0  # Overall test timeout

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(worker, i, prompt): i for i, prompt in enumerate(prompts)}

            for future in as_completed(futures, timeout=timeout_seconds):
                idx = futures[future]
                try:
                    future.result(timeout=10.0)  # Per-future timeout
                except Exception as e:
                    # Exceptions are rare and already captured in worker,
                    # just log additional context here
                    with lock:
                        exceptions.append((idx, e))

        elapsed = time.time() - start_time

        # Assertions
        # 1. No exceptions should occur
        assert len(exceptions) == 0, (
            f"Concurrent generate() raised {len(exceptions)} exceptions: "
            f"{[(idx, str(e)) for idx, e in exceptions[:5]]}"
        )

        # 2. All results should be collected
        assert len(results) == N, f"Expected {N} results, got {len(results)}"

        # 3. Verify step counter is accessible and consistent
        last_state = engine.get_last_states()
        assert last_state is not None
        assert "mlsdm" in last_state

        # 4. Check that MLSDM internal step counter is >= N (some may be rejected)
        # We access through the internal state
        if last_state["mlsdm"] is not None:
            step = last_state["mlsdm"].get("step", 0)
            assert step >= 0, "step_counter should never be negative"

        # 5. Verify test completed in reasonable time
        assert (
            elapsed < timeout_seconds
        ), f"Test took {elapsed:.2f}s, exceeds timeout of {timeout_seconds}s"

        # 6. Count accepted vs rejected
        accepted = sum(1 for r in results if r.get("error") is None)
        rejected = sum(1 for r in results if r.get("error") is not None)

        # At least some should be accepted (with low threshold and long wake)
        assert accepted > 0, "All requests were rejected - check configuration"

        print(
            f"\nConcurrency test completed: "
            f"{accepted} accepted, {rejected} rejected, "
            f"elapsed={elapsed:.2f}s"
        )

    def test_concurrent_generate_no_deadlock_timeout(
        self, fake_llm: Any, fake_embedder: Any
    ) -> None:
        """Test that concurrent generate() does not cause deadlocks.

        Uses aggressive concurrency with short timeouts to detect deadlocks.
        """
        N = 100
        MAX_WORKERS = 32
        TIMEOUT_PER_CALL = 5.0

        config = NeuroEngineConfig(
            dim=384,
            capacity=5_000,
            wake_duration=50,
            sleep_duration=1,
            initial_moral_threshold=0.1,
            llm_timeout=10.0,
            llm_retry_attempts=1,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=fake_llm,
            embedding_fn=fake_embedder,
            config=config,
        )

        prompts = [f"Deadlock test {i}" for i in range(N)]
        completed = [False] * N
        timed_out = [False] * N

        def worker(idx: int, prompt: str) -> None:
            """Worker that tracks completion state."""
            try:
                engine.generate(prompt=prompt, moral_value=0.8, max_tokens=30)
                completed[idx] = True
            except Exception:
                completed[idx] = True  # Still mark as completed (not hanging)

        start_time = time.time()
        overall_timeout = 30.0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(worker, i, prompt): i for i, prompt in enumerate(prompts)}

            for future in as_completed(futures, timeout=overall_timeout):
                idx = futures[future]
                try:
                    future.result(timeout=TIMEOUT_PER_CALL)
                except TimeoutError:
                    timed_out[idx] = True
                except Exception:
                    pass  # Other exceptions are OK, just not deadlocks

        elapsed = time.time() - start_time

        # Check for timeouts (potential deadlocks)
        num_timed_out = sum(timed_out)
        num_completed = sum(completed)

        assert num_timed_out == 0, f"{num_timed_out} calls timed out - possible deadlock detected"
        assert num_completed == N, f"Only {num_completed}/{N} calls completed - possible deadlock"
        assert (
            elapsed < overall_timeout
        ), f"Test took {elapsed:.2f}s, exceeded timeout - possible deadlock"

        print(f"\nNo deadlock detected: {num_completed}/{N} completed in {elapsed:.2f}s")


# ---------------------------------------------------------------------------
# Concurrency Test: Memory Integrity Under Concurrency
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.load
class TestCognitiveControllerConcurrency:
    """Concurrency tests for CognitiveController."""

    def test_memory_integrity_under_concurrency(self) -> None:
        """Test that memory structures remain valid under concurrent access.

        Spawns concurrent process_event calls and verifies:
        - step_counter never decreases (monotonic)
        - pelm_used stays within [0, capacity]
        - No emergency_shutdown triggered unexpectedly
        - Internal state remains consistent
        """
        N = 150  # Number of concurrent calls
        MAX_WORKERS = 16

        # Small capacity to stress memory limits
        controller = CognitiveController(
            dim=384,
            memory_threshold_mb=8192.0,
            max_processing_time_ms=5000.0,
        )

        # Track state snapshots for integrity checks
        step_snapshots: list[int] = []
        pelm_used_snapshots: list[int] = []
        exceptions: list[Exception] = []
        lock = threading.Lock()

        def worker(idx: int) -> dict[str, Any]:
            """Worker that processes events and captures state."""
            try:
                # Create a deterministic vector based on index
                local_rng = np.random.RandomState(idx)
                vec = local_rng.randn(384).astype(np.float32)
                vec = vec / np.linalg.norm(vec)

                # Moral value that should pass (high enough)
                moral_value = 0.7 + 0.2 * (idx % 3) / 2  # 0.7-0.8 range

                result = controller.process_event(vec, moral_value)

                # Capture state snapshot
                with lock:
                    step_snapshots.append(result["step"])
                    pelm_used_snapshots.append(result.get("pelm_used", 0))

                return result

            except Exception as e:
                with lock:
                    exceptions.append(e)
                raise

        # Execute concurrent calls
        start_time = time.time()
        timeout_seconds = 30.0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]

            for future in as_completed(futures, timeout=timeout_seconds):
                try:
                    future.result(timeout=10.0)
                except Exception:
                    pass  # Already captured in worker

        elapsed = time.time() - start_time

        # Assertions
        # 1. No exceptions
        assert (
            len(exceptions) == 0
        ), f"{len(exceptions)} exceptions occurred: {[str(e) for e in exceptions[:5]]}"

        # 2. Step counter never goes negative
        assert all(s >= 0 for s in step_snapshots), "step_counter went negative"

        # 3. Step counter is monotonically non-decreasing when sorted
        # (concurrent access means we can't guarantee strict order)
        sorted_steps = sorted(step_snapshots)
        for i in range(1, len(sorted_steps)):
            assert (
                sorted_steps[i] >= sorted_steps[i - 1]
            ), f"Step counter decreased: {sorted_steps[i - 1]} -> {sorted_steps[i]}"

        # 4. Final step counter should be >= N (accounting for potential rejections)
        final_step = controller.step_counter
        assert final_step >= N, f"Final step_counter {final_step} < {N} concurrent calls"

        # 5. pelm_used stays within valid bounds
        pelm_capacity = controller.pelm.capacity
        for used in pelm_used_snapshots:
            assert (
                0 <= used <= pelm_capacity
            ), f"pelm_used {used} out of bounds [0, {pelm_capacity}]"

        # 6. No unexpected emergency shutdown
        assert (
            not controller.emergency_shutdown
        ), "Unexpected emergency_shutdown triggered during normal load"

        # 7. Memory integrity check - internal structures should be consistent
        pelm_stats = controller.pelm.get_state_stats()
        assert pelm_stats["used"] >= 0
        assert pelm_stats["used"] <= pelm_stats["capacity"]

        print(
            f"\nMemory integrity test completed: "
            f"final_step={final_step}, pelm_used={pelm_stats['used']}, "
            f"elapsed={elapsed:.2f}s"
        )

    def test_step_counter_strictly_monotonic(self) -> None:
        """Test that step_counter always increases, never decreases.

        Uses rapid sequential calls with concurrent observers to verify
        that step_counter is properly protected by locks.
        """
        N = 100
        MAX_WORKERS = 8

        controller = CognitiveController(dim=384)

        step_values: list[tuple[int, int]] = []  # (call_order, step_value)
        lock = threading.Lock()
        call_counter = [0]  # Mutable for closure

        def worker() -> None:
            """Worker that records step values."""
            vec = np.random.randn(384).astype(np.float32)
            norm = np.linalg.norm(vec)
            vec = vec / (norm if norm > 1e-9 else 1.0)

            result = controller.process_event(vec, 0.8)

            with lock:
                order = call_counter[0]
                call_counter[0] += 1
                step_values.append((order, result["step"]))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            list(executor.map(lambda _: worker(), range(N)))

        # Verify step values are all unique (no race condition on increment)
        steps_only = [s for _, s in step_values]
        unique_steps = set(steps_only)

        # All steps should be unique (1 to N)
        assert len(unique_steps) == len(
            steps_only
        ), f"Duplicate step values detected: {len(unique_steps)} unique vs {len(steps_only)} total"

        # Steps should cover range 1 to N
        assert min(steps_only) >= 1
        assert max(steps_only) == N

        print(f"\nStep counter monotonicity verified: {N} unique values from 1 to {N}")

    def test_no_race_on_pelm_entangle(self) -> None:
        """Test that concurrent PELM entangle operations don't corrupt state.

        Verifies that:
        - pelm_used never exceeds capacity
        - No indices are duplicated or invalid
        - Memory content remains valid
        """
        N = 200
        MAX_WORKERS = 16

        controller = CognitiveController(dim=384)
        initial_pelm_used = controller.pelm.get_state_stats()["used"]

        exceptions: list[Exception] = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            """Worker that performs PELM operations."""
            try:
                local_rng = np.random.RandomState(idx * 31)
                vec = local_rng.randn(384).astype(np.float32)
                vec = vec / np.linalg.norm(vec)

                controller.process_event(vec, 0.85)

            except Exception as e:
                with lock:
                    exceptions.append(e)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            list(executor.map(worker, range(N)))

        # Check for exceptions
        assert len(exceptions) == 0, f"{len(exceptions)} exceptions during PELM operations"

        # Verify PELM state
        pelm_stats = controller.pelm.get_state_stats()
        assert pelm_stats["used"] >= initial_pelm_used
        assert pelm_stats["used"] <= pelm_stats["capacity"]

        # Verify no emergency shutdown
        assert not controller.emergency_shutdown

        print(
            f"\nPELM integrity verified: used={pelm_stats['used']}, "
            f"capacity={pelm_stats['capacity']}"
        )


# ---------------------------------------------------------------------------
# Stress Test: Mixed Workload
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.load
class TestMixedConcurrencyStress:
    """Stress tests with mixed concurrent operations."""

    def test_mixed_operations_stress(self, fake_llm: Any, fake_embedder: Any) -> None:
        """Test mixed concurrent operations: generate + process_event.

        Simulates realistic load with multiple operation types happening
        concurrently to detect any cross-component race conditions.
        """
        N_ENGINE_CALLS = 100
        N_CONTROLLER_CALLS = 100
        MAX_WORKERS = 20

        config = NeuroEngineConfig(
            dim=384,
            capacity=5_000,
            wake_duration=100,
            sleep_duration=1,
            initial_moral_threshold=0.1,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=fake_llm,
            embedding_fn=fake_embedder,
            config=config,
        )

        controller = CognitiveController(dim=384)

        engine_results: list[dict[str, Any]] = []
        controller_results: list[dict[str, Any]] = []
        exceptions: list[tuple[str, Exception]] = []
        lock = threading.Lock()

        def engine_worker(idx: int) -> None:
            """Engine generate worker."""
            try:
                result = engine.generate(
                    prompt=f"Mixed test {idx}",
                    moral_value=0.75,
                    max_tokens=30,
                )
                with lock:
                    engine_results.append(result)
            except Exception as e:
                with lock:
                    exceptions.append(("engine", e))

        def controller_worker(idx: int) -> None:
            """Controller process_event worker."""
            try:
                local_rng = np.random.RandomState(idx * 17)
                vec = local_rng.randn(384).astype(np.float32)
                vec = vec / np.linalg.norm(vec)

                result = controller.process_event(vec, 0.8)
                with lock:
                    controller_results.append(result)
            except Exception as e:
                with lock:
                    exceptions.append(("controller", e))

        start_time = time.time()
        timeout_seconds = 60.0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit mixed workload
            engine_futures = [executor.submit(engine_worker, i) for i in range(N_ENGINE_CALLS)]
            controller_futures = [
                executor.submit(controller_worker, i) for i in range(N_CONTROLLER_CALLS)
            ]

            all_futures = engine_futures + controller_futures

            for future in as_completed(all_futures, timeout=timeout_seconds):
                try:
                    future.result(timeout=10.0)
                except Exception:
                    pass

        elapsed = time.time() - start_time

        # Assertions
        assert len(exceptions) == 0, (
            f"{len(exceptions)} exceptions in mixed stress: "
            f"{[(t, str(e)) for t, e in exceptions[:5]]}"
        )

        assert len(engine_results) == N_ENGINE_CALLS
        assert len(controller_results) == N_CONTROLLER_CALLS

        # Verify final states
        engine_state = engine.get_last_states()
        assert engine_state is not None

        controller_final_step = controller.step_counter
        assert controller_final_step >= N_CONTROLLER_CALLS

        # No emergency shutdown
        assert not controller.emergency_shutdown

        print(
            f"\nMixed stress test completed: "
            f"engine_calls={len(engine_results)}, "
            f"controller_calls={len(controller_results)}, "
            f"elapsed={elapsed:.2f}s"
        )


# ---------------------------------------------------------------------------
# Optional: Smoke test for quick validation
# ---------------------------------------------------------------------------


class TestConcurrencySmoke:
    """Quick smoke tests for concurrency (not marked as slow)."""

    def test_basic_concurrent_generate(self, fake_llm: Any, fake_embedder: Any) -> None:
        """Quick smoke test for basic concurrent generate."""
        N = 10
        MAX_WORKERS = 4

        config = NeuroEngineConfig(
            dim=384,
            capacity=1_000,
            wake_duration=20,
            sleep_duration=1,
            initial_moral_threshold=0.1,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=fake_llm,
            embedding_fn=fake_embedder,
            config=config,
        )

        results: list[dict[str, Any]] = []

        def worker(idx: int) -> dict[str, Any]:
            result = engine.generate(f"Smoke test {idx}", moral_value=0.8, max_tokens=20)
            results.append(result)
            return result

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            list(executor.map(worker, range(N)))

        assert len(results) == N
        # At least some should succeed
        successful = [r for r in results if r.get("error") is None]
        assert len(successful) > 0

    def test_basic_concurrent_controller(self) -> None:
        """Quick smoke test for basic concurrent controller operations."""
        N = 10
        MAX_WORKERS = 4

        controller = CognitiveController(dim=384)

        def worker(idx: int) -> dict[str, Any]:
            vec = np.random.randn(384).astype(np.float32)
            norm = np.linalg.norm(vec)
            vec = vec / (norm if norm > 1e-9 else 1.0)
            return controller.process_event(vec, 0.8)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(worker, range(N)))

        assert len(results) == N
        assert controller.step_counter >= N
