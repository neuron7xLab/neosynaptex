"""
Integration Tests for NeuroLangWrapper

This test suite validates the complete NeuroLang + Aphasia-Broca pipeline
with full end-to-end integration.
"""

import numpy as np
import pytest

from mlsdm.extensions import NeuroLangWrapper
from mlsdm.extensions.neuro_lang_extension import TORCH_AVAILABLE

pytestmark = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="NeuroLang integration tests require PyTorch (mlsdm[neurolang])",
)


def dummy_llm(prompt: str, max_tokens: int) -> str:
    return (
        "This is a coherent answer that uses normal grammar and function words "
        "to describe the system behaviour in a clear way."
    )


def dummy_embedder(text: str):
    """Generate deterministic embeddings based on text hash."""
    np.random.seed(hash(text) & 0xFFFFFFFF)
    vec = np.random.randn(384).astype(np.float32)
    return vec / np.linalg.norm(vec)


def test_neurolang_wrapper_happy_path():
    """Test NeuroLangWrapper with valid inputs and successful generation."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=1024,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(
        prompt="Describe the system briefly.",
        moral_value=0.8,
        max_tokens=128,
    )

    assert isinstance(result, dict)
    for key in ("response", "phase", "accepted", "neuro_enhancement", "aphasia_flags"):
        assert key in result, f"Missing key: {key}"

    assert result["accepted"] is True

    aphasia_flags = result["aphasia_flags"]
    assert isinstance(aphasia_flags, dict)
    assert "is_aphasic" in aphasia_flags
    assert "severity" in aphasia_flags


def test_neurolang_wrapper_low_moral_value():
    """Test NeuroLangWrapper with low moral value (should be rejected)."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=1024,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(
        prompt="Test prompt.",
        moral_value=0.1,
        max_tokens=128,
    )

    assert isinstance(result, dict)
    assert result["accepted"] is False
    assert "response" in result


def test_neurolang_wrapper_aphasic_detection():
    """Test that NeuroLangWrapper detects and handles aphasic responses."""

    def aphasic_llm(prompt: str, max_tokens: int) -> str:
        return "Bad. Short. No good."

    wrapper = NeuroLangWrapper(
        llm_generate_fn=aphasic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=1024,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(
        prompt="Describe the system.",
        moral_value=0.8,
        max_tokens=128,
    )

    assert isinstance(result, dict)
    assert result["accepted"] is True

    aphasia_flags = result["aphasia_flags"]
    assert aphasia_flags["is_aphasic"] is True
    assert aphasia_flags["severity"] > 0.0


def test_neurolang_wrapper_multiple_generations():
    """Test NeuroLangWrapper with multiple sequential generations."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=1024,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    results = []
    for i in range(5):
        result = wrapper.generate(
            prompt=f"Test prompt {i}.",
            moral_value=0.8,
            max_tokens=128,
        )
        results.append(result)

    assert len(results) == 5
    for result in results:
        assert isinstance(result, dict)
        assert "response" in result
        assert "aphasia_flags" in result


def test_neurolang_wrapper_neuro_enhancement():
    """Test that NeuroLangWrapper provides neuro_enhancement metadata."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=1024,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(
        prompt="Test the NeuroLang enhancement.",
        moral_value=0.8,
        max_tokens=128,
    )

    assert "neuro_enhancement" in result
    assert isinstance(result["neuro_enhancement"], str)
    assert len(result["neuro_enhancement"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
