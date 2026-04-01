"""
Adapter Tests for LLM Providers.

Tests cover:
- LocalStubAdapter unit tests
- OpenAIAdapter contract tests with mocks
- Error handling for all adapters
- Typing and interface compliance
"""

import os
from unittest.mock import MagicMock

import pytest

from mlsdm.adapters import (
    AnthropicProvider,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
    LocalStubProvider,
    OpenAIProvider,
    build_anthropic_llm_adapter,
    build_local_stub_llm_adapter,
    build_openai_llm_adapter,
    build_provider_from_env,
)


class TestLocalStubAdapter:
    """Unit tests for LocalStubAdapter."""

    def test_build_local_stub_returns_callable(self):
        """Test that build_local_stub_llm_adapter returns callable."""
        adapter = build_local_stub_llm_adapter()
        assert callable(adapter)

    def test_adapter_returns_string(self):
        """Test that adapter returns string response."""
        adapter = build_local_stub_llm_adapter()
        result = adapter("Test prompt", 100)
        assert isinstance(result, str)

    def test_adapter_includes_prompt_preview(self):
        """Test that response includes prompt preview."""
        adapter = build_local_stub_llm_adapter()
        result = adapter("Hello world", 100)
        assert "NEURO-RESPONSE" in result
        assert "Hello world" in result

    def test_adapter_truncates_long_prompts(self):
        """Test that adapter truncates prompts longer than 50 chars."""
        adapter = build_local_stub_llm_adapter()
        long_prompt = "A" * 100
        result = adapter(long_prompt, 100)
        # Should only include first 50 chars of prompt
        assert "A" * 50 in result
        assert "A" * 100 not in result

    def test_adapter_extends_response_for_large_max_tokens(self):
        """Test that adapter extends response for large max_tokens."""
        adapter = build_local_stub_llm_adapter()

        short_result = adapter("Test", 10)
        long_result = adapter("Test", 500)

        # Longer max_tokens should produce longer response
        assert len(long_result) > len(short_result)

    def test_adapter_respects_max_chars_limit(self):
        """Test that adapter respects max character limit."""
        adapter = build_local_stub_llm_adapter()
        result = adapter("Test", 10)

        # 10 tokens * 4 chars = 40 max chars
        assert len(result) <= 40

    def test_adapter_handles_empty_prompt(self):
        """Test that adapter handles empty prompt."""
        adapter = build_local_stub_llm_adapter()
        result = adapter("", 100)
        assert isinstance(result, str)
        assert "NEURO-RESPONSE" in result

    def test_adapter_deterministic_output(self):
        """Test that adapter returns deterministic output for same input."""
        adapter = build_local_stub_llm_adapter()
        result1 = adapter("Test prompt", 100)
        result2 = adapter("Test prompt", 100)
        assert result1 == result2


class TestLocalStubProvider:
    """Unit tests for LocalStubProvider class."""

    def test_provider_inherits_llm_provider(self):
        """Test that LocalStubProvider inherits from LLMProvider."""
        provider = LocalStubProvider()
        assert isinstance(provider, LLMProvider)

    def test_provider_generate_returns_string(self):
        """Test that generate returns string."""
        provider = LocalStubProvider()
        result = provider.generate("Test", 100)
        assert isinstance(result, str)

    def test_provider_id_default(self):
        """Test that default provider_id is 'local_stub'."""
        provider = LocalStubProvider()
        assert provider.provider_id == "local_stub"

    def test_provider_id_custom(self):
        """Test that custom provider_id is respected."""
        provider = LocalStubProvider(provider_id="custom_stub")
        assert provider.provider_id == "custom_stub"

    def test_provider_accepts_kwargs(self):
        """Test that provider accepts and ignores extra kwargs."""
        provider = LocalStubProvider()
        # Should not raise even with extra kwargs
        result = provider.generate("Test", 100, moral_value=0.5, user_intent="test")
        assert isinstance(result, str)

    def test_provider_response_format(self):
        """Test that provider response has expected format."""
        provider = LocalStubProvider()
        result = provider.generate("Hello", 100)
        assert "NEURO-RESPONSE" in result
        assert "Hello" in result


class TestOpenAIAdapterContract:
    """Contract tests for OpenAI adapter with mocks."""

    def test_build_openai_requires_api_key(self):
        """Test that build_openai_llm_adapter requires API key."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            build_openai_llm_adapter()

    def test_openai_provider_requires_api_key(self):
        """Test that OpenAIProvider requires API key."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(ValueError, match="api_key"):
            OpenAIProvider()

    def test_openai_adapter_with_mock_client(self):
        """Test that OpenAI adapter makes correct API call (with mock)."""
        import sys

        # Create a mock openai module
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response

        # Temporarily replace openai in sys.modules
        original_openai = sys.modules.get("openai")
        sys.modules["openai"] = mock_openai

        try:
            os.environ["OPENAI_API_KEY"] = "sk-test-key"

            # Need to reimport to pick up the mock
            import importlib

            import mlsdm.adapters.openai_adapter as oa_module

            importlib.reload(oa_module)

            adapter = oa_module.build_openai_llm_adapter()
            result = adapter("Test prompt", 100)

            # Verify API was called
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["messages"][0]["content"] == "Test prompt"
            assert call_kwargs["max_tokens"] == 100
            assert result == "Test response"
        finally:
            # Restore original
            if original_openai:
                sys.modules["openai"] = original_openai
            else:
                del sys.modules["openai"]

    def test_openai_provider_id_format(self):
        """Test that OpenAI provider_id format is correct (with mock)."""
        import sys

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = MagicMock()

        original_openai = sys.modules.get("openai")
        sys.modules["openai"] = mock_openai

        try:
            os.environ["OPENAI_API_KEY"] = "sk-test-key"

            import importlib

            import mlsdm.adapters.llm_provider as lp_module

            importlib.reload(lp_module)

            provider = lp_module.OpenAIProvider(api_key="sk-test-key", model="gpt-4")
            # Provider ID should contain the model name (sanitized)
            assert "openai" in provider.provider_id
            assert "gpt" in provider.provider_id
        finally:
            if original_openai:
                sys.modules["openai"] = original_openai
            else:
                del sys.modules["openai"]
ANTHROPIC_TEST_MODEL = "claude-3-sonnet-20240229"


class TestAnthropicAdapterContract:
    """Contract tests for Anthropic adapter with mocks."""

    def test_build_anthropic_requires_api_key(self):
        """Test that build_anthropic_llm_adapter requires API key."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            build_anthropic_llm_adapter()

    def test_anthropic_provider_requires_api_key(self):
        """Test that AnthropicProvider requires API key."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with pytest.raises(ValueError, match="api_key"):
            AnthropicProvider()

    def test_anthropic_adapter_with_mock_client(self):
        """Test that Anthropic adapter makes correct API call (with mock)."""
        import sys

        # Create a mock anthropic module
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Test response"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        # Temporarily replace anthropic in sys.modules
        original_anthropic = sys.modules.get("anthropic")
        sys.modules["anthropic"] = mock_anthropic

        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

            # Need to reimport to pick up the mock
            import importlib

            import mlsdm.adapters.anthropic_adapter as aa_module

            importlib.reload(aa_module)

            adapter = aa_module.build_anthropic_llm_adapter()
            result = adapter("Test prompt", 100)

            # Verify API was called
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["messages"][0]["content"] == "Test prompt"
            assert call_kwargs["max_tokens"] == 100
            assert result == "Test response"
        finally:
            # Restore original
            if original_anthropic:
                sys.modules["anthropic"] = original_anthropic
            else:
                del sys.modules["anthropic"]

    def test_anthropic_provider_id_format(self):
        """Test that Anthropic provider_id format is correct (with mock)."""
        import sys

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = MagicMock()

        original_anthropic = sys.modules.get("anthropic")
        sys.modules["anthropic"] = mock_anthropic

        try:
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"

            import importlib

            import mlsdm.adapters.llm_provider as lp_module

            importlib.reload(lp_module)

            provider = lp_module.AnthropicProvider(api_key="sk-ant-test-key", model=ANTHROPIC_TEST_MODEL)
            # Provider ID should contain anthropic and model name (sanitized)
            assert "anthropic" in provider.provider_id
            assert "claude" in provider.provider_id
        finally:
            if original_anthropic:
                sys.modules["anthropic"] = original_anthropic
            else:
                del sys.modules["anthropic"]


class TestProviderFactory:
    """Test provider factory functions."""

    def test_build_local_stub_from_env(self):
        """Test building local_stub from env."""
        os.environ["LLM_BACKEND"] = "local_stub"
        provider = build_provider_from_env()
        assert isinstance(provider, LocalStubProvider)

    def test_build_with_explicit_backend(self):
        """Test building with explicit backend parameter."""
        provider = build_provider_from_env(backend="local_stub")
        assert isinstance(provider, LocalStubProvider)

    def test_invalid_backend_raises_error(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Invalid LLM_BACKEND"):
            build_provider_from_env(backend="invalid")

    def test_backend_case_insensitive(self):
        """Test that backend is case-insensitive."""
        provider = build_provider_from_env(backend="LOCAL_STUB")
        assert isinstance(provider, LocalStubProvider)

    def test_custom_provider_id_for_stub(self):
        """Test custom provider_id for local stub."""
        provider = build_provider_from_env(backend="local_stub", provider_id="custom_id")
        assert provider.provider_id == "custom_id"


class TestAdapterTyping:
    """Test that adapters have proper typing."""

    def test_local_stub_adapter_signature(self):
        """Test local stub adapter has correct signature."""
        adapter = build_local_stub_llm_adapter()

        # Should accept (str, int) -> str
        import inspect

        sig = inspect.signature(adapter)
        params = list(sig.parameters.keys())
        assert "prompt" in params
        assert "max_tokens" in params

    def test_local_stub_provider_method_typing(self):
        """Test LocalStubProvider.generate has correct typing."""
        provider = LocalStubProvider()

        import inspect

        sig = inspect.signature(provider.generate)
        params = sig.parameters

        # Required positional params
        assert "prompt" in params
        assert "max_tokens" in params
        # kwargs for extension
        assert "kwargs" in params

    def test_llm_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated."""
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore


class TestLLMProviderErrors:
    """Test LLM provider error classes."""

    def test_llm_provider_error_attributes(self):
        """Test LLMProviderError has expected attributes."""
        error = LLMProviderError(
            "Test error",
            provider_id="test_provider",
            original_error=ValueError("Original"),
        )

        assert str(error) == "Test error"
        assert error.provider_id == "test_provider"
        assert isinstance(error.original_error, ValueError)

    def test_llm_timeout_error_extends_provider_error(self):
        """Test LLMTimeoutError extends LLMProviderError."""
        error = LLMTimeoutError(
            "Timeout occurred",
            provider_id="test",
            timeout_seconds=30.0,
        )

        assert isinstance(error, LLMProviderError)
        assert error.timeout_seconds == 30.0

    def test_error_without_optional_fields(self):
        """Test errors work without optional fields."""
        error = LLMProviderError("Simple error")
        assert error.provider_id is None
        assert error.original_error is None


class TestAdapterStableBehavior:
    """Test adapter stable behavior on LLM provider errors."""

    def test_local_stub_never_raises_provider_error(self):
        """Test that LocalStubProvider never raises LLM errors."""
        provider = LocalStubProvider()

        # Should handle any input without raising
        for prompt in ["", "test", "a" * 10000]:
            for max_tokens in [1, 100, 4096]:
                result = provider.generate(prompt, max_tokens)
                assert isinstance(result, str)

    def test_local_stub_stable_on_special_chars(self):
        """Test local stub handles special characters."""
        provider = LocalStubProvider()

        special_prompts = [
            "Hello\nWorld",
            "Tab\tSeparated",
            "Unicode: 日本語",
            "Emoji: 🔥🎉",
            "Quotes: \"test\" and 'test'",
        ]

        for prompt in special_prompts:
            result = provider.generate(prompt, 100)
            assert isinstance(result, str)
            assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
