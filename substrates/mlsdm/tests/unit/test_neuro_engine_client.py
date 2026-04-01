"""
Unit tests for NeuroCognitiveClient SDK.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from mlsdm.engine import NeuroEngineConfig
from mlsdm.sdk import NeuroCognitiveClient


class TestNeuroCognitiveClientInit:
    """Test NeuroCognitiveClient initialization."""

    def test_client_with_local_stub_backend(self):
        """Test initialization with local_stub backend (default)."""
        client = NeuroCognitiveClient()
        assert client.backend == "local_stub"
        assert client.config is None

    def test_client_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = NeuroEngineConfig(dim=512, enable_fslgs=False)
        client = NeuroCognitiveClient(backend="local_stub", config=config)
        assert client.config == config
        assert client.config.dim == 512
        assert client.config.enable_fslgs is False

    def test_client_with_openai_backend_and_api_key(self):
        """Test initialization with OpenAI backend and API key (mocked)."""
        # Clean up any existing env vars
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        # Mock the factory to bypass OpenAI adapter creation
        with patch("mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env") as mock_factory:
            mock_engine = MagicMock()
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient(
                backend="openai", api_key="sk-test-key-12345", model="gpt-4"
            )
            assert client.backend == "openai"
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key-12345"
            assert os.environ.get("OPENAI_MODEL") == "gpt-4"

    def test_client_with_openai_backend_from_env(self):
        """Test OpenAI backend using environment variable (mocked)."""
        os.environ["OPENAI_API_KEY"] = "sk-env-key"

        # Mock the factory
        with patch("mlsdm.sdk.neuro_engine_client.build_neuro_engine_from_env") as mock_factory:
            mock_engine = MagicMock()
            mock_factory.return_value = mock_engine

            client = NeuroCognitiveClient(backend="openai")
            assert client.backend == "openai"

    def test_client_with_openai_backend_missing_api_key(self):
        """Test that OpenAI backend requires API key."""
        # Clean up any existing env vars
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(ValueError, match="OpenAI backend requires api_key"):
            NeuroCognitiveClient(backend="openai")

    def test_client_with_invalid_backend(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Invalid backend"):
            NeuroCognitiveClient(backend="invalid_backend")  # type: ignore


class TestNeuroCognitiveClientGenerate:
    """Test NeuroCognitiveClient generate method."""

    def test_generate_uses_local_stub_by_default(self):
        """Test that client uses local_stub backend by default."""
        client = NeuroCognitiveClient()
        result = client.generate("Test prompt")

        # Verify response structure
        assert "response" in result
        assert "timing" in result
        assert "validation_steps" in result
        assert isinstance(result["response"], str)

    def test_generate_propagates_parameters_to_engine(self):
        """Test that generate parameters are passed to engine."""
        client = NeuroCognitiveClient()

        # Mock the engine to verify parameters
        with patch.object(client._engine, "generate") as mock_generate:
            mock_generate.return_value = {
                "response": "test",
                "timing": {},
                "validation_steps": [],
                "error": None,
                "rejected_at": None,
            }

            client.generate(
                prompt="Test",
                max_tokens=256,
                moral_value=0.8,
                user_intent="test_intent",
                cognitive_load=0.3,
                context_top_k=10,
            )

            # Verify engine was called with correct parameters
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args[1]
            assert call_kwargs["prompt"] == "Test"
            assert call_kwargs["max_tokens"] == 256
            assert call_kwargs["moral_value"] == 0.8
            assert call_kwargs["user_intent"] == "test_intent"
            assert call_kwargs["cognitive_load"] == 0.3
            assert call_kwargs["context_top_k"] == 10

    def test_generate_with_minimal_parameters(self):
        """Test generate with only required parameters."""
        client = NeuroCognitiveClient()
        result = client.generate("Minimal test prompt")

        assert "response" in result
        assert isinstance(result["response"], str)
        assert result["response"]  # Non-empty response

    def test_generate_returns_complete_structure(self):
        """Test that generate returns all expected fields."""
        client = NeuroCognitiveClient()
        result = client.generate("Complete structure test")

        # Check all expected fields are present
        expected_fields = [
            "response",
            "governance",
            "mlsdm",
            "timing",
            "validation_steps",
            "error",
            "rejected_at",
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


class TestNeuroCognitiveClientProperties:
    """Test NeuroCognitiveClient properties."""

    def test_backend_property(self):
        """Test backend property getter."""
        client = NeuroCognitiveClient(backend="local_stub")
        assert client.backend == "local_stub"

    def test_config_property_with_none(self):
        """Test config property when no config provided."""
        client = NeuroCognitiveClient()
        assert client.config is None

    def test_config_property_with_custom_config(self):
        """Test config property with custom configuration."""
        config = NeuroEngineConfig(dim=256, capacity=10000)
        client = NeuroCognitiveClient(config=config)
        assert client.config is config
        assert client.config.dim == 256
        assert client.config.capacity == 10000
