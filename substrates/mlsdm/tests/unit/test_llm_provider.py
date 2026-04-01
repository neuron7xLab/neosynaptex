"""Tests for LLM provider abstraction module.

Tests cover:
- LLMProviderError and LLMTimeoutError exception classes
- LLMProvider abstract base class
- LocalStubProvider implementation
- OpenAIProvider initialization (without actual API calls)
- AnthropicProvider initialization (without actual API calls)
- Edge cases and error handling
"""

import contextlib
import sys
from collections.abc import Callable
from types import SimpleNamespace

import pytest

from mlsdm.adapters.llm_provider import (
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    LocalStubProvider,
)


def _install_module_stub(monkeypatch, name: str, client_attr: str) -> None:
    """Install a lightweight stub module so imports succeed deterministically."""

    class _DummyClient:
        def __init__(self, api_key: str | None = None) -> None:
            self.api_key = api_key

    stub = SimpleNamespace(
        **{
            client_attr: _DummyClient,
            "APITimeoutError": Exception,
            "APIConnectionError": Exception,
            "RateLimitError": Exception,
            "APIStatusError": type("APIStatusError", (Exception,), {"status_code": 0}),
        }
    )
    monkeypatch.setitem(sys.modules, name, stub)


class TestLLMProviderError:
    """Tests for LLMProviderError exception class."""

    def test_basic_error_creation(self):
        """Test creating a basic LLMProviderError."""
        error = LLMProviderError("Test error")
        assert str(error) == "Test error"
        assert error.provider_id is None
        assert error.original_error is None

    def test_error_with_provider_id(self):
        """Test LLMProviderError with provider_id."""
        error = LLMProviderError("Test error", provider_id="openai")
        assert str(error) == "Test error"
        assert error.provider_id == "openai"

    def test_error_with_original_exception(self):
        """Test LLMProviderError wrapping original exception."""
        original = ValueError("Original error")
        error = LLMProviderError(
            "Wrapped error",
            provider_id="test_provider",
            original_error=original,
        )
        assert error.original_error is original
        assert error.provider_id == "test_provider"

    def test_error_inheritance(self):
        """Test that LLMProviderError inherits from Exception."""
        error = LLMProviderError("Test")
        assert isinstance(error, Exception)


class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception class."""

    def test_basic_timeout_error(self):
        """Test creating a basic LLMTimeoutError."""
        error = LLMTimeoutError("Timeout occurred")
        assert str(error) == "Timeout occurred"
        assert error.timeout_seconds is None

    def test_timeout_error_with_seconds(self):
        """Test LLMTimeoutError with timeout_seconds."""
        error = LLMTimeoutError(
            "Request timed out",
            provider_id="openai",
            timeout_seconds=30.0,
        )
        assert error.timeout_seconds == 30.0
        assert error.provider_id == "openai"

    def test_timeout_error_inheritance(self):
        """Test that LLMTimeoutError inherits from LLMProviderError."""
        error = LLMTimeoutError("Test timeout")
        assert isinstance(error, LLMProviderError)
        assert isinstance(error, Exception)

    def test_timeout_error_with_original_exception(self):
        """Test LLMTimeoutError with original exception."""
        original = TimeoutError("Connection timeout")
        error = LLMTimeoutError(
            "API timeout",
            provider_id="anthropic",
            timeout_seconds=60.0,
            original_error=original,
        )
        assert error.original_error is original
        assert error.timeout_seconds == 60.0


class TestLLMProviderAbstract:
    """Tests for LLMProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """LLMProvider should not be directly instantiable."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            LLMProvider()  # type: ignore

    def test_provider_id_default(self):
        """Test that provider_id returns class name by default."""
        # Use LocalStubProvider which inherits from LLMProvider
        provider = LocalStubProvider()
        # LocalStubProvider overrides provider_id, so test base behavior via different means
        assert hasattr(provider, "provider_id")


class TestLocalStubProvider:
    """Tests for LocalStubProvider implementation."""

    def test_initialization_default(self):
        """Test LocalStubProvider with default provider_id."""
        provider = LocalStubProvider()
        assert provider.provider_id == "local_stub"

    def test_initialization_custom_id(self):
        """Test LocalStubProvider with custom provider_id."""
        provider = LocalStubProvider(provider_id="custom_stub")
        assert provider.provider_id == "custom_stub"

    def test_generate_basic_response(self):
        """Test generate returns expected stub response."""
        provider = LocalStubProvider()
        response = provider.generate("Hello world", max_tokens=50)

        assert isinstance(response, str)
        assert "NEURO-RESPONSE" in response
        assert "Hello world" in response

    def test_generate_truncates_long_prompts(self):
        """Test that long prompts are truncated in response."""
        provider = LocalStubProvider()
        long_prompt = "a" * 100  # 100 character prompt
        response = provider.generate(long_prompt, max_tokens=50)

        # Should contain truncated preview (first 50 chars)
        assert "a" * 50 in response

    def test_generate_extends_for_high_max_tokens(self):
        """Test that response extends for high max_tokens."""
        provider = LocalStubProvider()
        response = provider.generate("Test", max_tokens=100)

        # Should include extended message for max_tokens > 50
        assert "Generated with max_tokens=100" in response
        assert "stub response" in response

    def test_generate_respects_max_chars(self):
        """Test that response respects max character limit."""
        provider = LocalStubProvider()
        response = provider.generate("Test", max_tokens=10)

        # Should be limited to roughly max_tokens * 4 characters
        assert len(response) <= 10 * 4

    def test_generate_accepts_kwargs(self):
        """Test that generate accepts additional kwargs."""
        provider = LocalStubProvider()
        # Should not raise error with extra kwargs
        response = provider.generate(
            "Test",
            max_tokens=50,
            moral_value=0.8,
            user_intent="testing",
        )
        assert isinstance(response, str)

    def test_is_instance_of_llm_provider(self):
        """Test that LocalStubProvider is instance of LLMProvider."""
        provider = LocalStubProvider()
        assert isinstance(provider, LLMProvider)

    def test_deterministic_response(self):
        """Test that same input produces consistent output format."""
        provider = LocalStubProvider()

        response1 = provider.generate("Same prompt", max_tokens=30)
        response2 = provider.generate("Same prompt", max_tokens=30)

        # Should produce same response for same input
        assert response1 == response2


class TestOpenAIProviderInit:
    """Tests for OpenAIProvider initialization (without API calls)."""

    def test_raises_without_api_key(self, monkeypatch):
        """Should raise ValueError when API key is not provided."""
        # Ensure environment variable is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from mlsdm.adapters.llm_provider import OpenAIProvider

        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIProvider()

    def test_raises_import_error_without_openai(
        self,
        monkeypatch: pytest.MonkeyPatch,
        block_imports: Callable[[set[str]], contextlib.AbstractContextManager[None]],
    ):
        """Should raise ImportError when openai package is not installed."""

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        with block_imports({"openai"}), pytest.raises(ImportError, match="openai package is required"):
            OpenAIProvider(api_key="test-key")

    def test_accepts_api_key_parameter(self, monkeypatch):
        """Should accept API key via parameter."""
        # Ensure environment variable is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        _install_module_stub(monkeypatch, "openai", "OpenAI")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        # This should not raise
        provider = OpenAIProvider(api_key="test-api-key-12345")
        assert provider.api_key == "test-api-key-12345"

    def test_uses_environment_api_key(self, monkeypatch):
        """Should use OPENAI_API_KEY from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key-67890")

        _install_module_stub(monkeypatch, "openai", "OpenAI")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        provider = OpenAIProvider()
        assert provider.api_key == "env-api-key-67890"

    def test_default_model(self, monkeypatch):
        """Should use default model when not specified."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_MODEL", raising=False)

        _install_module_stub(monkeypatch, "openai", "OpenAI")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        provider = OpenAIProvider()
        assert provider.model == "gpt-3.5-turbo"

    def test_custom_model(self, monkeypatch):
        """Should accept custom model parameter."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        _install_module_stub(monkeypatch, "openai", "OpenAI")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        provider = OpenAIProvider(model="gpt-4")
        assert provider.model == "gpt-4"

    def test_provider_id_format(self, monkeypatch):
        """Provider ID should include formatted model name."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        _install_module_stub(monkeypatch, "openai", "OpenAI")

        from mlsdm.adapters.llm_provider import OpenAIProvider

        provider = OpenAIProvider(model="gpt-3.5-turbo")
        assert provider.provider_id == "openai_gpt_3_5_turbo"


class TestAnthropicProviderInit:
    """Tests for AnthropicProvider initialization (without API calls)."""

    def test_raises_without_api_key(self, monkeypatch):
        """Should raise ValueError when API key is not provided."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        from mlsdm.adapters.llm_provider import AnthropicProvider

        with pytest.raises(ValueError, match="Anthropic API key is required"):
            AnthropicProvider()

    def test_accepts_api_key_parameter(self, monkeypatch):
        """Should accept API key via parameter."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        _install_module_stub(monkeypatch, "anthropic", "Anthropic")

        from mlsdm.adapters.llm_provider import AnthropicProvider

        provider = AnthropicProvider(api_key="test-anthropic-key")
        assert provider.api_key == "test-anthropic-key"

    def test_uses_environment_api_key(self, monkeypatch):
        """Should use ANTHROPIC_API_KEY from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic-key")

        _install_module_stub(monkeypatch, "anthropic", "Anthropic")

        from mlsdm.adapters.llm_provider import AnthropicProvider

        provider = AnthropicProvider()
        assert provider.api_key == "env-anthropic-key"

    def test_default_model(self, monkeypatch):
        """Should use default model when not specified."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)

        _install_module_stub(monkeypatch, "anthropic", "Anthropic")

        from mlsdm.adapters.llm_provider import AnthropicProvider

        provider = AnthropicProvider()
        assert provider.model == "claude-3-sonnet-20240229"

    def test_custom_model(self, monkeypatch):
        """Should accept custom model parameter."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        _install_module_stub(monkeypatch, "anthropic", "Anthropic")

        from mlsdm.adapters.llm_provider import AnthropicProvider

        provider = AnthropicProvider(model="claude-3-opus-20240229")
        assert provider.model == "claude-3-opus-20240229"

    def test_provider_id_format(self, monkeypatch):
        """Provider ID should include formatted model name."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        _install_module_stub(monkeypatch, "anthropic", "Anthropic")

        from mlsdm.adapters.llm_provider import AnthropicProvider

        provider = AnthropicProvider(model="claude-3-sonnet-20240229")
        assert provider.provider_id == "anthropic_claude_3_sonnet_20240229"
