"""Tests for OIDC authentication module (SEC-004).

Tests the OIDC functionality including:
- OIDCConfig creation and validation
- OIDCConfig.from_env() loading
- UserInfo dataclass
- JWKSCache behavior
- OIDCAuthenticator creation
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mlsdm.security.oidc import (
    JWKSCache,
    OIDCAuthenticator,
    OIDCConfig,
    UserInfo,
)


class TestOIDCConfig:
    """Tests for OIDCConfig dataclass."""

    def test_default_values(self) -> None:
        """Test OIDCConfig default values."""
        config = OIDCConfig()
        assert config.enabled is False
        assert config.issuer == ""
        assert config.audience == ""
        assert config.jwks_uri is None
        assert config.roles_claim == "roles"
        assert config.algorithms == ["RS256"]
        assert config.cache_ttl == 3600

    def test_custom_values(self) -> None:
        """Test OIDCConfig with custom values."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            roles_claim="custom_roles",
            algorithms=["RS256", "RS384"],
            cache_ttl=7200,
        )
        assert config.enabled is True
        assert config.issuer == "https://auth.example.com/"
        assert config.audience == "my-api"
        assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert config.roles_claim == "custom_roles"
        assert config.algorithms == ["RS256", "RS384"]
        assert config.cache_ttl == 7200

    def test_from_env_defaults(self) -> None:
        """Test OIDCConfig.from_env() with default values."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any MLSDM_OIDC_* env vars
            env = {k: v for k, v in os.environ.items() if not k.startswith("MLSDM_OIDC")}
            with patch.dict(os.environ, env, clear=True):
                config = OIDCConfig.from_env()
                assert config.enabled is False
                assert config.issuer == ""
                assert config.audience == ""
                assert config.roles_claim == "roles"
                assert config.algorithms == ["RS256"]

    def test_from_env_enabled(self) -> None:
        """Test OIDCConfig.from_env() with OIDC enabled."""
        env = {
            "MLSDM_OIDC_ENABLED": "true",
            "MLSDM_OIDC_ISSUER": "https://auth0.example.com/",
            "MLSDM_OIDC_AUDIENCE": "my-api",
            "MLSDM_OIDC_ROLES_CLAIM": "permissions",
            "MLSDM_OIDC_ALGORITHMS": "RS256, RS384",
            "MLSDM_OIDC_CACHE_TTL": "1800",
        }
        with patch.dict(os.environ, env, clear=False):
            config = OIDCConfig.from_env()
            assert config.enabled is True
            assert config.issuer == "https://auth0.example.com/"
            assert config.audience == "my-api"
            assert config.roles_claim == "permissions"
            assert config.algorithms == ["RS256", "RS384"]
            assert config.cache_ttl == 1800

    def test_validate_disabled(self) -> None:
        """Test validation passes when OIDC is disabled."""
        config = OIDCConfig(enabled=False)
        config.validate()  # Should not raise

    def test_validate_enabled_missing_issuer(self) -> None:
        """Test validation fails when enabled without issuer."""
        config = OIDCConfig(enabled=True, audience="my-api")
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "MLSDM_OIDC_ISSUER is required" in str(exc_info.value)

    def test_validate_enabled_missing_audience(self) -> None:
        """Test validation fails when enabled without audience."""
        config = OIDCConfig(enabled=True, issuer="https://auth.example.com/")
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        assert "MLSDM_OIDC_AUDIENCE is required" in str(exc_info.value)

    def test_validate_enabled_valid(self) -> None:
        """Test validation passes with all required fields."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
        )
        config.validate()  # Should not raise


class TestUserInfo:
    """Tests for UserInfo dataclass."""

    def test_default_values(self) -> None:
        """Test UserInfo with minimal required values."""
        user = UserInfo(subject="user123")
        assert user.subject == "user123"
        assert user.email is None
        assert user.name is None
        assert user.roles == []
        assert user.issuer == ""
        assert user.audience == ""
        assert user.claims == {}

    def test_full_user_info(self) -> None:
        """Test UserInfo with all fields populated."""
        claims = {"sub": "user123", "email": "test@example.com"}
        user = UserInfo(
            subject="user123",
            email="test@example.com",
            name="Test User",
            roles=["admin", "user"],
            issuer="https://auth.example.com/",
            audience="my-api",
            claims=claims,
        )
        assert user.subject == "user123"
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.roles == ["admin", "user"]
        assert user.issuer == "https://auth.example.com/"
        assert user.audience == "my-api"
        assert user.claims == claims


class TestJWKSCache:
    """Tests for JWKSCache."""

    def test_init(self) -> None:
        """Test JWKSCache initialization."""
        cache = JWKSCache(cache_ttl=1800)
        assert cache._cache_ttl == 1800
        assert cache._cache == {}
        assert cache._cache_time == 0

    def test_clear(self) -> None:
        """Test clearing the JWKS cache."""
        cache = JWKSCache()
        cache._cache = {"keys": [{"kid": "test"}]}
        cache._cache_time = 12345
        cache.clear()
        assert cache._cache == {}
        assert cache._cache_time == 0


class TestOIDCAuthenticator:
    """Tests for OIDCAuthenticator."""

    def test_init_disabled(self) -> None:
        """Test OIDCAuthenticator with disabled config."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)
        assert auth.enabled is False

    def test_init_enabled_valid(self) -> None:
        """Test OIDCAuthenticator with valid enabled config."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
        )
        auth = OIDCAuthenticator(config)
        assert auth.enabled is True

    def test_init_enabled_invalid(self) -> None:
        """Test OIDCAuthenticator raises on invalid enabled config."""
        config = OIDCConfig(enabled=True)  # Missing issuer and audience
        with pytest.raises(ValueError):
            OIDCAuthenticator(config)

    def test_from_env_disabled(self) -> None:
        """Test OIDCAuthenticator.from_env() with disabled OIDC."""
        env = {"MLSDM_OIDC_ENABLED": "false"}
        with patch.dict(os.environ, env, clear=False):
            auth = OIDCAuthenticator.from_env()
            assert auth.enabled is False

    def test_enabled_property(self) -> None:
        """Test enabled property."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)
        assert auth.enabled is False

        config2 = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
        )
        auth2 = OIDCAuthenticator(config2)
        assert auth2.enabled is True
