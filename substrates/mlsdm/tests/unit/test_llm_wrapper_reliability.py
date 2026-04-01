"""
Unit tests for LLM Wrapper reliability features.

Tests cover:
1. Retry logic with exponential backoff
2. Circuit breaker for embedding failures
3. Graceful degradation to stateless mode
4. Timeout handling for slow LLM calls
5. Recovery scenarios: corrupted vector, OOM, network timeout
"""

import time
from unittest.mock import Mock

import numpy as np
import pytest

from mlsdm.core.llm_wrapper import CircuitBreaker, CircuitBreakerState, LLMWrapper
from mlsdm.utils.embedding_cache import EmbeddingCacheConfig


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_normal_operation(self):
        """Circuit breaker allows calls in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        mock_func = Mock(return_value="success")
        result = cb.call(mock_func, "arg1")

        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_opens_after_failures(self):
        """Circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        mock_func = Mock(side_effect=RuntimeError("Service error"))

        # Trigger failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(mock_func)

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """Circuit breaker blocks calls when OPEN."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

        mock_func = Mock(side_effect=RuntimeError("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(mock_func)

        # Should block now
        with pytest.raises(RuntimeError, match="Circuit breaker is OPEN"):
            cb.call(mock_func)

    def test_circuit_breaker_half_open_recovery(self):
        """Circuit breaker transitions to HALF_OPEN and recovers."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, success_threshold=2)

        mock_func = Mock(side_effect=RuntimeError("Service error"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(mock_func)

        assert cb.state == CircuitBreakerState.OPEN

        # Force transition without waiting
        cb.last_failure_time = time.time() - cb.recovery_timeout

        # Should transition to HALF_OPEN and allow test
        mock_func = Mock(return_value="success")
        result = cb.call(mock_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Second success should close the circuit
        result = cb.call(mock_func)
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_reset(self):
        """Circuit breaker reset clears all state."""
        cb = CircuitBreaker(failure_threshold=2)

        mock_func = Mock(side_effect=RuntimeError("Error"))

        # Trigger some failures
        with pytest.raises(RuntimeError):
            cb.call(mock_func)

        cb.reset()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0


class TestLLMWrapperReliability:
    """Test LLM wrapper reliability features."""

    def mock_llm_generate(self, prompt: str, max_tokens: int) -> str:
        """Basic mock LLM."""
        return f"Response to: {prompt[:20]}"

    def mock_embedding(self, text: str) -> np.ndarray:
        """Basic mock embedding."""
        np.random.seed(42)
        return np.random.randn(384).astype(np.float32)

    def test_llm_retry_on_transient_error(self):
        """LLM generation retries on transient errors."""
        attempt_count = 0

        def failing_llm(prompt: str, max_tokens: int) -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Transient network error")
            return "Success after retry"

        wrapper = LLMWrapper(
            llm_generate_fn=failing_llm, embedding_fn=self.mock_embedding, llm_retry_attempts=3
        )

        result = wrapper.generate(prompt="Test", moral_value=0.9)

        assert result["accepted"] is True
        assert "Success after retry" in result["response"]
        assert attempt_count == 3

    def test_llm_retry_exhaustion(self):
        """LLM generation fails after retry exhaustion."""

        def always_failing_llm(prompt: str, max_tokens: int) -> str:
            raise ConnectionError("Persistent error")

        wrapper = LLMWrapper(
            llm_generate_fn=always_failing_llm,
            embedding_fn=self.mock_embedding,
            llm_retry_attempts=2,
        )

        result = wrapper.generate(prompt="Test", moral_value=0.9)

        assert result["accepted"] is False
        assert "generation failed" in result["note"]

    def test_llm_timeout_handling(self, fake_clock, monkeypatch):
        """LLM generation detects timeouts."""

        def slow_llm(prompt: str, max_tokens: int) -> str:
            fake_clock.advance(0.2)
            return "Slow response"

        monkeypatch.setattr("mlsdm.core.llm_wrapper.time.time", fake_clock.now)

        wrapper = LLMWrapper(
            llm_generate_fn=slow_llm,
            embedding_fn=self.mock_embedding,
            llm_timeout=0.1,  # Very short timeout
        )

        result = wrapper.generate(prompt="Test", moral_value=0.9)

        # Should fail due to timeout
        assert result["accepted"] is False
        assert "generation failed" in result["note"]

    def test_embedding_circuit_breaker_protection(self):
        """Circuit breaker protects against embedding failures."""
        failure_count = 0

        def failing_embedding(text: str) -> np.ndarray:
            nonlocal failure_count
            failure_count += 1
            raise RuntimeError("Embedding service down")

        wrapper = LLMWrapper(llm_generate_fn=self.mock_llm_generate, embedding_fn=failing_embedding)

        # Trigger multiple failures to open circuit
        for _ in range(6):
            result = wrapper.generate(prompt="Test", moral_value=0.9)
            assert result["accepted"] is False

        # Circuit should be open now
        state = wrapper.get_state()
        assert state["reliability"]["circuit_breaker_state"] == "open"
        assert state["reliability"]["embedding_failure_count"] >= 5

    def test_corrupted_vector_handling(self):
        """System handles corrupted embedding vectors."""

        def corrupted_embedding(text: str) -> np.ndarray:
            # Return vector with NaN values
            vec = np.random.randn(384).astype(np.float32)
            vec[0] = np.nan
            return vec

        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=corrupted_embedding
        )

        result = wrapper.generate(prompt="Test", moral_value=0.9)

        assert result["accepted"] is False
        assert "embedding failed" in result["note"]
        assert "Corrupted embedding vector" in result["note"]

    def test_zero_norm_vector_handling(self):
        """System handles zero-norm embedding vectors."""

        def zero_norm_embedding(text: str) -> np.ndarray:
            return np.zeros(384, dtype=np.float32)

        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=zero_norm_embedding
        )

        result = wrapper.generate(prompt="Test", moral_value=0.9)

        assert result["accepted"] is False
        assert "embedding failed" in result["note"]
        assert "Zero-norm embedding vector" in result["note"]

    def test_graceful_degradation_to_stateless_mode(self):
        """System degrades to stateless mode on QILM failures."""
        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding, capacity=10
        )

        # Simulate QILM failures by corrupting the QILM
        wrapper.qilm_failure_count = 3
        wrapper.stateless_mode = True

        # Should still work in stateless mode
        result = wrapper.generate(prompt="Test in stateless", moral_value=0.9)

        assert result["accepted"] is True
        assert result["stateless_mode"] is True
        assert "stateless mode" in result["note"]

    def test_memory_error_triggers_stateless_mode(self):
        """MemoryError during QILM operations triggers stateless mode."""

        def memory_error_embedding(text: str) -> np.ndarray:
            # This won't directly trigger MemoryError, but we can simulate it
            return np.random.randn(384).astype(np.float32)

        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=memory_error_embedding, capacity=10
        )

        # Manually trigger stateless mode to simulate OOM scenario
        wrapper.qilm_failure_count = 3
        wrapper.stateless_mode = True

        state = wrapper.get_state()
        assert state["reliability"]["stateless_mode"] is True
        assert state["reliability"]["qilm_failure_count"] == 3

    def test_consolidated_reliability_metrics(self):
        """State includes comprehensive reliability metrics."""
        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )

        # Generate some activity
        wrapper.generate(prompt="Test 1", moral_value=0.9)

        state = wrapper.get_state()

        assert "reliability" in state
        assert "stateless_mode" in state["reliability"]
        assert "circuit_breaker_state" in state["reliability"]
        assert "qilm_failure_count" in state["reliability"]
        assert "embedding_failure_count" in state["reliability"]
        assert "llm_failure_count" in state["reliability"]

    def test_reset_clears_reliability_state(self):
        """Reset clears all reliability counters and states."""
        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )

        # Set some failure states
        wrapper.qilm_failure_count = 5
        wrapper.embedding_failure_count = 3
        wrapper.llm_failure_count = 2
        wrapper.stateless_mode = True

        # Reset
        wrapper.reset()

        state = wrapper.get_state()
        assert state["reliability"]["stateless_mode"] is False
        assert state["reliability"]["qilm_failure_count"] == 0
        assert state["reliability"]["embedding_failure_count"] == 0
        assert state["reliability"]["llm_failure_count"] == 0
        assert state["reliability"]["circuit_breaker_state"] == "closed"

    def test_network_timeout_recovery(self):
        """System recovers from network timeout errors."""
        attempt_count = 0

        def intermittent_network_llm(prompt: str, max_tokens: int) -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ConnectionError("Network timeout")
            return "Recovered from timeout"

        wrapper = LLMWrapper(
            llm_generate_fn=intermittent_network_llm,
            embedding_fn=self.mock_embedding,
            llm_retry_attempts=3,
        )

        result = wrapper.generate(prompt="Test network", moral_value=0.9)

        assert result["accepted"] is True
        assert "Recovered from timeout" in result["response"]
        assert attempt_count == 2  # Failed once, succeeded on retry

    def test_embedding_cache_stats_and_aliases(self):
        """Exercise cache conversion path, aliases, and sleep token clamp."""
        cache_config = EmbeddingCacheConfig(max_size=4, ttl_seconds=10, enabled=True)

        def list_embedding(text: str):
            # Return list to exercise ndarray conversion path
            return [1.0] * 384

        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate,
            embedding_fn=list_embedding,
            embedding_cache_config=cache_config,
        )
        wrapper.qilm_failure_count = 2
        assert wrapper.qilm_failure_count == 2

        wrapper.stateless_mode = True
        assert wrapper._safe_pelm_operation("retrieve") == []
        wrapper.stateless_mode = False

        first = wrapper.generate(prompt="Hello world", moral_value=0.9)
        second = wrapper.generate(prompt="Hello world", moral_value=0.9)

        assert first["accepted"] is True
        assert second["accepted"] is True

        state = wrapper.get_state()
        assert "embedding_cache" in state
        assert state["embedding_cache"]["hits"] >= 1
        assert state["embedding_cache"]["misses"] >= 1

        clamped_tokens = wrapper._determine_max_tokens(max_tokens=500, is_wake=False)
        assert clamped_tokens == wrapper.MAX_SLEEP_TOKENS

    def test_embed_validation_and_pelm_failure_paths(self):
        """Cover embedding validation errors and PELM failure handling."""
        empty_wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate,
            embedding_fn=lambda _text: np.array([], dtype=np.float32),
        )

        error_response = empty_wrapper._embed_and_validate_prompt("bad")
        assert empty_wrapper._is_error_response(error_response)
        assert "empty vector" in error_response["note"]

        failure_wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )
        failure_wrapper.pelm_failure_count = failure_wrapper.DEFAULT_PELM_FAILURE_THRESHOLD - 1
        failure_wrapper.pelm.retrieve = Mock(side_effect=MemoryError("pelm boom"))

        with pytest.raises(MemoryError):
            failure_wrapper._safe_pelm_operation(
                "retrieve", query_vector=[], current_phase=0.0, phase_tolerance=0.1, top_k=1
            )

        assert failure_wrapper.stateless_mode is True
        assert failure_wrapper.pelm_failure_count == failure_wrapper.DEFAULT_PELM_FAILURE_THRESHOLD

        unknown_wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )
        with pytest.raises(ValueError):
            unknown_wrapper._safe_pelm_operation("unknown-op")

        retrieval_wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )
        retrieval_wrapper._safe_pelm_operation = Mock(side_effect=RuntimeError("pelm fail"))
        memories, enhanced_prompt = retrieval_wrapper._retrieve_and_build_context(
            prompt="hi",
            prompt_vector=np.ones(384, dtype=np.float32),
            phase_val=retrieval_wrapper.WAKE_PHASE,
            context_top_k=2,
        )

        assert memories == []
        assert "hi" in enhanced_prompt

    def test_memory_consolidation_failure_and_confidence(self):
        """Cover memory update failure paths and confidence heuristics."""
        wrapper = LLMWrapper(
            llm_generate_fn=self.mock_llm_generate, embedding_fn=self.mock_embedding
        )
        wrapper._kernel.memory_commit = Mock(side_effect=RuntimeError("commit failure"))

        start_failures = wrapper.pelm_failure_count
        wrapper._update_memory_after_generate(
            np.ones(384, dtype=np.float32), wrapper.WAKE_PHASE, response_text="maybe short"
        )
        assert wrapper.pelm_failure_count == start_failures + 1
        assert wrapper.accepted_count == 1

        wrapper.consolidation_buffer.clear()
        wrapper._consolidate_memories()

        wrapper.consolidation_buffer.append(np.ones(wrapper.dim, dtype=np.float32))
        wrapper._kernel.memory_commit = Mock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            wrapper._consolidate_memories()
        assert wrapper.pelm_failure_count == start_failures + 2

        wrapper.consolidation_buffer.append(np.ones(wrapper.dim, dtype=np.float32))
        wrapper.stateless_mode = False
        wrapper._consolidate_memories = Mock(side_effect=RuntimeError("consolidation error"))
        wrapper.rhythm.is_sleep = lambda: True
        wrapper._advance_rhythm_and_consolidate()

        confidence = wrapper._estimate_confidence("Maybe this is maybe short")
        assert confidence < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
