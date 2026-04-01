"""
Tests for NeuroLang performance modes.

This test suite validates the three operating modes of NeuroLangWrapper:
- eager_train: Trains at initialization
- lazy_train: Trains on first generation call
- disabled: Skips NeuroLang entirely (Aphasia-Broca only)
"""

import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from mlsdm.extensions import NeuroLangWrapper

# Skip all tests in this module if torch is not available
TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None
pytestmark = pytest.mark.skipif(
    not TORCH_AVAILABLE,
    reason="optional dependency 'torch' is not installed; skipping NeuroLang tests.",
)


def dummy_llm(prompt: str, max_tokens: int) -> str:
    """Dummy LLM for testing."""
    return "This is a coherent response with proper grammar and function words."


def dummy_embedder(text: str):
    """Generate deterministic embeddings based on text hash."""
    np.random.seed(hash(text) & 0xFFFFFFFF)
    vec = np.random.randn(384).astype(np.float32)
    return vec / np.linalg.norm(vec)


def test_neurolang_disabled_skips_training_and_grammar():
    """Test that disabled mode skips all NeuroLang components and training."""
    # Mock the trainer to ensure it's never called
    with patch("mlsdm.extensions.neuro_lang_extension.CriticalPeriodTrainer") as mock_trainer_class:
        mock_trainer_instance = MagicMock()
        mock_trainer_class.return_value = mock_trainer_instance

        # Create wrapper with disabled mode
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            neurolang_mode="disabled",
        )

        # Verify NeuroLang components are None
        assert wrapper.actor is None
        assert wrapper.critic is None
        assert wrapper.trainer is None
        assert wrapper.integrator is None
        assert wrapper.dataset is None

        # Verify trainer was never instantiated in disabled mode
        mock_trainer_class.assert_not_called()

        # Verify controller and aphasia detector are still initialized
        assert wrapper.controller is not None
        assert wrapper.aphasia_detector is not None

        # Generate should work without NeuroLang
        result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

        assert isinstance(result, dict)
        assert result["accepted"] is True
        assert "response" in result
        assert result["neuro_enhancement"] == "NeuroLang disabled"

        # Trainer.train() should never have been called
        mock_trainer_instance.train.assert_not_called()


def test_neurolang_eager_train_calls_trainer_once():
    """Test that eager_train mode trains exactly once at initialization."""
    train_call_count = 0

    def counting_train(self):
        nonlocal train_call_count
        train_call_count += 1

    # Patch the train method to count calls
    with patch("mlsdm.extensions.neuro_lang_extension.CriticalPeriodTrainer.train", counting_train):
        # Create wrapper with eager_train mode
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            neurolang_mode="eager_train",
        )

        # Verify training was called once during initialization
        assert train_call_count == 1

        # Multiple generate calls should not trigger more training
        for _ in range(3):
            result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)
            assert result["accepted"] is True

        # Training count should still be 1
        assert train_call_count == 1


def test_neurolang_lazy_train_trains_on_first_generate_only():
    """Test that lazy_train mode trains on first generate call only."""
    train_call_count = 0

    def counting_train(self):
        nonlocal train_call_count
        train_call_count += 1

    # Patch the train method to count calls
    with patch("mlsdm.extensions.neuro_lang_extension.CriticalPeriodTrainer.train", counting_train):
        # Create wrapper with lazy_train mode
        wrapper = NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            neurolang_mode="lazy_train",
        )

        # Verify training was NOT called during initialization
        assert train_call_count == 0

        # First generate should trigger training
        result1 = wrapper.generate(prompt="First prompt", moral_value=0.8, max_tokens=50)
        assert result1["accepted"] is True
        assert train_call_count == 1

        # Subsequent generates should not trigger more training
        for _ in range(3):
            result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)
            assert result["accepted"] is True

        # Training count should still be 1
        assert train_call_count == 1


def test_neurolang_uses_checkpoint_if_available():
    """Test that checkpoint is loaded and training is skipped when checkpoint exists."""
    # Import ALLOWED_CHECKPOINT_DIR to use the correct directory
    from mlsdm.extensions.neuro_lang_extension import ALLOWED_CHECKPOINT_DIR

    # Create a temporary checkpoint file in the allowed directory
    with tempfile.NamedTemporaryFile(
        suffix=".pt", dir=str(ALLOWED_CHECKPOINT_DIR), delete=False
    ) as tmp_file:
        checkpoint_path = tmp_file.name

    try:
        # Create a minimal checkpoint
        from mlsdm.extensions.neuro_lang_extension import (
            InnateGrammarModule,
            LanguageDataset,
            all_sentences,
        )

        dataset = LanguageDataset(all_sentences)
        vocab_size = len(dataset.vocab)
        actor = InnateGrammarModule(vocab_size)
        critic = InnateGrammarModule(vocab_size)

        checkpoint = {
            "actor": actor.state_dict(),
            "critic": critic.state_dict(),
        }
        import torch

        torch.save(checkpoint, checkpoint_path)

        train_call_count = 0

        def counting_train(self):
            nonlocal train_call_count
            train_call_count += 1

        # Patch the train method to count calls
        with patch(
            "mlsdm.extensions.neuro_lang_extension.CriticalPeriodTrainer.train", counting_train
        ):
            # Create wrapper with checkpoint
            wrapper = NeuroLangWrapper(
                llm_generate_fn=dummy_llm,
                embedding_fn=dummy_embedder,
                dim=384,
                neurolang_mode="eager_train",
                neurolang_checkpoint_path=checkpoint_path,
            )

            # Verify training was NOT called (checkpoint was loaded instead)
            assert train_call_count == 0

            # Generate should work fine
            result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)
            assert result["accepted"] is True

            # Training should still not have been called
            assert train_call_count == 0

    finally:
        # Clean up temp file
        Path(checkpoint_path).unlink(missing_ok=True)


def test_neurolang_invalid_mode_raises_error():
    """Test that invalid neurolang_mode raises ValueError."""
    with pytest.raises(ValueError, match="Invalid neurolang_mode"):
        NeuroLangWrapper(
            llm_generate_fn=dummy_llm,
            embedding_fn=dummy_embedder,
            dim=384,
            neurolang_mode="invalid_mode",
        )


def test_neurolang_disabled_preserves_aphasia_functionality():
    """Test that disabled mode still provides full Aphasia-Broca functionality."""

    def aphasic_llm(prompt: str, max_tokens: int) -> str:
        """LLM that produces aphasic output."""
        return "Bad. No. Short."

    wrapper = NeuroLangWrapper(
        llm_generate_fn=aphasic_llm,
        embedding_fn=dummy_embedder,
        dim=384,
        neurolang_mode="disabled",
        aphasia_detect_enabled=True,
        aphasia_repair_enabled=True,
    )

    result = wrapper.generate(prompt="Test prompt", moral_value=0.8, max_tokens=50)

    # Aphasia detection should still work
    assert result["accepted"] is True
    assert result["aphasia_flags"] is not None
    assert result["aphasia_flags"]["is_aphasic"] is True
    assert result["aphasia_flags"]["severity"] > 0.0


def test_neurolang_checkpoint_invalid_format_raises_error():
    """Test that loading an invalid checkpoint raises a clear error."""
    # Import ALLOWED_CHECKPOINT_DIR to use the correct directory
    from mlsdm.extensions.neuro_lang_extension import ALLOWED_CHECKPOINT_DIR

    # Create a checkpoint with wrong format in the allowed directory
    with tempfile.NamedTemporaryFile(
        suffix=".pt", dir=str(ALLOWED_CHECKPOINT_DIR), delete=False
    ) as tmp_file:
        checkpoint_path = tmp_file.name

    try:
        # Save invalid checkpoint (missing required keys)
        invalid_checkpoint = {"wrong_key": "wrong_value"}
        import torch

        torch.save(invalid_checkpoint, checkpoint_path)

        # Should raise clear error about missing keys
        with pytest.raises(
            ValueError, match="Invalid checkpoint structure.*missing 'actor' or 'critic'"
        ):
            NeuroLangWrapper(
                llm_generate_fn=dummy_llm,
                embedding_fn=dummy_embedder,
                dim=384,
                neurolang_mode="eager_train",
                neurolang_checkpoint_path=checkpoint_path,
            )
    finally:
        Path(checkpoint_path).unlink(missing_ok=True)


def test_neurolang_checkpoint_corrupted_raises_error():
    """Test that loading a corrupted checkpoint raises a clear error."""
    # Create a corrupted file
    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp_file:
        checkpoint_path = tmp_file.name
        tmp_file.write(b"corrupted data that is not a valid torch checkpoint")

    try:
        # Should raise clear error about loading failure
        with pytest.raises(ValueError, match="Failed to load NeuroLang checkpoint"):
            NeuroLangWrapper(
                llm_generate_fn=dummy_llm,
                embedding_fn=dummy_embedder,
                dim=384,
                neurolang_mode="eager_train",
                neurolang_checkpoint_path=checkpoint_path,
            )
    finally:
        Path(checkpoint_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
