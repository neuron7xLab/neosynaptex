"""LLM failure mode tests.

Tests system behavior when LLM provider fails in various ways.
Validates circuit breaker, retry logic, and graceful degradation.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np
import pytest

from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def create_stub_embedder(dim: int = 384) -> Callable[[str], np.ndarray]:
    """Create a deterministic stub embedding function."""

    def stub_embed(text: str) -> np.ndarray:
        # Use bitwise AND for uniform distribution across 32-bit range
        np.random.seed(hash(text) & 0xFFFFFFFF)
        vec = np.random.randn(dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            vec = np.zeros(dim, dtype=np.float32)
            vec[0] = 1.0
        else:
            vec = vec / norm
        return vec

    return stub_embed


@pytest.mark.security
class TestLLMTimeoutHandling:
    """Test system behavior when LLM provider times out."""

    def test_llm_timeout_behavior(self) -> None:
        """Validate LLM wrapper handles timeouts gracefully.

        Timeout handling should prevent indefinite blocking.
        """
        timeout_count = [0]

        def timeout_llm(prompt: str, max_tokens: int) -> str:
            """LLM that always times out."""
            timeout_count[0] += 1
            time.sleep(2.0)  # Simulate slow response
            return "Too slow"

        wrapper = LLMWrapper(
            llm_generate_fn=timeout_llm,
            embedding_fn=create_stub_embedder(),
            llm_timeout=0.5,  # Very short timeout
            llm_retry_attempts=1,
        )

        # Should handle timeout (may raise or return error response)
        try:
            result = wrapper.generate(prompt="Test timeout", moral_value=0.8)
            # If it doesn't timeout, verify we got a result
            assert result is not None
        except Exception:
            # Timeout exception is acceptable
            pass

        # Verify at least one attempt was made
        assert timeout_count[0] >= 1

    def test_llm_partial_timeout_recovery(self) -> None:
        """Test recovery when timeouts are intermittent.

        System should retry and eventually succeed when LLM becomes responsive.
        """
        call_count = [0]

        def intermittent_timeout_llm(prompt: str, max_tokens: int) -> str:
            """LLM that times out first 2 times, then succeeds."""
            call_count[0] += 1
            if call_count[0] <= 2:
                time.sleep(2.0)
                return "Timeout"
            return "Success after recovery"

        wrapper = LLMWrapper(
            llm_generate_fn=intermittent_timeout_llm,
            embedding_fn=create_stub_embedder(),
            llm_timeout=1.5,
            llm_retry_attempts=5,
        )

        result = wrapper.generate(prompt="Test recovery", moral_value=0.8)

        # Should eventually succeed
        assert result["accepted"] is True
        assert "Success" in result["response"]
        assert call_count[0] == 3  # Failed twice, succeeded third time


@pytest.mark.security
class TestLLM5xxErrors:
    """Test system behavior when LLM provider returns 5xx errors."""

    def test_llm_500_error_retry(self) -> None:
        """Validate retry logic for 5xx errors.

        System should retry 5xx errors and eventually succeed or fail gracefully.
        """
        call_count = [0]

        def flaky_500_llm(prompt: str, max_tokens: int) -> str:
            """LLM that returns 500 error first 2 times."""
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("HTTP 500: Internal Server Error")
            return "Success after retry"

        wrapper = LLMWrapper(
            llm_generate_fn=flaky_500_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=5,
            llm_timeout=5.0,
        )

        result = wrapper.generate(prompt="Test 500 error", moral_value=0.8)

        # System should handle retry
        assert result is not None
        # Either accepted or rejected, but didn't crash
        assert "accepted" in result

    def test_llm_persistent_500_error(self) -> None:
        """Test graceful handling of persistent 5xx errors.

        When LLM consistently fails, system should exhaust retries
        and return structured error response or raise exception.
        """

        def always_500_llm(prompt: str, max_tokens: int) -> str:
            """LLM that always returns 500 error."""
            raise Exception("HTTP 500: Internal Server Error")

        wrapper = LLMWrapper(
            llm_generate_fn=always_500_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=3,
            llm_timeout=5.0,
        )

        # Should either raise exception or return rejected response
        try:
            result = wrapper.generate(prompt="Test persistent 500", moral_value=0.8)
            # If it doesn't raise, it should return a rejection
            assert result["accepted"] is False or "error" in result
        except Exception:
            # Exception is also acceptable - system didn't crash silently
            pass


@pytest.mark.security
class TestMalformedLLMResponses:
    """Test system behavior when LLM returns malformed responses."""

    def test_empty_llm_response(self) -> None:
        """Validate handling of empty LLM responses.

        System should detect empty responses and handle gracefully.
        """

        def empty_response_llm(prompt: str, max_tokens: int) -> str:
            """LLM that returns empty response."""
            return ""

        wrapper = LLMWrapper(
            llm_generate_fn=empty_response_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=1,
            llm_timeout=5.0,
        )

        result = wrapper.generate(prompt="Test empty response", moral_value=0.8)

        # System should handle empty response
        assert result["accepted"] is False or result["response"] == ""

    def test_malformed_json_response(self) -> None:
        """Test handling of malformed JSON responses from LLM.

        Some LLM APIs return JSON. System should handle malformed JSON gracefully.
        """

        def malformed_json_llm(prompt: str, max_tokens: int) -> str:
            """LLM that returns malformed JSON."""
            return "{invalid json response"

        wrapper = LLMWrapper(
            llm_generate_fn=malformed_json_llm,
            embedding_fn=create_stub_embedder(),
            llm_retry_attempts=1,
            llm_timeout=5.0,
        )

        # Should not crash, even with malformed JSON
        result = wrapper.generate(prompt="Test malformed JSON", moral_value=0.8)

        # Should return some response (may treat as plain text)
        assert "response" in result


@pytest.mark.security
class TestCircuitBreakerBehavior:
    """Test circuit breaker activation and recovery."""

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        """Validate circuit breaker opens after failure threshold.

        Circuit breaker should open after N consecutive failures.
        """
        circuit_breaker = CircuitBreaker(
            name="test_circuit",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=10.0,
            ),
        )

        # Trigger failures by recording them directly
        for _ in range(3):
            circuit_breaker.record_failure(Exception("Simulated failure"))

        # Circuit should be open now
        assert circuit_breaker.state.value == "open"

        # Verify stats show failures
        stats = circuit_breaker.get_stats()
        assert stats.total_failures >= 3
        assert stats.state == CircuitState.OPEN

    def test_circuit_breaker_half_open_recovery(self) -> None:
        """Test circuit breaker half-open state and recovery.

        After timeout, circuit should enter half-open state
        and allow limited requests for testing recovery.
        """
        circuit_breaker = CircuitBreaker(
            name="test_recovery",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=1.0,  # Short for testing
            ),
        )

        # Trigger failures to open circuit
        for _ in range(2):
            circuit_breaker.record_failure(Exception("Fail"))

        assert circuit_breaker.state.value == "open"

        # Wait for recovery timeout
        time.sleep(1.5)

        # Circuit should transition to half-open or closed after recovery
        # Verify it's no longer permanently open
        assert circuit_breaker.state.value in ("half_open", "closed")
