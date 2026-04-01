"""
Tests for NeuroLang optional dependency.

Validates that:
1. Core MLSDM and AphasiaBrocaDetector work without PyTorch
2. NeuroLangWrapper raises clear errors when neurolang_mode is enabled without PyTorch
3. NeuroLangWrapper works when neurolang_mode is disabled without PyTorch
"""

import sys
from unittest.mock import patch

import numpy as np
import pytest


def test_import_aphasia_without_torch_ok():
    """Test that AphasiaBrocaDetector can be imported and used without torch."""
    # Mock torch as unavailable
    with patch.dict(sys.modules, {"torch": None}):
        # Force reload to trigger the ImportError handling

        import mlsdm.extensions.neuro_lang_extension as nle_module

        # Temporarily set TORCH_AVAILABLE to False
        original_torch_available = nle_module.TORCH_AVAILABLE
        nle_module.TORCH_AVAILABLE = False

        try:
            # Import and instantiate AphasiaBrocaDetector
            from mlsdm.extensions import AphasiaBrocaDetector

            detector = AphasiaBrocaDetector()

            # Test that it works without torch
            result = detector.analyze("This short. No connect. Bad.")

            assert result is not None
            assert "is_aphasic" in result
            assert result["is_aphasic"] is True  # This text should be detected as aphasic
            assert "severity" in result
            assert "flags" in result
        finally:
            # Restore original value
            nle_module.TORCH_AVAILABLE = original_torch_available


def test_neurolang_wrapper_raises_without_torch_if_enabled():
    """Test that NeuroLangWrapper raises RuntimeError when neurolang_mode is enabled without torch."""
    import mlsdm.extensions.neuro_lang_extension as nle_module

    # Temporarily set TORCH_AVAILABLE to False
    original_torch_available = nle_module.TORCH_AVAILABLE
    nle_module.TORCH_AVAILABLE = False

    try:
        from mlsdm.extensions import NeuroLangWrapper

        # Mock LLM and embedding functions
        def mock_llm(prompt: str, max_tokens: int) -> str:
            return "Mock response"

        def mock_embedder(text: str) -> np.ndarray:
            return np.random.randn(384).astype(np.float32)

        # Try to create NeuroLangWrapper with neurolang_mode enabled
        with pytest.raises(RuntimeError) as exc_info:
            NeuroLangWrapper(
                llm_generate_fn=mock_llm,
                embedding_fn=mock_embedder,
                neurolang_mode="eager_train",
                dim=384,
            )

        # Check that error message is clear and helpful
        error_message = str(exc_info.value)
        assert "mlsdm[neurolang]" in error_message
        assert "PyTorch" in error_message or "torch" in error_message.lower()
        assert "disabled" in error_message
    finally:
        # Restore original value
        nle_module.TORCH_AVAILABLE = original_torch_available


def test_neurolang_wrapper_allowed_when_disabled_without_torch():
    """Test that NeuroLangWrapper works when neurolang_mode='disabled' without torch."""
    import mlsdm.extensions.neuro_lang_extension as nle_module

    # Temporarily set TORCH_AVAILABLE to False
    original_torch_available = nle_module.TORCH_AVAILABLE
    nle_module.TORCH_AVAILABLE = False

    try:
        from mlsdm.extensions import NeuroLangWrapper

        # Mock LLM and embedding functions
        def mock_llm(prompt: str, max_tokens: int) -> str:
            return "This is a proper full sentence response."

        def mock_embedder(text: str) -> np.ndarray:
            return np.random.randn(384).astype(np.float32)

        # Create NeuroLangWrapper with neurolang_mode disabled - should work
        wrapper = NeuroLangWrapper(
            llm_generate_fn=mock_llm,
            embedding_fn=mock_embedder,
            neurolang_mode="disabled",
            dim=384,
            aphasia_detect_enabled=True,
            aphasia_repair_enabled=False,  # Disable repair to avoid extra LLM calls
        )

        # Generate should work (without NeuroLang enhancement)
        result = wrapper.generate(
            prompt="Test prompt",
            moral_value=0.8,
            max_tokens=50,
        )

        assert result is not None
        assert "response" in result
        assert result["response"] == "This is a proper full sentence response."
        assert result["neuro_enhancement"] == "NeuroLang disabled"
        assert result["accepted"] is True

        # Aphasia detection should still work
        if result["aphasia_flags"] is not None:
            assert "is_aphasic" in result["aphasia_flags"]
    finally:
        # Restore original value
        nle_module.TORCH_AVAILABLE = original_torch_available


def test_neurolang_wrapper_with_torch_enabled():
    """Test that NeuroLangWrapper works normally when torch is available and mode is enabled."""
    import mlsdm.extensions.neuro_lang_extension as nle_module

    # Only run if torch is actually available
    if not nle_module.TORCH_AVAILABLE:
        pytest.skip("PyTorch not available - skipping test with torch")

    from mlsdm.extensions import NeuroLangWrapper

    # Mock LLM and embedding functions
    def mock_llm(prompt: str, max_tokens: int) -> str:
        return "This is a proper full sentence response with good grammar."

    def mock_embedder(text: str) -> np.ndarray:
        return np.random.randn(384).astype(np.float32)

    # Create NeuroLangWrapper with neurolang_mode enabled - should work with torch
    wrapper = NeuroLangWrapper(
        llm_generate_fn=mock_llm,
        embedding_fn=mock_embedder,
        neurolang_mode="eager_train",
        dim=384,
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=False,
    )

    # Generate should work with NeuroLang enhancement
    result = wrapper.generate(
        prompt="Test prompt",
        moral_value=0.8,
        max_tokens=50,
    )

    assert result is not None
    assert "response" in result
    assert result["accepted"] is True
    assert result["neuro_enhancement"] != "NeuroLang disabled"
