"""Comprehensive tests for request signing module (SEC-007).

This test module expands coverage to include:
- SigningConfig.from_env with keys file
- SigningMiddleware dispatch logic
- Edge cases for parse_signature_header
- RequestSigner edge cases
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from mlsdm.security.signing import (
    RequestSigner,
    SignatureInfo,
    SigningConfig,
    SigningMiddleware,
    compute_signature,
    parse_signature_header,
    verify_signature,
)


class TestSigningConfigFromEnvExtended:
    """Extended tests for SigningConfig.from_env()."""

    def test_from_env_with_keys_file(self) -> None:
        """Test loading signing keys from file."""
        keys_data = {
            "key1": "secret1",
            "key2": "secret2",
            "production": "prod-secret-key",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(keys_data, f)
            keys_path = f.name

        try:
            env = {
                "MLSDM_SIGNING_ENABLED": "true",
                "MLSDM_SIGNING_KEYS_PATH": keys_path,
            }
            with patch.dict(os.environ, env, clear=False):
                config = SigningConfig.from_env()
                assert config.keys == keys_data
                assert config.keys["production"] == "prod-secret-key"
        finally:
            os.unlink(keys_path)

    def test_from_env_with_invalid_keys_file(self) -> None:
        """Test handling invalid keys file gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {{{")
            keys_path = f.name

        try:
            env = {
                "MLSDM_SIGNING_ENABLED": "true",
                "MLSDM_SIGNING_KEYS_PATH": keys_path,
            }
            with patch.dict(os.environ, env, clear=False):
                # Should not raise, just log error
                config = SigningConfig.from_env()
                assert config.keys == {}
        finally:
            os.unlink(keys_path)

    def test_from_env_with_nonexistent_keys_file(self) -> None:
        """Test handling nonexistent keys file."""
        env = {
            "MLSDM_SIGNING_ENABLED": "true",
            "MLSDM_SIGNING_KEYS_PATH": "/nonexistent/path/keys.json",
        }
        with patch.dict(os.environ, env, clear=False):
            config = SigningConfig.from_env()
            assert config.keys == {}


class TestParseSignatureHeaderExtended:
    """Extended tests for parse_signature_header."""

    def test_parse_header_empty_string(self) -> None:
        """Test parsing empty string."""
        assert parse_signature_header("") is None

    def test_parse_header_single_equals_in_value(self) -> None:
        """Test parsing header where value contains equals sign."""
        # Base64 encoded signatures often end with =
        header = "timestamp=1699123456,signature=abc123=="
        info = parse_signature_header(header)
        assert info is not None
        assert info.signature == "abc123=="

    def test_parse_header_extra_fields(self) -> None:
        """Test parsing header with extra fields."""
        header = "timestamp=1699123456,signature=abc123,extra=value"
        info = parse_signature_header(header)
        assert info is not None
        assert info.timestamp == 1699123456
        assert info.signature == "abc123"


class TestVerifySignatureExtended:
    """Extended tests for verify_signature."""

    def test_verify_clock_skew_allowance(self) -> None:
        """Test clock skew allowance for slightly future timestamps."""
        method = "POST"
        path = "/test"
        body = b"test"
        secret = "secret"
        # Timestamp 15 seconds in the future (within 30s allowance)
        future_time = int(time.time()) + 15

        sig = compute_signature(method, path, future_time, body, secret)
        sig_info = SignatureInfo(timestamp=future_time, signature=sig)

        result = verify_signature(
            method=method,
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is True

    def test_verify_tampered_body(self) -> None:
        """Test signature verification fails with tampered body."""
        method = "POST"
        path = "/test"
        original_body = b"original"
        tampered_body = b"tampered"
        secret = "secret"
        current_time = int(time.time())

        sig = compute_signature(method, path, current_time, original_body, secret)
        sig_info = SignatureInfo(timestamp=current_time, signature=sig)

        result = verify_signature(
            method=method,
            path=path,
            body=tampered_body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is False

    def test_verify_wrong_method(self) -> None:
        """Test signature verification fails with wrong method."""
        path = "/test"
        body = b"test"
        secret = "secret"
        current_time = int(time.time())

        sig = compute_signature("POST", path, current_time, body, secret)
        sig_info = SignatureInfo(timestamp=current_time, signature=sig)

        result = verify_signature(
            method="GET",  # Wrong method
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is False

    def test_verify_wrong_path(self) -> None:
        """Test signature verification fails with wrong path."""
        method = "POST"
        body = b"test"
        secret = "secret"
        current_time = int(time.time())

        sig = compute_signature(method, "/original", current_time, body, secret)
        sig_info = SignatureInfo(timestamp=current_time, signature=sig)

        result = verify_signature(
            method=method,
            path="/tampered",  # Wrong path
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is False


class TestSigningMiddlewareDispatch:
    """Tests for SigningMiddleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatch_skip_health_path(self) -> None:
        """Test middleware skips health paths."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health"

        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once_with(mock_request)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_skip_docs_path(self) -> None:
        """Test middleware skips docs paths."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs"

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_skip_redoc_path(self) -> None:
        """Test middleware skips redoc paths."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/redoc"

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_healthcheck_not_skipped(self) -> None:
        """Test middleware does not skip /healthcheck prefix collisions."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=None)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/healthcheck"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_docs2_not_skipped(self) -> None:
        """Test middleware does not skip /docs2 prefix collisions."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=None)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs2"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_verify_exception_fails_closed(self) -> None:
        """Test middleware fails closed on signature verification exceptions."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="timestamp=123456,signature=abc123")

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/private"
        mock_request.headers = mock_headers
        mock_request.method = "GET"
        mock_request.body = AsyncMock(return_value=b"")

        mock_call_next = AsyncMock()

        with (
            patch("mlsdm.security.signing.verify_signature", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError),
        ):
            await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_signing_disabled(self) -> None:
        """Test middleware passes through when signing disabled."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=False)
        middleware = SigningMiddleware(mock_app, config=config)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_missing_signature(self) -> None:
        """Test middleware raises 401 when signature missing."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=None)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Missing request signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_invalid_signature_format(self) -> None:
        """Test middleware raises 401 for invalid signature format."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="invalid-format")

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Invalid signature format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_no_secret_key_configured(self) -> None:
        """Test middleware raises 401 when no secret key configured."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key=None)
        middleware = SigningMiddleware(mock_app, config=config)

        sig_header = "timestamp=123456,signature=abc123"
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=sig_header)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Signing not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_invalid_key_id(self) -> None:
        """Test middleware raises 401 for invalid key_id."""
        mock_app = MagicMock()
        config = SigningConfig(
            enabled=True,
            secret_key=None,
            keys={"valid-key": "secret"},
        )
        middleware = SigningMiddleware(mock_app, config=config)

        sig_header = "key_id=invalid-key,timestamp=123456,signature=abc123"
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=sig_header)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Invalid key ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_invalid_signature(self) -> None:
        """Test middleware raises 401 for invalid signature."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(mock_app, config=config)

        current_time = int(time.time())
        sig_header = f"timestamp={current_time},signature=invalid-signature"

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=sig_header)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.method = "POST"
        mock_request.headers = mock_headers
        mock_request.body = AsyncMock(return_value=b"test body")

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Invalid request signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_valid_signature(self) -> None:
        """Test middleware accepts valid signature."""
        mock_app = MagicMock()
        secret = "test-secret"
        config = SigningConfig(enabled=True, secret_key=secret)
        middleware = SigningMiddleware(mock_app, config=config)

        method = "POST"
        path = "/api/endpoint"
        body = b"test body"
        current_time = int(time.time())

        # Generate valid signature
        valid_sig = compute_signature(method, path, current_time, body, secret)
        sig_header = f"timestamp={current_time},signature={valid_sig}"

        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=sig_header)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = path
        mock_request.method = method
        mock_request.headers = mock_headers
        mock_request.body = AsyncMock(return_value=body)

        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once()
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_with_require_signature_paths(self) -> None:
        """Test middleware respects require_signature_paths."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(
            mock_app,
            config=config,
            require_signature_paths=["/api/secure"],
        )

        # Request to non-required path should pass without signature
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/public"

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_require_signature_boundary_safe(self) -> None:
        """Test require_signature_paths uses boundary-safe matching."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(
            mock_app,
            config=config,
            require_signature_paths=["/api/secure/"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/secure"
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=None)
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock(return_value=MagicMock())

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_require_signature_no_prefix_collision(self) -> None:
        """Test require_signature_paths does not overmatch prefix collisions."""
        mock_app = MagicMock()
        config = SigningConfig(enabled=True, secret_key="test-secret")
        middleware = SigningMiddleware(
            mock_app,
            config=config,
            require_signature_paths=["/api/secure/"],
        )

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/securex"
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value=None)
        mock_request.headers = mock_headers

        mock_call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_called_once_with(mock_request)


class TestSigningMiddlewareGetSecretKey:
    """Tests for SigningMiddleware._get_secret_key."""

    def test_get_secret_key_with_key_id(self) -> None:
        """Test getting secret key by key_id."""
        mock_app = MagicMock()
        config = SigningConfig(
            enabled=True,
            keys={"key1": "secret1", "key2": "secret2"},
        )
        middleware = SigningMiddleware(mock_app, config=config)

        result = middleware._get_secret_key("key1")
        assert result == "secret1"

    def test_get_secret_key_fallback(self) -> None:
        """Test falling back to single secret key."""
        mock_app = MagicMock()
        config = SigningConfig(
            enabled=True,
            secret_key="fallback-secret",
            keys={},
        )
        middleware = SigningMiddleware(mock_app, config=config)

        result = middleware._get_secret_key(None)
        assert result == "fallback-secret"

    def test_get_secret_key_invalid_key_id(self) -> None:
        """Test invalid key_id returns None."""
        mock_app = MagicMock()
        config = SigningConfig(
            enabled=True,
            secret_key=None,
            keys={"valid": "secret"},
        )
        middleware = SigningMiddleware(mock_app, config=config)

        result = middleware._get_secret_key("invalid")
        assert result is None


class TestRequestSignerExtended:
    """Extended tests for RequestSigner."""

    def test_sign_request_empty_body(self) -> None:
        """Test signing with empty body."""
        signer = RequestSigner(secret_key="my-secret")
        headers = signer.sign_request(
            method="GET",
            path="/health",
            body=b"",
        )
        assert "X-MLSDM-Signature" in headers

    def test_sign_request_without_key_id(self) -> None:
        """Test signing without key_id doesn't add Key-ID header."""
        signer = RequestSigner(secret_key="my-secret", key_id=None)
        headers = signer.sign_request(
            method="GET",
            path="/health",
        )
        assert "X-MLSDM-Key-ID" not in headers

    def test_sign_request_roundtrip(self) -> None:
        """Test that signed request can be verified."""
        secret = "test-secret"
        signer = RequestSigner(secret_key=secret)

        method = "POST"
        path = "/api/test"
        body = b'{"data": "test"}'

        headers = signer.sign_request(method=method, path=path, body=body)
        sig_header = headers["X-MLSDM-Signature"]

        # Parse and verify
        sig_info = parse_signature_header(sig_header)
        assert sig_info is not None

        result = verify_signature(
            method=method,
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is True


class TestComputeSignatureExtended:
    """Extended tests for compute_signature."""

    def test_compute_signature_case_sensitivity(self) -> None:
        """Test that method is case-insensitive (uppercased)."""
        body = b"test"
        secret = "secret"
        timestamp = 12345

        # Both should produce same signature since method is uppercased
        sig1 = compute_signature("post", "/path", timestamp, body, secret)
        sig2 = compute_signature("POST", "/path", timestamp, body, secret)
        assert sig1 == sig2

    def test_compute_signature_empty_body(self) -> None:
        """Test computing signature with empty body."""
        sig = compute_signature("GET", "/health", 12345, b"", "secret")
        assert sig is not None
        assert len(sig) > 0


class TestSigningMiddlewareInit:
    """Tests for SigningMiddleware initialization."""

    def test_init_default_config(self) -> None:
        """Test middleware uses from_env when no config provided."""
        mock_app = MagicMock()

        env = {k: v for k, v in os.environ.items() if not k.startswith("MLSDM_SIGNING")}
        with patch.dict(os.environ, env, clear=True):
            middleware = SigningMiddleware(mock_app)
            assert middleware.config.enabled is False

    def test_init_custom_skip_paths(self) -> None:
        """Test custom skip paths."""
        mock_app = MagicMock()
        custom_paths = ["/custom1", "/custom2"]
        middleware = SigningMiddleware(mock_app, skip_paths=custom_paths)
        assert middleware.skip_paths == custom_paths

    def test_init_default_skip_paths(self) -> None:
        """Test default skip paths include common endpoints."""
        mock_app = MagicMock()
        middleware = SigningMiddleware(mock_app)
        assert "/health" in middleware.skip_paths
        assert "/docs" in middleware.skip_paths
        assert "/openapi.json" in middleware.skip_paths
        assert "/redoc" in middleware.skip_paths
