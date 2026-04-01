"""
Unit tests for NeuroCognitiveEngine.

Tests cover:
1. Basic initialization with default config
2. Custom configuration
3. Generate method without FSLGS (fallback mode)
4. Mock FSLGS integration
5. get_last_states method
6. Error handling scenarios
7. Metrics integration
8. Router integration
9. Moral check paths
10. Exception handling
11. Circuit breaker integration
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from mlsdm.engine import NeuroCognitiveEngine, NeuroEngineConfig
from mlsdm.utils.circuit_breaker import CircuitState


class TestNeuroEngineConfig:
    """Test NeuroEngineConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = NeuroEngineConfig()

        # MLSDM defaults
        assert config.dim == 384
        assert config.capacity == 20_000
        assert config.wake_duration == 8
        assert config.sleep_duration == 3
        assert config.initial_moral_threshold == 0.50
        assert config.llm_timeout == 30.0
        assert config.llm_retry_attempts == 3

        # FSLGS defaults
        assert config.enable_fslgs is True
        assert config.enable_universal_grammar is True
        assert config.grammar_strictness == 0.9
        assert config.association_threshold == 0.65
        assert config.enable_monitoring is True
        assert config.stress_threshold == 0.7
        assert config.fslgs_fractal_levels is None
        assert config.fslgs_memory_capacity == 0
        assert config.enable_entity_tracking is True
        assert config.enable_temporal_validation is True
        assert config.enable_causal_checking is True

        # Runtime defaults
        assert config.default_moral_value == 0.5
        assert config.default_context_top_k == 5
        assert config.default_cognitive_load == 0.5
        assert config.default_user_intent == "conversational"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = NeuroEngineConfig(
            dim=512,
            capacity=10_000,
            wake_duration=10,
            enable_fslgs=False,
            default_moral_value=0.7,
        )

        assert config.dim == 512
        assert config.capacity == 10_000
        assert config.wake_duration == 10
        assert config.enable_fslgs is False
        assert config.default_moral_value == 0.7


class TestNeuroCognitiveEngineInit:
    """Test NeuroCognitiveEngine initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
        )

        assert engine.config is not None
        assert engine.config.dim == 384
        assert engine._mlsdm is not None
        assert engine._last_mlsdm_state is None
        # FSLGS will be None since it's not installed
        assert engine._fslgs is None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(512))

        config = NeuroEngineConfig(
            dim=512,
            capacity=5_000,
            enable_fslgs=False,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        assert engine.config.dim == 512
        assert engine.config.capacity == 5_000
        assert engine.config.enable_fslgs is False
        assert engine._fslgs is None

    def test_init_without_fslgs_installed(self):
        """Test that engine works when FSLGS is not installed."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        # FSLGS should be None by default (not installed in test environment)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
        )

        assert engine._fslgs is None


class TestNeuroCognitiveEngineGenerate:
    """Test NeuroCognitiveEngine.generate method."""

    def test_generate_without_fslgs(self):
        """Test generate method when FSLGS is not available (fallback mode)."""
        llm_fn = Mock(return_value="Hello, world!")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        result = engine.generate("Test prompt", max_tokens=128)

        # Verify structure
        assert "response" in result
        assert "governance" in result
        assert "mlsdm" in result

        # Verify values
        assert result["response"] == "Hello, world!"
        assert result["governance"] is None
        assert result["mlsdm"] is not None
        assert "response" in result["mlsdm"]

    def test_generate_with_custom_parameters(self):
        """Test generate with custom moral_value and context_top_k."""
        llm_fn = Mock(return_value="Custom response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        result = engine.generate(
            "Test prompt",
            max_tokens=256,
            moral_value=0.8,
            context_top_k=10,
        )

        assert result["response"] == "Custom response"
        assert result["mlsdm"] is not None

    def test_generate_uses_default_parameters(self):
        """Test that generate uses config defaults when parameters not provided."""
        llm_fn = Mock(return_value="Default response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            default_moral_value=0.6,
            default_context_top_k=7,
            default_user_intent="testing",
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        result = engine.generate("Test prompt")

        assert result["response"] == "Default response"
        # Verify defaults were used (implicitly through successful generation)
        assert result["mlsdm"] is not None

    @patch("mlsdm.engine.neuro_cognitive_engine.FSLGSWrapper")
    def test_generate_with_fslgs_mock(self, mock_fslgs_class):
        """Test generate method with mocked FSLGS integration."""
        llm_fn = Mock(return_value="MLSDM response")
        embed_fn = Mock(return_value=np.random.randn(384))

        # Mock FSLGS instance and its generate method
        mock_fslgs_instance = Mock()
        mock_fslgs_instance.generate.return_value = {
            "response": "FSLGS enhanced response",
            "governance_data": {"dual_stream": "processed"},
        }
        mock_fslgs_class.return_value = mock_fslgs_instance

        config = NeuroEngineConfig(enable_fslgs=True)

        # Patch FSLGSWrapper at module level to simulate it being available
        with patch("mlsdm.engine.neuro_cognitive_engine.FSLGSWrapper", mock_fslgs_class):
            engine = NeuroCognitiveEngine(
                llm_generate_fn=llm_fn,
                embedding_fn=embed_fn,
                config=config,
            )

            # FSLGS should be initialized
            assert engine._fslgs is not None

            result = engine.generate("Test prompt", max_tokens=128)

            # Verify FSLGS was called
            mock_fslgs_instance.generate.assert_called_once()

            # Verify result structure
            assert result["response"] == "FSLGS enhanced response"
            assert result["governance"] is not None
            # mlsdm state may be None if governed_llm wasn't actually called by the mock
            assert "mlsdm" in result


class TestNeuroCognitiveEngineState:
    """Test NeuroCognitiveEngine state management."""

    def test_get_last_states_initial(self):
        """Test get_last_states returns correct initial state."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
        )

        states = engine.get_last_states()

        assert "mlsdm" in states
        assert "has_fslgs" in states
        assert states["mlsdm"] is None  # No generation yet
        assert states["has_fslgs"] is False  # FSLGS not installed

    def test_get_last_states_after_generate(self):
        """Test get_last_states after a generation."""
        llm_fn = Mock(return_value="Test response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Generate to populate state
        engine.generate("Test prompt")

        states = engine.get_last_states()

        assert states["mlsdm"] is not None
        assert "response" in states["mlsdm"]
        assert states["has_fslgs"] is False


class TestNeuroCognitiveEngineErrorHandling:
    """Test error handling in NeuroCognitiveEngine."""

    def test_llm_error_propagates(self):
        """Test that LLM errors are handled and returned in response."""
        llm_fn = Mock(side_effect=RuntimeError("LLM error"))
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False, llm_retry_attempts=1)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # LLMWrapper catches errors and returns error response
        result = engine.generate("Test prompt")

        # Verify error is captured in response
        assert result["response"] == ""
        assert result["mlsdm"] is not None
        assert "error" in result["mlsdm"].get("note", "").lower()

    def test_embedding_error_handling(self):
        """Test that embedding errors are handled gracefully."""
        llm_fn = Mock(return_value="Response")
        embed_fn = Mock(side_effect=RuntimeError("Embedding error"))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # The circuit breaker catches embedding errors and returns error response
        result = engine.generate("Test prompt")

        # Verify error response structure
        assert result["response"] == ""
        assert result["mlsdm"] is not None
        assert "error" in result["mlsdm"].get("note", "").lower()


class TestNeuroCognitiveEngineIntegration:
    """Integration-level tests for NeuroCognitiveEngine."""

    def test_end_to_end_without_fslgs(self):
        """Test complete flow without FSLGS."""

        def simple_llm(prompt: str, max_tokens: int) -> str:
            return f"Response to: {prompt[:20]}"

        def simple_embed(text: str) -> np.ndarray:
            # Simple deterministic embedding for testing
            return np.ones(384) * len(text)

        config = NeuroEngineConfig(
            dim=384,
            capacity=1000,
            enable_fslgs=False,
        )

        engine = NeuroCognitiveEngine(
            llm_generate_fn=simple_llm,
            embedding_fn=simple_embed,
            config=config,
        )

        # First generation
        result1 = engine.generate("Hello, how are you?", max_tokens=50)

        assert "response" in result1
        assert result1["response"].startswith("Response to:")
        assert result1["governance"] is None
        assert result1["mlsdm"] is not None

        # Second generation (should maintain state)
        result2 = engine.generate("What is the weather?", max_tokens=50)

        assert "response" in result2
        assert result2["mlsdm"] is not None

        # Verify state is tracked
        states = engine.get_last_states()
        assert states["mlsdm"] is not None


class TestNeuroCognitiveEngineMetrics:
    """Test metrics integration in NeuroCognitiveEngine."""

    def test_get_metrics_returns_registry_when_enabled(self):
        """Test that get_metrics returns MetricsRegistry when enabled."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            enable_metrics=True,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        metrics = engine.get_metrics()
        assert metrics is not None

    def test_get_metrics_returns_none_when_disabled(self):
        """Test that get_metrics returns None when metrics disabled."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            enable_metrics=False,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        metrics = engine.get_metrics()
        assert metrics is None


class TestNeuroCognitiveEngineValidation:
    """Test input validation in NeuroCognitiveEngine."""

    def test_missing_llm_fn_and_router_raises_error(self):
        """Test that missing both llm_fn and router raises ValueError."""
        embed_fn = Mock(return_value=np.random.randn(384))

        with pytest.raises(ValueError, match="Either llm_generate_fn or router must be provided"):
            NeuroCognitiveEngine(
                llm_generate_fn=None,
                embedding_fn=embed_fn,
                router=None,
            )

    def test_missing_embedding_fn_raises_error(self):
        """Test that missing embedding_fn raises ValueError."""
        llm_fn = Mock(return_value="response")

        with pytest.raises(ValueError, match="embedding_fn is required"):
            NeuroCognitiveEngine(
                llm_generate_fn=llm_fn,
                embedding_fn=None,
            )


class TestNeuroCognitiveEngineRouter:
    """Test router integration in NeuroCognitiveEngine."""

    def test_router_provider_selection(self):
        """Test that router correctly selects provider."""
        embed_fn = Mock(return_value=np.random.randn(384))

        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = "routed response"
        mock_provider.provider_id = "mock_provider"

        # Mock router
        mock_router = Mock()
        mock_router.select_provider.return_value = "mock_provider"
        mock_router.get_provider.return_value = mock_provider

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=embed_fn,
            router=mock_router,
            config=config,
        )

        result = engine.generate("Test prompt", max_tokens=100)

        assert result["response"] == "routed response"
        mock_router.select_provider.assert_called()
        mock_provider.generate.assert_called()

    def test_router_with_variant_tracking(self):
        """Test that router tracks variants when get_variant is available."""
        embed_fn = Mock(return_value=np.random.randn(384))

        # Mock provider
        mock_provider = Mock()
        mock_provider.generate.return_value = "variant response"
        mock_provider.provider_id = "test_provider"

        # Mock router with get_variant
        mock_router = Mock()
        mock_router.select_provider.return_value = "test_provider"
        mock_router.get_provider.return_value = mock_provider
        mock_router.get_variant.return_value = "treatment"

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=embed_fn,
            router=mock_router,
            config=config,
        )

        result = engine.generate("Test prompt")

        assert result["response"] == "variant response"
        assert "meta" in result
        # Meta should contain backend_id and variant
        assert result["meta"].get("backend_id") == "test_provider"
        assert result["meta"].get("variant") == "treatment"

    def test_router_provider_type_error_fallback(self):
        """Test fallback when provider.generate doesn't accept kwargs."""
        embed_fn = Mock(return_value=np.random.randn(384))

        # Mock provider that raises TypeError on kwargs but works without kwargs
        mock_provider = Mock()
        mock_provider.provider_id = "fallback_provider"

        def generate_side_effect(prompt, max_tokens, **kwargs):
            """Simulates provider that doesn't accept kwargs."""
            if kwargs:
                raise TypeError("unexpected keyword argument")
            return "fallback response"

        mock_provider.generate.side_effect = generate_side_effect

        # Mock router
        mock_router = Mock()
        mock_router.select_provider.return_value = "fallback_provider"
        mock_router.get_provider.return_value = mock_provider

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=embed_fn,
            router=mock_router,
            config=config,
        )

        result = engine.generate("Test prompt")

        assert result["response"] == "fallback response"

    def test_router_provider_error_returns_fallback_message(self):
        """Test that provider errors return fallback message."""
        embed_fn = Mock(return_value=np.random.randn(384))

        # Mock provider that raises exception
        mock_provider = Mock()
        mock_provider.generate.side_effect = RuntimeError("provider failed")
        mock_provider.provider_id = "error_provider"

        # Mock router
        mock_router = Mock()
        mock_router.select_provider.return_value = "error_provider"
        mock_router.get_provider.return_value = mock_provider

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=None,
            embedding_fn=embed_fn,
            router=mock_router,
            config=config,
        )

        result = engine.generate("Test prompt")

        # Should contain error fallback message
        assert "[provider_error:" in result["response"]
        assert "provider failed" in result["response"]


class TestNeuroCognitiveEngineMoralChecks:
    """Test moral check paths in NeuroCognitiveEngine."""

    def test_estimate_response_moral_score_harmful_response(self):
        """Test that harmful responses get low moral score."""
        llm_fn = Mock(return_value="normal response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Test harmful pattern detection in RESPONSE text
        # The moral filter now analyzes the response text for harmful patterns
        score = engine._estimate_response_moral_score("I hate this so much", "normal prompt")
        assert score < 0.8  # Should be penalized for "hate"

        score = engine._estimate_response_moral_score("Let's attack them with violence", "normal prompt")
        assert score < 0.6  # Should be heavily penalized for "attack" and "violence"

    def test_estimate_response_moral_score_neutral_response(self):
        """Test that neutral responses get high score (innocent until proven guilty)."""
        llm_fn = Mock(return_value="I cannot respond to that")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Neutral responses without harmful patterns get high score
        score = engine._estimate_response_moral_score(
            "I am unable to respond to that request", "normal prompt"
        )
        assert score == 0.8  # High score for neutral text (no harmful patterns)

    def test_estimate_response_moral_score_positive_response(self):
        """Test that positive responses get higher moral score."""
        llm_fn = Mock(return_value="normal response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Positive response patterns increase the score
        score = engine._estimate_response_moral_score("I'm happy to help you with that!", "How are you?")
        assert score > 0.8  # Should be boosted for "help"


class TestNeuroCognitiveEngineExceptionHandling:
    """Test exception handling paths in NeuroCognitiveEngine."""

    def test_generate_handles_unexpected_exception(self):
        """Test that generate() catches unexpected exceptions."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Force an unexpected exception in internal method
        with patch.object(
            engine, "_prepare_request_context", side_effect=RuntimeError("unexpected")
        ):
            result = engine.generate("Test prompt")

            assert result["response"] == ""
            assert result["error"] is not None
            assert result["error"]["type"] == "internal_error"
            assert "RuntimeError" in result["error"]["message"]
            assert result["rejected_at"] == "generation"

    def test_empty_response_error_handling(self):
        """Test that empty response from MLSDM is handled properly."""
        # Return empty response
        llm_fn = Mock(return_value="")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        result = engine.generate("Test prompt")

        # Should handle empty response gracefully
        assert result["error"] is not None
        error_type = result["error"].get("type", "")
        assert error_type == "empty_response"
        assert error_type != "mlsdm_rejection"

    def test_whitespace_response_error_handling(self):
        """Test that whitespace-only response from MLSDM is handled properly."""
        llm_fn = Mock(return_value="   ")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        result = engine.generate("Test prompt")

        assert result["error"] is not None
        error_type = result["error"].get("type", "")
        assert error_type == "empty_response"
        assert error_type != "mlsdm_rejection"


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with NeuroCognitiveEngine."""

    def test_circuit_breaker_enabled_by_default(self):
        """Test that circuit breaker is enabled by default."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        assert engine.get_circuit_breaker() is not None
        state = engine.get_circuit_breaker_state()
        assert state["enabled"] is True
        assert state["state"] == "closed"

    def test_circuit_breaker_can_be_disabled(self):
        """Test that circuit breaker can be disabled via config."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False, enable_circuit_breaker=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        assert engine.get_circuit_breaker() is None
        state = engine.get_circuit_breaker_state()
        assert state["enabled"] is False

    def test_circuit_breaker_custom_config(self):
        """Test circuit breaker with custom configuration."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            circuit_breaker_failure_threshold=10,
            circuit_breaker_success_threshold=5,
            circuit_breaker_recovery_timeout=60.0,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        cb = engine.get_circuit_breaker()
        assert cb is not None
        assert cb.config.failure_threshold == 10
        assert cb.config.success_threshold == 5
        assert cb.config.recovery_timeout == 60.0

    def test_circuit_breaker_records_success(self):
        """Test that successful generations record success on circuit breaker."""
        llm_fn = Mock(return_value="test response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Generate should record success
        result = engine.generate("Test prompt")
        assert result["error"] is None

        cb = engine.get_circuit_breaker()
        stats = cb.get_stats()
        assert stats.total_successes == 1
        assert stats.total_failures == 0

    def test_circuit_breaker_records_failure(self):
        """Test that failed generations record failure on circuit breaker."""
        # LLM that throws exception
        llm_fn = Mock(side_effect=RuntimeError("Provider error"))
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            circuit_breaker_failure_threshold=5,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Generate with moral_value that allows neutral prompts to pass moral filter
        # (neutral prompts score 0.8, so we use 0.5 to ensure they pass)
        result = engine.generate("Test prompt", moral_value=0.5)
        assert result["error"] is not None

        cb = engine.get_circuit_breaker()
        stats = cb.get_stats()
        assert stats.total_failures == 1

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        call_count = 0

        def failing_llm(prompt, max_tokens, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"Provider error {call_count}")

        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(
            enable_fslgs=False,
            circuit_breaker_failure_threshold=3,
        )
        engine = NeuroCognitiveEngine(
            llm_generate_fn=failing_llm,
            embedding_fn=embed_fn,
            config=config,
        )

        cb = engine.get_circuit_breaker()

        # Record failures directly on circuit breaker to simulate provider failures
        # This avoids MLSDM internal state affecting the test
        for _ in range(3):
            cb.record_failure(RuntimeError("Provider error"))

        # Circuit should now be open
        assert cb.state == CircuitState.OPEN

        # Next generate call should fail fast with circuit_open error
        result = engine.generate("Test prompt", moral_value=0.5)
        assert result["error"]["type"] == "circuit_open"
        assert "circuit breaker" in result["error"]["message"].lower()

    def test_circuit_breaker_state_in_response(self):
        """Test that circuit breaker state is included in get_circuit_breaker_state."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        state = engine.get_circuit_breaker_state()

        assert "name" in state
        assert "state" in state
        assert "config" in state
        assert "total_failures" in state
        assert "total_successes" in state

    def test_circuit_breaker_ignores_moral_rejections(self):
        """Test that moral rejections don't trigger circuit breaker failures."""
        llm_fn = Mock(return_value="response")
        embed_fn = Mock(return_value=np.random.randn(384))

        config = NeuroEngineConfig(enable_fslgs=False)
        engine = NeuroCognitiveEngine(
            llm_generate_fn=llm_fn,
            embedding_fn=embed_fn,
            config=config,
        )

        # Generate with very high moral threshold to trigger moral rejection
        # Using a prompt that will be evaluated as low moral score
        _ = engine.generate("Test", moral_value=0.99)

        # Check circuit breaker wasn't affected
        cb = engine.get_circuit_breaker()
        stats = cb.get_stats()
        # Either it succeeded (success recorded) or it was a moral rejection (no failure recorded)
        assert stats.total_failures == 0
