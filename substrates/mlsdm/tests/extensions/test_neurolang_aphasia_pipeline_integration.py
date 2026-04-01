"""
Integration tests for NeuroLangWrapper with PipelineSpeechGovernor.

Tests that NeuroLangWrapper correctly uses PipelineSpeechGovernor
and exposes the proper metadata structure.

Requires PyTorch (torch). Tests are skipped if torch is not installed.
"""

import numpy as np
import pytest

# Skip all tests in this module if torch is not available
pytest.importorskip("torch")

from mlsdm.extensions import NeuroLangWrapper


def dummy_llm(prompt: str, max_tokens: int) -> str:
    # Deliberately telegraphic style to trigger Aphasia
    return "This short. No connect. Bad."


def dummy_embedder(text: str):
    v = np.ones(384, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_neurolang_uses_speech_pipeline_and_exposes_metadata():
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        # Default aphasia_detect_enabled=True
    )

    result = wrapper.generate(prompt="Test", moral_value=0.8, max_tokens=64)

    assert "speech_governance" in result
    sg = result["speech_governance"]
    assert "pipeline" in sg["metadata"]

    steps = sg["metadata"]["pipeline"]
    # Should have at least one step (Aphasia)
    names = [step["name"] for step in steps]
    assert "aphasia_broca" in names


def test_neurolang_pipeline_step_structure():
    """Test that pipeline steps have correct structure."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(prompt="Explain something", moral_value=0.8, max_tokens=64)

    sg = result["speech_governance"]
    steps = sg["metadata"]["pipeline"]

    # Find aphasia_broca step
    aphasia_step = None
    for step in steps:
        if step["name"] == "aphasia_broca":
            aphasia_step = step
            break

    assert aphasia_step is not None
    assert "status" in aphasia_step
    assert aphasia_step["status"] in ["ok", "error"]

    if aphasia_step["status"] == "ok":
        # Successful step should have these fields
        assert "raw_text" in aphasia_step
        assert "final_text" in aphasia_step
        assert "metadata" in aphasia_step
        # Aphasia-specific metadata
        assert "aphasia_report" in aphasia_step["metadata"]


def test_neurolang_with_aphasia_disabled():
    """Test that when aphasia is disabled, no pipeline is used."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_detect_enabled=False,
    )

    result = wrapper.generate(prompt="Test", moral_value=0.8, max_tokens=64)

    # When aphasia is disabled, no speech_governance should be present
    assert "speech_governance" not in result


def test_neurolang_pipeline_preserves_raw_text():
    """Test that pipeline preserves the original draft in raw_text."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(prompt="Test", moral_value=0.8, max_tokens=64)

    sg = result["speech_governance"]
    # raw_text at top level should be the original draft
    assert sg["raw_text"] == "This short. No connect. Bad."


def test_neurolang_backward_compatible_aphasia_flags():
    """Test that aphasia_flags still exists for backward compatibility."""
    wrapper = NeuroLangWrapper(
        llm_generate_fn=dummy_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
    )

    result = wrapper.generate(prompt="Test", moral_value=0.8, max_tokens=64)

    # NeuroLangWrapper still exposes aphasia_flags for backward compatibility
    assert "aphasia_flags" in result
    # It should contain the aphasia report
    assert result["aphasia_flags"] is not None


def test_neurolang_pipeline_with_repair_enabled():
    """Test pipeline when repair is enabled."""

    def repair_llm(prompt: str, max_tokens: int) -> str:
        if "Broca-like aphasia" in prompt:
            return "This is a properly repaired sentence with good grammar."
        return "This short. No connect. Bad."

    wrapper = NeuroLangWrapper(
        llm_generate_fn=repair_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        capacity=512,
        wake_duration=2,
        sleep_duration=1,
        initial_moral_threshold=0.5,
        aphasia_repair_enabled=True,
    )

    result = wrapper.generate(prompt="Test", moral_value=0.8, max_tokens=64)

    sg = result["speech_governance"]
    steps = sg["metadata"]["pipeline"]

    aphasia_step = next((s for s in steps if s["name"] == "aphasia_broca"), None)
    assert aphasia_step is not None
    assert "metadata" in aphasia_step
    # Check if repair was attempted
    # (Actual repair depends on severity threshold and detection)
    assert "repaired" in aphasia_step["metadata"]
