"""
Integration tests for the public MLSDM Python API.

Tests that `from mlsdm import ...` provides a stable public interface
and that the factory functions work correctly.
"""

import numpy as np
import pytest


class TestPublicImports:
    """Test that all public API components can be imported."""

    def test_import_version(self):
        """Test version string import."""
        from mlsdm import __version__

        assert isinstance(__version__, str)
        assert __version__ == "1.2.0"

    def test_import_llm_wrapper(self):
        """Test LLMWrapper class import."""
        from mlsdm import LLMWrapper

        assert LLMWrapper is not None
        assert callable(LLMWrapper)

    def test_import_neuro_cognitive_engine(self):
        """Test NeuroCognitiveEngine class import."""
        from mlsdm import NeuroCognitiveEngine, NeuroEngineConfig

        assert NeuroCognitiveEngine is not None
        assert NeuroEngineConfig is not None

    def test_import_client(self):
        """Test NeuroCognitiveClient import."""
        from mlsdm import NeuroCognitiveClient

        assert NeuroCognitiveClient is not None

    def test_import_speech_governance(self):
        """Test speech governance types import."""
        from mlsdm import (
            PipelineSpeechGovernor,
            SpeechGovernanceResult,
            SpeechGovernor,
        )

        assert SpeechGovernor is not None
        assert SpeechGovernanceResult is not None
        assert PipelineSpeechGovernor is not None

    def test_import_factory_functions(self):
        """Test factory function imports."""
        from mlsdm import (
            build_neuro_engine_from_env,
            build_stub_embedding_fn,
            create_llm_wrapper,
            create_neuro_engine,
        )

        assert callable(create_llm_wrapper)
        assert callable(create_neuro_engine)
        assert callable(build_neuro_engine_from_env)
        assert callable(build_stub_embedding_fn)


class TestCreateLLMWrapper:
    """Test the create_llm_wrapper factory function."""

    def test_create_with_defaults(self):
        """Test creating LLMWrapper with default parameters."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        assert wrapper is not None

    def test_generate_basic(self):
        """Test basic generation with default wrapper."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        result = wrapper.generate(prompt="Hello, world!", moral_value=0.8)

        assert "response" in result
        assert "accepted" in result
        assert "phase" in result
        assert result["accepted"] is True

    def test_generate_with_moral_filtering(self):
        """Test that moral filtering works."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper(initial_moral_threshold=0.9)

        # Low moral value should be rejected
        result = wrapper.generate(prompt="Test", moral_value=0.1)
        assert result["accepted"] is False
        assert "morally rejected" in result["note"]

    def test_custom_llm_function(self):
        """Test with custom LLM function."""
        from mlsdm import create_llm_wrapper

        def custom_llm(prompt: str, max_tokens: int) -> str:
            return f"Custom response to: {prompt[:20]}"

        wrapper = create_llm_wrapper(llm_generate_fn=custom_llm)
        result = wrapper.generate(prompt="Test prompt", moral_value=0.8)

        assert result["accepted"] is True
        assert "Custom response" in result["response"]

    def test_custom_embedding_function(self):
        """Test with custom embedding function."""
        from mlsdm import create_llm_wrapper

        def custom_embed(text: str) -> np.ndarray:
            # Simple deterministic embedding
            vec = np.ones(384, dtype=np.float32)
            return vec / np.linalg.norm(vec)

        wrapper = create_llm_wrapper(embedding_fn=custom_embed, dim=384)
        result = wrapper.generate(prompt="Test", moral_value=0.8)
        assert result["accepted"] is True

    def test_get_state(self):
        """Test getting wrapper state."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper()
        wrapper.generate(prompt="Test 1", moral_value=0.9)
        wrapper.generate(prompt="Test 2", moral_value=0.9)

        state = wrapper.get_state()
        assert "step" in state
        assert state["step"] == 2
        assert "phase" in state
        assert "moral_threshold" in state


class TestCreateNeuroEngine:
    """Test the create_neuro_engine factory function."""

    def test_create_with_defaults(self):
        """Test creating engine with default parameters."""
        from mlsdm import create_neuro_engine

        engine = create_neuro_engine()
        assert engine is not None

    def test_generate_basic(self):
        """Test basic generation with default engine."""
        from mlsdm import create_neuro_engine

        engine = create_neuro_engine()
        result = engine.generate("Tell me about Python")

        assert "response" in result
        assert "timing" in result
        assert "validation_steps" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

    def test_generate_with_params(self):
        """Test generation with explicit parameters."""
        from mlsdm import create_neuro_engine

        engine = create_neuro_engine()
        result = engine.generate(
            prompt="Test prompt",
            max_tokens=256,
            moral_value=0.7,
            user_intent="test",
            context_top_k=3,
        )

        assert "response" in result
        assert "timing" in result

    def test_custom_config(self):
        """Test with custom NeuroEngineConfig."""
        from mlsdm import NeuroEngineConfig, create_neuro_engine

        config = NeuroEngineConfig(
            dim=384,
            enable_fslgs=False,
            enable_metrics=False,
            initial_moral_threshold=0.6,
        )
        engine = create_neuro_engine(config=config)

        result = engine.generate("Test")
        assert "response" in result


class TestNeuroCognitiveClient:
    """Test the NeuroCognitiveClient SDK."""

    def test_create_with_local_stub(self):
        """Test creating client with local stub backend."""
        from mlsdm import NeuroCognitiveClient

        client = NeuroCognitiveClient(backend="local_stub")
        assert client.backend == "local_stub"

    def test_generate(self):
        """Test generation through client."""
        from mlsdm import NeuroCognitiveClient

        client = NeuroCognitiveClient(backend="local_stub")
        result = client.generate("What is AI?")

        assert "response" in result
        assert isinstance(result["response"], str)

    def test_generate_with_params(self):
        """Test generation with all parameters."""
        from mlsdm import NeuroCognitiveClient

        client = NeuroCognitiveClient(backend="local_stub")
        result = client.generate(
            prompt="Explain machine learning",
            max_tokens=200,
            moral_value=0.8,
            user_intent="educational",
            cognitive_load=0.5,
            context_top_k=5,
        )

        assert "response" in result

    def test_invalid_backend_raises(self):
        """Test that invalid backend raises ValueError."""
        from mlsdm import NeuroCognitiveClient

        with pytest.raises(ValueError, match="Invalid backend"):
            NeuroCognitiveClient(backend="invalid_backend")


class TestSpeechGovernance:
    """Test speech governance integration."""

    def test_custom_speech_governor(self):
        """Test wrapper with custom speech governor."""
        from mlsdm import SpeechGovernanceResult, create_llm_wrapper

        class TestGovernor:
            def __call__(
                self, *, prompt: str, draft: str, max_tokens: int
            ) -> SpeechGovernanceResult:
                return SpeechGovernanceResult(
                    final_text=draft.upper(),
                    raw_text=draft,
                    metadata={"transformed": True},
                )

        wrapper = create_llm_wrapper(speech_governor=TestGovernor())
        result = wrapper.generate(prompt="Hello", moral_value=0.9)

        assert result["accepted"] is True
        # Response should be uppercased by governor
        assert result["response"].isupper()
        assert "speech_governance" in result
        assert result["speech_governance"]["metadata"]["transformed"] is True

    def test_pipeline_speech_governor(self):
        """Test pipeline speech governor composition."""
        from mlsdm import (
            PipelineSpeechGovernor,
            SpeechGovernanceResult,
            create_llm_wrapper,
        )

        class UppercaseGovernor:
            def __call__(
                self, *, prompt: str, draft: str, max_tokens: int
            ) -> SpeechGovernanceResult:
                return SpeechGovernanceResult(
                    final_text=draft.upper(),
                    raw_text=draft,
                    metadata={"step": "uppercase"},
                )

        class SuffixGovernor:
            def __call__(
                self, *, prompt: str, draft: str, max_tokens: int
            ) -> SpeechGovernanceResult:
                return SpeechGovernanceResult(
                    final_text=draft + " [GOVERNED]",
                    raw_text=draft,
                    metadata={"step": "suffix"},
                )

        pipeline = PipelineSpeechGovernor(
            governors=[
                ("uppercase", UppercaseGovernor()),
                ("suffix", SuffixGovernor()),
            ]
        )

        wrapper = create_llm_wrapper(speech_governor=pipeline)
        result = wrapper.generate(prompt="Test", moral_value=0.9)

        assert result["accepted"] is True
        # Should be uppercased and have suffix
        assert "[GOVERNED]" in result["response"]


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_multi_turn_conversation(self):
        """Test multiple turns of conversation."""
        from mlsdm import create_llm_wrapper

        def deterministic_llm(prompt: str, max_tokens: int) -> str:
            return (
                "Deterministic response for integration testing with enough tokens "
                "to stay within the quality gate thresholds."
            )

        wrapper = create_llm_wrapper(llm_generate_fn=deterministic_llm, wake_duration=10)

        prompts = [
            "Hello, how are you?",
            "Tell me about Python",
            "What's your favorite color?",
        ]

        for prompt in prompts:
            result = wrapper.generate(prompt=prompt, moral_value=0.85)
            assert result["accepted"] is True

        state = wrapper.get_state()
        assert state["step"] == 3
        assert state["accepted_count"] == 3

    def test_memory_context_retrieval(self):
        """Test that memory context is retrieved."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper(wake_duration=10)

        # Build context
        topics = ["AI", "Python", "Machine Learning"]
        for topic in topics:
            wrapper.generate(prompt=f"Tell me about {topic}", moral_value=0.9)

        # Query related topic
        result = wrapper.generate(prompt="Explain programming", moral_value=0.9)
        assert result["accepted"] is True
        assert "context_items" in result

    def test_cycle_through_wake_sleep(self):
        """Test wake/sleep cycle behavior."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper(wake_duration=2, sleep_duration=1)

        results = []
        for i in range(5):
            result = wrapper.generate(prompt=f"Message {i}", moral_value=0.9)
            results.append(result)

        # Should have mix of accepted and rejected (during sleep)
        accepted = sum(1 for r in results if r["accepted"])
        rejected = sum(1 for r in results if not r["accepted"])

        assert accepted > 0
        assert rejected > 0  # At least one during sleep

    def test_moral_threshold_adaptation(self):
        """Test that moral threshold adapts over time."""
        from mlsdm import create_llm_wrapper

        wrapper = create_llm_wrapper(initial_moral_threshold=0.5)
        initial_threshold = wrapper.get_state()["moral_threshold"]

        # Generate with high moral values
        for _ in range(5):
            wrapper.generate(prompt="Test", moral_value=0.95)

        final_threshold = wrapper.get_state()["moral_threshold"]

        # Threshold should have adapted
        assert final_threshold != initial_threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
