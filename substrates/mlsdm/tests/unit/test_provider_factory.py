"""
Unit tests for LLM provider factory.

Tests cover:
1. build_provider_from_env with different backends
2. build_multiple_providers_from_env configurations
3. Error handling for invalid backends
4. Environment variable handling
"""

import contextlib
import os
import sys
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from mlsdm.adapters import (
    LLMProviderError,
    LocalStubProvider,
    build_multiple_providers_from_env,
    build_provider_from_env,
)


def _install_module_stub(monkeypatch: pytest.MonkeyPatch, name: str, client_attr: str) -> None:
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


class TestBuildProviderFromEnv:
    """Tests for build_provider_from_env factory function."""

    def test_default_is_local_stub(self) -> None:
        """Test that default backend is local_stub."""
        with patch.dict(os.environ, {}, clear=True):
            provider = build_provider_from_env()
            assert isinstance(provider, LocalStubProvider)
            assert provider.provider_id == "local_stub"

    def test_explicit_local_stub(self) -> None:
        """Test explicit local_stub backend."""
        provider = build_provider_from_env(backend="local_stub")
        assert isinstance(provider, LocalStubProvider)

    def test_local_stub_with_custom_id(self) -> None:
        """Test local_stub with custom provider_id."""
        with patch.dict(os.environ, {"LOCAL_STUB_PROVIDER_ID": "my_stub"}):
            provider = build_provider_from_env(backend="local_stub")
            assert provider.provider_id == "my_stub"

    def test_local_stub_from_env(self) -> None:
        """Test local_stub backend from environment variable."""
        with patch.dict(os.environ, {"LLM_BACKEND": "local_stub"}):
            provider = build_provider_from_env()
            assert isinstance(provider, LocalStubProvider)

    def test_invalid_backend_raises_error(self) -> None:
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            build_provider_from_env(backend="invalid_backend")

        assert "Invalid LLM_BACKEND" in str(exc_info.value)
        assert "invalid_backend" in str(exc_info.value)

    def test_invalid_backend_from_env_raises_error(self) -> None:
        """Test that invalid backend from env raises ValueError."""
        with patch.dict(os.environ, {"LLM_BACKEND": "unknown_provider"}):
            with pytest.raises(ValueError) as exc_info:
                build_provider_from_env()

            assert "Invalid LLM_BACKEND" in str(exc_info.value)

    def test_backend_case_insensitive(self) -> None:
        """Test that backend names are case-insensitive."""
        provider_lower = build_provider_from_env(backend="local_stub")
        provider_upper = build_provider_from_env(backend="LOCAL_STUB")
        provider_mixed = build_provider_from_env(backend="Local_Stub")

        assert isinstance(provider_lower, LocalStubProvider)
        assert isinstance(provider_upper, LocalStubProvider)
        assert isinstance(provider_mixed, LocalStubProvider)

    def test_backend_with_whitespace(self) -> None:
        """Test that backend name handles whitespace."""
        provider = build_provider_from_env(backend="  local_stub  ")
        assert isinstance(provider, LocalStubProvider)

    def test_openai_without_api_key_raises_error(self) -> None:
        """Test that openai without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing OPENAI_API_KEY
            env = dict(os.environ)
            env.pop("OPENAI_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    build_provider_from_env(backend="openai")

                assert "API key" in str(exc_info.value)

    def test_anthropic_without_api_key_raises_error(self) -> None:
        """Test that anthropic without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing ANTHROPIC_API_KEY
            env = dict(os.environ)
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    build_provider_from_env(backend="anthropic")

                assert "API key" in str(exc_info.value)


class TestBuildMultipleProvidersFromEnv:
    """Tests for build_multiple_providers_from_env function."""

    def test_empty_env_returns_default_stub(self) -> None:
        """Test that empty MULTI_LLM_BACKENDS returns default local_stub."""
        with patch.dict(os.environ, {"MULTI_LLM_BACKENDS": ""}, clear=True):
            providers = build_multiple_providers_from_env()
            assert "default" in providers
            assert isinstance(providers["default"], LocalStubProvider)

    def test_single_backend_named(self) -> None:
        """Test single backend with custom name."""
        with patch.dict(os.environ, {"MULTI_LLM_BACKENDS": "myname:local_stub"}):
            providers = build_multiple_providers_from_env()
            assert "myname" in providers
            assert isinstance(providers["myname"], LocalStubProvider)

    def test_single_backend_unnamed(self) -> None:
        """Test single backend without custom name."""
        with patch.dict(os.environ, {"MULTI_LLM_BACKENDS": "local_stub"}):
            providers = build_multiple_providers_from_env()
            assert "local_stub" in providers
            assert isinstance(providers["local_stub"], LocalStubProvider)

    def test_multiple_backends(self) -> None:
        """Test multiple backends configuration."""
        with patch.dict(
            os.environ, {"MULTI_LLM_BACKENDS": "control:local_stub,treatment:local_stub"}
        ):
            providers = build_multiple_providers_from_env()
            assert "control" in providers
            assert "treatment" in providers
            assert isinstance(providers["control"], LocalStubProvider)
            assert isinstance(providers["treatment"], LocalStubProvider)

    def test_multiple_backends_with_spaces(self) -> None:
        """Test multiple backends with spaces in config."""
        with patch.dict(
            os.environ, {"MULTI_LLM_BACKENDS": " control : local_stub , treatment : local_stub "}
        ):
            providers = build_multiple_providers_from_env()
            assert "control" in providers
            assert "treatment" in providers

    def test_failed_provider_continues(self) -> None:
        """Test that failed provider doesn't break other providers."""
        with patch.dict(os.environ, {"MULTI_LLM_BACKENDS": "good:local_stub,bad:invalid_provider"}):
            # Should emit a warning but continue
            import warnings

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                providers = build_multiple_providers_from_env()

                # Should have the good provider
                assert "good" in providers
                assert isinstance(providers["good"], LocalStubProvider)

                # Should have warning about bad provider
                assert len(w) > 0

    def test_all_providers_fail_fallback_to_stub(self) -> None:
        """Test that if all providers fail, fallback to local_stub."""
        with patch.dict(os.environ, {"MULTI_LLM_BACKENDS": "bad1:invalid1,bad2:invalid2"}):
            import warnings

            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                providers = build_multiple_providers_from_env()

                # Should fallback to default
                assert "default" in providers
                assert isinstance(providers["default"], LocalStubProvider)


class TestProviderContract:
    """Tests for LLM provider contract compliance."""

    def test_local_stub_implements_protocol(self) -> None:
        """Test LocalStubProvider implements LLMProvider protocol."""
        provider = LocalStubProvider()

        # Check required method exists
        assert hasattr(provider, "generate")
        assert callable(provider.generate)

        # Check property exists
        assert hasattr(provider, "provider_id")

        # Test generate returns string
        result = provider.generate("test", 100)
        assert isinstance(result, str)

    def test_provider_generate_with_kwargs(self) -> None:
        """Test that provider.generate accepts kwargs."""
        provider = LocalStubProvider()

        # Should not raise
        result = provider.generate(
            "test prompt", 100, moral_value=0.5, user_intent="test", custom_param="value"
        )
        assert isinstance(result, str)

    def test_provider_id_is_string(self) -> None:
        """Test that provider_id is a string."""
        provider = LocalStubProvider()
        assert isinstance(provider.provider_id, str)
        assert len(provider.provider_id) > 0


class TestBuildProviderFromEnvWithOpenAI:
    """Tests for OpenAI provider creation (with mocked API key)."""

    def test_openai_with_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test OpenAI provider creation with API key from env."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            _install_module_stub(monkeypatch, "openai", "OpenAI")
            provider = build_provider_from_env(backend="openai")
            assert provider.provider_id.startswith("openai_")

    def test_openai_with_custom_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test OpenAI provider with custom model from env."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123", "OPENAI_MODEL": "gpt-4"}):
            _install_module_stub(monkeypatch, "openai", "OpenAI")
            provider = build_provider_from_env(backend="openai")
            assert "gpt_4" in provider.provider_id

    def test_openai_missing_dependency_raises_import_error(
        self,
        block_imports: Callable[[set[str]], contextlib.AbstractContextManager[None]],
    ) -> None:
        """Ensure missing openai dependency fails deterministically."""
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}),
            block_imports({"openai"}),
            pytest.raises(ImportError, match="openai package is required"),
        ):
            build_provider_from_env(backend="openai")


class TestProviderErrorHandling:
    """Tests for provider error handling patterns."""

    def test_provider_error_has_provider_id(self) -> None:
        """Test that LLMProviderError includes provider_id."""
        error = LLMProviderError("Test error", provider_id="test_provider")
        assert error.provider_id == "test_provider"

    def test_provider_error_chain_preserves_original(self) -> None:
        """Test that error chain preserves original exception."""
        original = ValueError("Original error")
        error = LLMProviderError("Wrapped error", original_error=original)
        assert error.original_error is original
