"""
Unit tests for NeuroCognitiveEngine.from_config() factory method.

Tests cover:
1. Loading from YAML configuration file
2. Configuration validation at startup
3. Default functions when not provided
4. Error handling for missing/invalid files
"""

import tempfile
from pathlib import Path

import pytest

from mlsdm.engine import NeuroCognitiveEngine


class TestFromConfig:
    """Tests for NeuroCognitiveEngine.from_config() factory method."""

    def test_from_config_with_default_config(self) -> None:
        """Test loading from default config file."""
        engine = NeuroCognitiveEngine.from_config("config/default_config.yaml")

        # Engine should be created successfully
        assert engine is not None
        assert engine.config is not None

    def test_from_config_with_production_config(self) -> None:
        """Test loading from production config file."""
        engine = NeuroCognitiveEngine.from_config("config/production.yaml")

        # Engine should be created with production settings
        assert engine is not None
        assert engine.config.dim == 384  # Production uses 384 dim

    def test_from_config_generates_response(self) -> None:
        """Test that engine created from config can generate responses."""
        engine = NeuroCognitiveEngine.from_config("config/default_config.yaml")

        result = engine.generate(prompt="Hello, world!", max_tokens=100)

        assert "response" in result
        assert result["error"] is None
        assert len(result["response"]) > 0

    def test_from_config_missing_file(self) -> None:
        """Test error handling for missing config file."""
        with pytest.raises(FileNotFoundError):
            NeuroCognitiveEngine.from_config("nonexistent_config.yaml")

    def test_from_config_invalid_yaml(self) -> None:
        """Test error handling for invalid YAML content."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: {{{}}")
            f.flush()

            with pytest.raises(ValueError):
                NeuroCognitiveEngine.from_config(f.name)

            Path(f.name).unlink()

    def test_from_config_invalid_config_values(self) -> None:
        """Test error handling for invalid configuration values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Invalid dimension value (too small)
            f.write("dimension: 1\n")
            f.flush()

            with pytest.raises(ValueError):
                NeuroCognitiveEngine.from_config(f.name)

            Path(f.name).unlink()

    def test_from_config_with_custom_llm_fn(self) -> None:
        """Test from_config with custom LLM function."""
        custom_response = "Custom LLM Response"

        def custom_llm(prompt: str, max_tokens: int) -> str:
            return custom_response

        engine = NeuroCognitiveEngine.from_config(
            "config/default_config.yaml",
            llm_generate_fn=custom_llm,
        )

        result = engine.generate(prompt="Test", max_tokens=50)

        assert custom_response in result["response"]

    def test_from_config_with_custom_embedding_fn(self) -> None:
        """Test from_config with custom embedding function."""
        import numpy as np

        def custom_embed(text: str) -> np.ndarray:
            # Return a fixed embedding
            return np.ones(10, dtype=np.float32)

        engine = NeuroCognitiveEngine.from_config(
            "config/default_config.yaml",
            embedding_fn=custom_embed,
        )

        # Should create engine successfully
        result = engine.generate(prompt="Test", max_tokens=50)
        assert result is not None

    def test_from_config_applies_config_values(self) -> None:
        """Test that config values are properly applied to engine."""
        engine = NeuroCognitiveEngine.from_config("config/production.yaml")

        # Check that config values are reflected
        assert engine.config.dim == 384
        assert engine.config.wake_duration == 8
        assert engine.config.sleep_duration == 3


class TestFromConfigValidation:
    """Tests for configuration validation in from_config."""

    def test_invalid_moral_threshold(self) -> None:
        """Test validation of moral threshold bounds."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Invalid threshold (too high)
            f.write("""
dimension: 10
moral_filter:
  threshold: 0.95
  min_threshold: 0.3
  max_threshold: 0.9
""")
            f.flush()

            with pytest.raises(ValueError):
                NeuroCognitiveEngine.from_config(f.name)

            Path(f.name).unlink()

    def test_valid_minimal_config(self) -> None:
        """Test that minimal valid config works."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Minimal valid config
            f.write("""
dimension: 10
multi_level_memory:
  lambda_l1: 0.5
  lambda_l2: 0.1
  lambda_l3: 0.01
  theta_l1: 1.0
  theta_l2: 2.0
  gating12: 0.5
  gating23: 0.3
moral_filter:
  threshold: 0.5
  min_threshold: 0.3
  max_threshold: 0.9
  adapt_rate: 0.05
cognitive_rhythm:
  wake_duration: 5
  sleep_duration: 2
ontology_matcher:
  ontology_vectors:
    - [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    - [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  ontology_labels: ["concept1", "concept2"]
strict_mode: false
""")
            f.flush()

            engine = NeuroCognitiveEngine.from_config(f.name)
            assert engine is not None

            Path(f.name).unlink()
