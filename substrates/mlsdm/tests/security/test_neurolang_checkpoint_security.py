"""
Security tests for NeuroLang checkpoint loading.

This test suite validates that checkpoint loading is restricted to allowed directories
and properly validates checkpoint structure to prevent loading malicious files.

Requires PyTorch (torch). Tests are skipped if torch is not installed.
"""

import tempfile
from pathlib import Path

import pytest

# Skip all tests in this module if torch is not available
pytest.importorskip("torch")

from mlsdm.extensions.neuro_lang_extension import (  # noqa: E402
    ALLOWED_CHECKPOINT_DIR,
    safe_load_neurolang_checkpoint,
)


@pytest.mark.security
def test_checkpoint_outside_allowed_dir_is_rejected():
    """Test that checkpoints outside ALLOWED_CHECKPOINT_DIR are rejected."""
    import torch

    device = torch.device("cpu")

    # Try loading from /tmp (outside config/)
    with pytest.raises(ValueError) as exc_info:
        safe_load_neurolang_checkpoint("/tmp/evil.pt", device)

    assert "Refusing to load checkpoint outside" in str(exc_info.value)
    assert str(ALLOWED_CHECKPOINT_DIR) in str(exc_info.value)


@pytest.mark.security
def test_nonexistent_checkpoint_raises_file_not_found():
    """Test that attempting to load a non-existent checkpoint raises FileNotFoundError."""
    import torch

    device = torch.device("cpu")

    # Create a path within config/ that doesn't exist
    nonexistent_path = str(ALLOWED_CHECKPOINT_DIR / "nonexistent_checkpoint.pt")

    with pytest.raises(FileNotFoundError) as exc_info:
        safe_load_neurolang_checkpoint(nonexistent_path, device)

    assert "Checkpoint not found" in str(exc_info.value)


@pytest.mark.security
def test_invalid_checkpoint_structure_raises_value_error():
    """Test that checkpoints with invalid structure are rejected."""
    import torch

    device = torch.device("cpu")

    # Create a temporary checkpoint file with invalid structure
    with tempfile.NamedTemporaryFile(
        suffix=".pt", dir=str(ALLOWED_CHECKPOINT_DIR), delete=False
    ) as tmp_file:
        temp_path = Path(tmp_file.name)

        try:
            # Test 1: Non-dict checkpoint (list instead)
            torch.save(["invalid", "structure"], temp_path)
            with pytest.raises(ValueError) as exc_info:
                safe_load_neurolang_checkpoint(str(temp_path), device)
            assert "Invalid neurolang checkpoint format: expected dict" in str(exc_info.value)

            # Test 2: Dict but missing required keys
            torch.save({"wrong_key": "value"}, temp_path)
            with pytest.raises(ValueError) as exc_info:
                safe_load_neurolang_checkpoint(str(temp_path), device)
            assert "Invalid checkpoint structure: missing 'actor' or 'critic' keys" in str(
                exc_info.value
            )

            # Test 3: Dict with only 'actor' key
            torch.save({"actor": {}}, temp_path)
            with pytest.raises(ValueError) as exc_info:
                safe_load_neurolang_checkpoint(str(temp_path), device)
            assert "Invalid checkpoint structure: missing 'actor' or 'critic' keys" in str(
                exc_info.value
            )

        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()


@pytest.mark.security
def test_valid_checkpoint_loads_successfully():
    """Test that a valid checkpoint within allowed directory loads successfully."""
    import torch

    device = torch.device("cpu")

    # Create a temporary valid checkpoint
    with tempfile.NamedTemporaryFile(
        suffix=".pt", dir=str(ALLOWED_CHECKPOINT_DIR), delete=False
    ) as tmp_file:
        temp_path = Path(tmp_file.name)

        try:
            # Create valid checkpoint structure
            valid_checkpoint = {
                "actor": {"dummy_param": torch.tensor([1.0, 2.0])},
                "critic": {"dummy_param": torch.tensor([3.0, 4.0])},
            }
            torch.save(valid_checkpoint, temp_path)

            # Should load without error
            result = safe_load_neurolang_checkpoint(str(temp_path), device)

            assert result is not None
            assert isinstance(result, dict)
            assert "actor" in result
            assert "critic" in result

        finally:
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()


@pytest.mark.security
def test_none_checkpoint_path_returns_none():
    """Test that passing None as checkpoint path returns None without error."""
    import torch

    device = torch.device("cpu")
    result = safe_load_neurolang_checkpoint(None, device)
    assert result is None
