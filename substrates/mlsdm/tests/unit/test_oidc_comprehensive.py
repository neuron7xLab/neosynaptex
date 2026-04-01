"""Comprehensive tests for OIDC authentication module (SEC-004).

This test module expands coverage to include:
- Token extraction from requests
- JWKS discovery and caching
- OIDCAuthMiddleware dispatch logic
- require_oidc_auth decorator
- get_current_user and get_optional_user dependencies
- Error handling paths
"""

from __future__ import annotations

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from mlsdm.security.oidc import (
    JWKSCache,
    OIDCAuthenticator,
    OIDCAuthMiddleware,
    OIDCConfig,
    UserInfo,
    get_current_user,
    get_optional_user,
    require_oidc_auth,
)


class TestOIDCConfigValidation:
    """Extended tests for OIDCConfig validation."""

    def test_validate_enabled_missing_both(self) -> None:
        """Test validation fails when enabled without issuer and audience."""
        config = OIDCConfig(enabled=True)
        with pytest.raises(ValueError) as exc_info:
            config.validate()
        error_msg = str(exc_info.value)
        assert "MLSDM_OIDC_ISSUER is required" in error_msg
        assert "MLSDM_OIDC_AUDIENCE is required" in error_msg

    def test_from_env_jwks_uri(self) -> None:
        """Test OIDCConfig.from_env() with JWKS URI specified."""
        env = {
            "MLSDM_OIDC_ENABLED": "true",
            "MLSDM_OIDC_ISSUER": "https://auth.example.com/",
            "MLSDM_OIDC_AUDIENCE": "my-api",
            "MLSDM_OIDC_JWKS_URI": "https://auth.example.com/.well-known/jwks.json",
        }
        with patch.dict(os.environ, env, clear=False):
            config = OIDCConfig.from_env()
            assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"


class TestJWKSCacheExtended:
    """Extended tests for JWKSCache functionality."""

    def test_cache_hit(self) -> None:
        """Test JWKS cache returns cached data when not expired."""
        cache = JWKSCache(cache_ttl=3600)
        cache._cache = {"keys": [{"kid": "test-key"}]}
        cache._cache_time = time.time()

        # Should return cached data without fetching
        with patch("requests.get") as mock_get:
            result = cache.get_keys("https://example.com/jwks")
            mock_get.assert_not_called()
            assert result == {"keys": [{"kid": "test-key"}]}

    def test_cache_expired_refetch(self) -> None:
        """Test JWKS cache refreshes when expired."""
        cache = JWKSCache(cache_ttl=1)
        cache._cache = {"keys": [{"kid": "old-key"}]}
        cache._cache_time = time.time() - 10  # Expired

        new_jwks = {"keys": [{"kid": "new-key"}]}
        mock_response = MagicMock()
        mock_response.json.return_value = new_jwks

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = cache.get_keys("https://example.com/jwks")
            mock_get.assert_called_once()
            assert result == new_jwks

    def test_cache_fetch_failure_stale_cache(self) -> None:
        """Test JWKS cache returns stale data on fetch failure."""
        cache = JWKSCache(cache_ttl=1)
        cache._cache = {"keys": [{"kid": "stale-key"}]}
        cache._cache_time = time.time() - 10  # Expired

        with patch("requests.get", side_effect=Exception("Network error")):
            result = cache.get_keys("https://example.com/jwks")
            # Should return stale cache
            assert result == {"keys": [{"kid": "stale-key"}]}

    def test_cache_fetch_failure_no_stale_cache(self) -> None:
        """Test JWKS cache raises HTTP 503 when fetch fails and no stale cache."""
        cache = JWKSCache(cache_ttl=3600)
        # No cached data

        with patch("requests.get", side_effect=Exception("Network error")):
            with pytest.raises(HTTPException) as exc_info:
                cache.get_keys("https://example.com/jwks")
            assert exc_info.value.status_code == 503
            assert "Unable to validate authentication" in exc_info.value.detail


class TestOIDCAuthenticatorExtended:
    """Extended tests for OIDCAuthenticator."""

    def test_get_jwks_uri_from_config(self) -> None:
        """Test _get_jwks_uri returns config value when set."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            jwks_uri="https://auth.example.com/custom/jwks",
        )
        auth = OIDCAuthenticator(config)
        result = auth._get_jwks_uri()
        assert result == "https://auth.example.com/custom/jwks"

    def test_get_jwks_uri_discovery_success(self) -> None:
        """Test _get_jwks_uri discovers from .well-known when not configured."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            jwks_uri=None,
        )
        auth = OIDCAuthenticator(config)

        discovery_response = {"jwks_uri": "https://auth.example.com/discovered/jwks"}
        mock_response = MagicMock()
        mock_response.json.return_value = discovery_response

        with patch("requests.get", return_value=mock_response):
            result = auth._get_jwks_uri()
            assert result == "https://auth.example.com/discovered/jwks"

    def test_get_jwks_uri_discovery_cached(self) -> None:
        """Test _get_jwks_uri uses cached discovery."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            jwks_uri=None,
        )
        auth = OIDCAuthenticator(config)
        auth._discovery_cache = {"jwks_uri": "https://cached.example.com/jwks"}

        # Should not call requests.get
        with patch("requests.get") as mock_get:
            result = auth._get_jwks_uri()
            mock_get.assert_not_called()
            assert result == "https://cached.example.com/jwks"

    def test_get_jwks_uri_discovery_failure(self) -> None:
        """Test _get_jwks_uri raises HTTP 503 on discovery failure."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
            jwks_uri=None,
        )
        auth = OIDCAuthenticator(config)

        with patch("requests.get", side_effect=Exception("Network error")):
            with pytest.raises(HTTPException) as exc_info:
                auth._get_jwks_uri()
            assert exc_info.value.status_code == 503
            assert "Unable to discover OIDC configuration" in exc_info.value.detail

    def test_extract_token_no_header(self) -> None:
        """Test _extract_token returns None when no Authorization header."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        request = MagicMock(spec=Request)
        request.headers = {}
        result = auth._extract_token(request)
        assert result is None

    def test_extract_token_non_bearer(self) -> None:
        """Test _extract_token returns None for non-Bearer auth."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        result = auth._extract_token(request)
        assert result is None

    def test_extract_token_bearer(self) -> None:
        """Test _extract_token extracts Bearer token."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        request = MagicMock(spec=Request)
        request.headers.get = MagicMock(return_value="Bearer test-token-123")
        result = auth._extract_token(request)
        assert result == "test-token-123"

    @pytest.mark.asyncio
    async def test_authenticate_disabled(self) -> None:
        """Test authenticate returns None when OIDC disabled."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        request = MagicMock(spec=Request)
        result = await auth.authenticate(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self) -> None:
        """Test authenticate returns None when no token present."""
        config = OIDCConfig(
            enabled=True,
            issuer="https://auth.example.com/",
            audience="my-api",
        )
        auth = OIDCAuthenticator(config)

        # Use MagicMock for headers instead of dict
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="")

        request = MagicMock(spec=Request)
        request.headers = mock_headers
        result = await auth.authenticate(request)
        assert result is None


class TestOIDCAuthMiddlewareDispatch:
    """Tests for OIDCAuthMiddleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatch_skip_health_path(self) -> None:
        """Test middleware skips health check paths."""
        config = OIDCConfig(enabled=True, issuer="https://auth.example.com/", audience="api")
        auth = OIDCAuthenticator(config)

        # Create mock app and middleware
        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=auth)

        # Create mock request for health path
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health"
        mock_request.state = MagicMock()

        # Create mock call_next
        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None
        mock_call_next.assert_called_once_with(mock_request)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_skip_docs_path(self) -> None:
        """Test middleware skips docs paths."""
        config = OIDCConfig(enabled=True, issuer="https://auth.example.com/", audience="api")
        auth = OIDCAuthenticator(config)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None

    @pytest.mark.asyncio
    async def test_dispatch_skip_redoc_path(self) -> None:
        """Test middleware skips redoc paths."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock()

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/redoc"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None
        mock_auth.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_skip_openapi_path(self) -> None:
        """Test middleware skips openapi.json path."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock()

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/openapi.json"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None
        mock_auth.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_skip_health_subpath(self) -> None:
        """Test middleware skips health subpaths."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock()

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health/live"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None
        mock_auth.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_docs2_not_skipped(self) -> None:
        """Test middleware does not skip similar doc paths."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock(return_value=None)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs2"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_auth.authenticate.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_redoc2_not_skipped(self) -> None:
        """Test middleware does not skip similar redoc paths."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock(return_value=None)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/redoc2"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_auth.authenticate.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_dispatch_authenticator_exception_fails_closed(self) -> None:
        """Test middleware fails closed on authenticator exceptions."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock(side_effect=RuntimeError("auth failure"))

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=mock_auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 503
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_oidc_disabled(self) -> None:
        """Test middleware passes through when OIDC disabled."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(mock_app, authenticator=auth)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.user_info is None

    @pytest.mark.asyncio
    async def test_dispatch_oidc_disabled_blocks_required_paths(self) -> None:
        """Test middleware fails closed on protected paths when OIDC disabled."""
        config = OIDCConfig(enabled=False)
        auth = OIDCAuthenticator(config)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(
            mock_app,
            authenticator=auth,
            require_auth_paths=["/admin/"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/admin"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 503
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_require_auth_paths_boundary_safe(self) -> None:
        """Test require_auth_paths uses boundary-safe matching."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock(return_value=None)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(
            mock_app,
            authenticator=mock_auth,
            require_auth_paths=["/admin/"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/admin"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_require_auth_paths_no_prefix_collision(self) -> None:
        """Test require_auth_paths does not overmatch prefix collisions."""
        mock_auth = MagicMock()
        mock_auth.enabled = True
        mock_auth.authenticate = AsyncMock(return_value=None)

        mock_app = MagicMock()
        middleware = OIDCAuthMiddleware(
            mock_app,
            authenticator=mock_auth,
            require_auth_paths=["/admin/"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/adminx"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once_with(mock_request)


class TestRequireOIDCAuthDecorator:
    """Tests for require_oidc_auth decorator."""

    @pytest.mark.asyncio
    async def test_decorator_no_request_in_args(self) -> None:
        """Test decorator raises when request not found in args."""

        @require_oidc_auth()
        async def endpoint():
            return {"status": "ok"}

        with pytest.raises(HTTPException) as exc_info:
            await endpoint()
        assert exc_info.value.status_code == 500
        assert "Request object not found" in exc_info.value.detail

    def test_decorator_returns_function(self) -> None:
        """Test that decorator returns a callable."""

        @require_oidc_auth()
        async def endpoint(request):
            return {"status": "ok"}

        assert callable(endpoint)

    def test_decorator_with_roles(self) -> None:
        """Test decorator with roles parameter."""

        @require_oidc_auth(roles=["admin", "editor"])
        async def endpoint(request):
            return {"status": "ok"}

        assert callable(endpoint)

    def test_decorator_preserves_function_name(self) -> None:
        """Test that decorator preserves the original function name."""

        @require_oidc_auth()
        async def my_endpoint(request):
            return {"status": "ok"}

        assert my_endpoint.__name__ == "my_endpoint"


class TestUserDependencies:
    """Tests for get_current_user and get_optional_user dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(self) -> None:
        """Test get_current_user returns user when authenticated."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.user_info = UserInfo(
            subject="user123",
            email="user@example.com",
            roles=["admin"],
        )

        result = await get_current_user(mock_request)
        assert result.subject == "user123"
        assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_not_authenticated(self) -> None:
        """Test get_current_user raises 401 when not authenticated."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.user_info = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_optional_user_authenticated(self) -> None:
        """Test get_optional_user returns user when authenticated."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.user_info = UserInfo(subject="user123")

        result = await get_optional_user(mock_request)
        assert result is not None
        assert result.subject == "user123"

    @pytest.mark.asyncio
    async def test_get_optional_user_not_authenticated(self) -> None:
        """Test get_optional_user returns None when not authenticated."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.state.user_info = None

        result = await get_optional_user(mock_request)
        assert result is None


class TestUserInfoRolesList:
    """Test UserInfo roles handling."""

    def test_user_info_audience_as_list(self) -> None:
        """Test UserInfo supports audience as list."""
        user = UserInfo(
            subject="user123",
            audience=["api1", "api2"],
        )
        assert user.audience == ["api1", "api2"]
