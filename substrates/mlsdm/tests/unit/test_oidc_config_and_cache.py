"""Targeted tests for OIDC configuration and caching utilities."""

import pytest
from starlette.requests import Request

from mlsdm.security.oidc import JWKSCache, OIDCAuthenticator, OIDCConfig


def test_oidc_config_validate_requires_fields():
    """Enabled config without issuer/audience should raise errors."""
    config = OIDCConfig(enabled=True, issuer="", audience="")
    with pytest.raises(ValueError, match="OIDC configuration error"):
        config.validate()


def test_oidc_config_from_env_parses_algorithms(monkeypatch):
    """Environment parsing should honor booleans, algorithms, and cache TTL."""
    monkeypatch.setenv("MLSDM_OIDC_ENABLED", "true")
    monkeypatch.setenv("MLSDM_OIDC_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("MLSDM_OIDC_AUDIENCE", "api://example")
    monkeypatch.setenv("MLSDM_OIDC_ALGORITHMS", "RS256,HS256")
    monkeypatch.setenv("MLSDM_OIDC_CACHE_TTL", "120")
    monkeypatch.setenv("MLSDM_OIDC_ROLES_CLAIM", "custom_roles")

    config = OIDCConfig.from_env()

    assert config.enabled is True
    assert config.algorithms == ["RS256", "HS256"]
    assert config.cache_ttl == 120
    assert config.roles_claim == "custom_roles"


def test_jwks_cache_uses_cached_value(monkeypatch):
    """JWKS cache should avoid refetching within TTL."""
    calls: list[str] = []

    def fake_get(url: str, timeout: int):
        calls.append(url)

        class _Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"keys": ["k1"]}

        return _Resp()

    monkeypatch.setattr("requests.get", fake_get)
    cache = JWKSCache(cache_ttl=3600)

    first = cache.get_keys("http://example.com/jwks")
    second = cache.get_keys("http://example.com/jwks")

    assert len(calls) == 1
    assert first == {"keys": ["k1"]}
    assert second == first


def test_jwks_cache_returns_stale_on_error(monkeypatch):
    """When refresh fails but cache exists, stale data should be returned."""
    cache = JWKSCache(cache_ttl=1)
    cache._cache = {"keys": ["stale"]}  # type: ignore[attr-defined]
    cache._cache_time = 0  # type: ignore[attr-defined]

    def failing_get(*_args, **_kwargs):
        raise Exception("network error")

    monkeypatch.setattr("requests.get", failing_get)
    result = cache.get_keys("http://example.com/jwks")

    assert result == {"keys": ["stale"]}


def test_extract_token_handles_bearer_header():
    """_extract_token should parse Bearer tokens and ignore missing headers."""
    config = OIDCConfig(enabled=False, issuer="", audience="")
    authenticator = OIDCAuthenticator(config)

    request = Request(
        {"type": "http", "method": "GET", "path": "/", "headers": [(b"authorization", b"Bearer token123")]}
    )
    assert authenticator._extract_token(request) == "token123"

    request_no_auth = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    assert authenticator._extract_token(request_no_auth) is None
