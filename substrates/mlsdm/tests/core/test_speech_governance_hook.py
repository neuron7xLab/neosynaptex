"""
Unit tests for Speech Governance Hook in LLMWrapper.

Tests the integration of speech governance policies into the core LLM wrapper,
demonstrating that arbitrary speech policies can be plugged in without
modifying the wrapper itself.
"""

import numpy as np
import pytest

from mlsdm.core.llm_wrapper import LLMWrapper
from mlsdm.speech.governance import SpeechGovernanceResult


def dummy_llm(prompt: str, max_tokens: int) -> str:
    """Simple mock LLM that echoes part of the prompt."""
    return "draft response"


def dummy_embedder(text: str):
    """Generate deterministic embeddings based on text hash."""
    np.random.seed(hash(text) & 0xFFFFFFFF)
    vec = np.random.randn(384).astype(np.float32)
    return vec / np.linalg.norm(vec)


class UpperCaseGovernor:
    """Test governor that converts text to uppercase."""

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        return SpeechGovernanceResult(
            final_text=draft.upper(),
            raw_text=draft,
            metadata={"case": "upper", "prompt_length": len(prompt)},
        )


class PrefixGovernor:
    """Test governor that adds a prefix to responses."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        return SpeechGovernanceResult(
            final_text=f"{self.prefix}: {draft}",
            raw_text=draft,
            metadata={"prefix_added": self.prefix},
        )


class ConditionalGovernor:
    """Test governor that only modifies text if a condition is met."""

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        # Only modify if draft is short
        if len(draft) < 20:
            final = f"[EXPANDED] {draft}"
            modified = True
        else:
            final = draft
            modified = False

        return SpeechGovernanceResult(
            final_text=final,
            raw_text=draft,
            metadata={"modified": modified, "original_length": len(draft)},
        )


def test_llmwrapper_without_governor():
    """Test that LLMWrapper works normally without a speech governor."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(prompt="test prompt", moral_value=0.8, max_tokens=16)

    assert result["accepted"] is True
    assert result["response"] == "draft response"
    assert "speech_governance" not in result


def test_llmwrapper_applies_uppercase_governor():
    """Test that speech governor is applied to LLM output."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        speech_governor=UpperCaseGovernor(),
    )

    result = wrapper.generate(prompt="hi", moral_value=0.8, max_tokens=16)

    assert result["accepted"] is True
    assert result["response"] == "DRAFT RESPONSE"
    assert "speech_governance" in result

    sg = result["speech_governance"]
    assert sg["raw_text"] == "draft response"
    assert sg["metadata"]["case"] == "upper"
    assert "prompt_length" in sg["metadata"]


def test_llmwrapper_applies_prefix_governor():
    """Test that parameterized governor works correctly."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        speech_governor=PrefixGovernor("[SAFE]"),
    )

    result = wrapper.generate(prompt="hello", moral_value=0.8, max_tokens=16)

    assert result["accepted"] is True
    assert result["response"] == "[SAFE]: draft response"
    assert result["speech_governance"]["raw_text"] == "draft response"
    assert result["speech_governance"]["metadata"]["prefix_added"] == "[SAFE]"


def test_llmwrapper_applies_conditional_governor():
    """Test that governor can make conditional modifications."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        speech_governor=ConditionalGovernor(),
    )

    result = wrapper.generate(prompt="test", moral_value=0.8, max_tokens=16)

    assert result["accepted"] is True
    # "draft response" is 14 chars, less than 20, so should be expanded
    assert result["response"] == "[EXPANDED] draft response"
    assert result["speech_governance"]["metadata"]["modified"] is True
    assert result["speech_governance"]["metadata"]["original_length"] == 14


def test_speech_governance_receives_correct_parameters():
    """Test that governor receives the correct prompt, draft, and max_tokens."""
    received_params = {}

    class ParameterCapturingGovernor:
        def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
            received_params["prompt"] = prompt
            received_params["draft"] = draft
            received_params["max_tokens"] = max_tokens
            return SpeechGovernanceResult(
                final_text=draft,
                raw_text=draft,
                metadata={},
            )

    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        speech_governor=ParameterCapturingGovernor(),
    )

    wrapper.generate(prompt="test prompt", moral_value=0.8, max_tokens=32)

    assert received_params["prompt"] == "test prompt"
    assert received_params["draft"] == "draft response"
    assert received_params["max_tokens"] == 32


def test_speech_governance_preserves_other_response_fields():
    """Test that governor doesn't interfere with other response fields."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        speech_governor=UpperCaseGovernor(),
    )

    result = wrapper.generate(prompt="test", moral_value=0.8, max_tokens=16)

    # Verify all standard fields are present
    assert "accepted" in result
    assert "phase" in result
    assert "step" in result
    assert "note" in result
    assert "moral_threshold" in result
    assert "context_items" in result
    assert "max_tokens_used" in result


def test_speech_governance_not_applied_on_rejection():
    """Test that governor is not applied when request is rejected."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.99,  # Very high threshold
        speech_governor=UpperCaseGovernor(),
    )

    result = wrapper.generate(prompt="test", moral_value=0.1, max_tokens=16)

    assert result["accepted"] is False
    assert "speech_governance" not in result


def test_speech_governance_not_applied_during_sleep():
    """Test that governor is not applied during sleep phase."""
    wrapper = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=1,
        sleep_duration=3,
        speech_governor=UpperCaseGovernor(),
    )

    # First request to enter wake phase
    result1 = wrapper.generate(prompt="wake", moral_value=0.8, max_tokens=16)
    assert result1["accepted"] is True

    # Step through wake phase to enter sleep
    result2 = wrapper.generate(prompt="wake", moral_value=0.8, max_tokens=16)

    # Should be in sleep now, request rejected
    if not result2["accepted"]:
        assert "speech_governance" not in result2


def test_multiple_governors_can_be_swapped():
    """Test that different governor instances can be used."""
    # Test with one governor
    wrapper1 = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        speech_governor=PrefixGovernor("[A]"),
    )

    result1 = wrapper1.generate(prompt="test", moral_value=0.8, max_tokens=16)
    assert result1["response"] == "[A]: draft response"

    # Test with different governor
    wrapper2 = LLMWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=128,
        wake_duration=2,
        sleep_duration=1,
        speech_governor=PrefixGovernor("[B]"),
    )

    result2 = wrapper2.generate(prompt="test", moral_value=0.8, max_tokens=16)
    assert result2["response"] == "[B]: draft response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
