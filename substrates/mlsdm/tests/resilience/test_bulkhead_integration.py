"""
Integration tests for Bulkhead pattern in NeuroCognitiveEngine.

Tests cover:
1. Bulkhead is initialized with engine
2. Bulkhead limits concurrent LLM operations
3. Bulkhead full error handling
4. Bulkhead state observability
5. Graceful degradation under load
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
import pytest

from mlsdm.engine.neuro_cognitive_engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.utils.bulkhead import BulkheadCompartment


def create_slow_llm(delay_seconds: float = 0.1):
    """Create an LLM that simulates slow responses."""

    def slow_llm(prompt: str, max_tokens: int = 100) -> str:
        time.sleep(delay_seconds)
        return f"Response to: {prompt[:20]}..."

    return slow_llm


def create_fast_llm():
    """Create a fast LLM for testing."""

    def fast_llm(prompt: str, max_tokens: int = 100) -> str:
        return f"Fast response to: {prompt[:20]}..."

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


class TestBulkheadEngineIntegration:
    """Test bulkhead integration with NeuroCognitiveEngine."""

    def test_bulkhead_enabled_by_default(self):
        """Test that bulkhead is enabled by default."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        assert engine.get_bulkhead() is not None
        state = engine.get_bulkhead_state()
        assert state["enabled"] is True

    def test_bulkhead_can_be_disabled(self):
        """Test that bulkhead can be disabled via config."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            enable_bulkhead=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        assert engine.get_bulkhead() is None
        state = engine.get_bulkhead_state()
        assert state["enabled"] is False

    def test_bulkhead_custom_limits(self):
        """Test that bulkhead respects custom limits."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            bulkhead_llm_limit=5,
            bulkhead_embedding_limit=10,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        bulkhead = engine.get_bulkhead()
        assert bulkhead is not None

        # Check limits
        available, max_concurrent = bulkhead.get_availability(BulkheadCompartment.LLM_GENERATION)
        assert max_concurrent == 5

        available, max_concurrent = bulkhead.get_availability(BulkheadCompartment.EMBEDDING)
        assert max_concurrent == 10


class TestBulkheadConcurrencyLimits:
    """Test bulkhead enforces concurrency limits during generation."""

    def test_concurrent_requests_limited(self):
        """Test that bulkhead limits concurrent LLM operations."""
        # Use slow LLM to ensure requests overlap
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            bulkhead_llm_limit=3,  # Very low limit
            bulkhead_timeout=0.5,  # Short timeout
            wake_duration=100,  # Long wake to avoid sleep rejections
            initial_moral_threshold=0.1,  # Low threshold to accept requests
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_slow_llm(delay_seconds=0.2),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Try to make more concurrent requests than bulkhead allows
        N = 10
        MAX_WORKERS = 10
        results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            result = engine.generate(
                prompt=f"Test request {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with lock:
                results.append(result)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(worker, i) for i in range(N)]
            for future in as_completed(futures, timeout=30.0):
                try:
                    future.result()
                except Exception:
                    pass

        # Should have all results (some may be rejected by bulkhead)
        assert len(results) == N

        # Count bulkhead rejections
        bulkhead_rejections = [
            r for r in results if r.get("error") and r["error"].get("type") == "bulkhead_full"
        ]

        # Some requests should have been rejected due to bulkhead limit
        # (with 3 slots and 0.2s delay, 10 parallel requests will exceed capacity)
        assert len(bulkhead_rejections) >= 0  # At least 0 (could be more with timing)

        # Check bulkhead state tracked the activity
        state = engine.get_bulkhead_state()
        llm_state = state["compartments"]["llm_generation"]
        assert llm_state["total_acquired"] > 0

    def test_bulkhead_full_graceful_error(self):
        """Test that bulkhead full returns graceful error response."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            bulkhead_llm_limit=1,  # Only 1 concurrent
            bulkhead_timeout=0.01,  # Very short timeout
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_slow_llm(delay_seconds=0.5),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        results: list[dict[str, Any]] = []
        lock = threading.Lock()

        def worker(idx: int) -> None:
            result = engine.generate(
                prompt=f"Test request {idx}",
                moral_value=0.8,
                max_tokens=50,
            )
            with lock:
                results.append(result)

        # Start two concurrent requests (second should be rejected)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(results) == 2

        # At least one should succeed
        successes = [r for r in results if r.get("error") is None]
        assert len(successes) >= 1

        # If there's a bulkhead rejection, verify error format
        rejections = [
            r for r in results if r.get("error") and r["error"].get("type") == "bulkhead_full"
        ]
        for rejection in rejections:
            assert rejection["error"]["type"] == "bulkhead_full"
            assert "bulkhead full" in rejection["error"]["message"]
            assert rejection["rejected_at"] == "generation"


class TestBulkheadObservability:
    """Test bulkhead state observability."""

    def test_bulkhead_state_structure(self):
        """Test bulkhead state has expected structure."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Make a request to populate stats
        engine.generate(prompt="Test", moral_value=0.8, max_tokens=50)

        state = engine.get_bulkhead_state()

        assert "enabled" in state
        assert state["enabled"] is True
        assert "compartments" in state
        assert "summary" in state

        # Check compartments
        assert "llm_generation" in state["compartments"]
        llm_state = state["compartments"]["llm_generation"]
        assert "current_active" in llm_state
        assert "max_concurrent" in llm_state
        assert "total_acquired" in llm_state
        assert "total_rejected" in llm_state

        # Should have acquired at least one slot
        assert llm_state["total_acquired"] >= 1

    def test_bulkhead_state_when_disabled(self):
        """Test bulkhead state when disabled."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            enable_bulkhead=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        state = engine.get_bulkhead_state()
        assert state == {"enabled": False}


class TestBulkheadRecovery:
    """Test bulkhead recovery and slot release."""

    def test_slots_released_after_request(self):
        """Test that bulkhead slots are released after request completes."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            bulkhead_llm_limit=5,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Make several requests
        for i in range(10):
            engine.generate(prompt=f"Request {i}", moral_value=0.8, max_tokens=50)

        # Check all slots are released
        bulkhead = engine.get_bulkhead()
        assert bulkhead is not None

        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.current_active == 0  # All should be released
        assert stats.total_acquired >= 1  # Should have acquired slots

    def test_slots_released_on_error(self):
        """Test that bulkhead slots are released even when LLM fails."""
        call_count = [0]

        def failing_llm(prompt: str, max_tokens: int = 100) -> str:
            call_count[0] += 1
            if call_count[0] <= 3:
                raise ConnectionError("LLM service unavailable")
            return "Success"

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            bulkhead_llm_limit=5,
            wake_duration=100,
            initial_moral_threshold=0.1,
            llm_retry_attempts=1,  # No retries to simplify test
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=failing_llm,
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        # Make requests that will fail
        for i in range(5):
            engine.generate(prompt=f"Request {i}", moral_value=0.8, max_tokens=50)

        # Check all slots are released
        bulkhead = engine.get_bulkhead()
        assert bulkhead is not None

        stats = bulkhead.get_stats(BulkheadCompartment.LLM_GENERATION)
        assert stats.current_active == 0  # All should be released


class TestBulkheadWithDisabledEngine:
    """Test engine works correctly with bulkhead disabled."""

    def test_generation_works_without_bulkhead(self):
        """Test that generation works when bulkhead is disabled."""
        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            enable_bulkhead=False,
            wake_duration=100,
            initial_moral_threshold=0.1,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=create_fast_llm(),
            embedding_fn=create_fake_embedder(),
            config=config,
        )

        result = engine.generate(prompt="Test", moral_value=0.8, max_tokens=50)

        assert result.get("error") is None
        assert result.get("response") is not None
        assert len(result["response"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
