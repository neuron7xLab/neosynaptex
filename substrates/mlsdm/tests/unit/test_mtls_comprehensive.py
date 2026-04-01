"""Comprehensive tests for mTLS authentication module (SEC-006).

This test module expands coverage to include:
- MTLSMiddleware dispatch logic
- create_ssl_context function
- Certificate parsing edge cases
- Request transport handling
"""

from __future__ import annotations

import os
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from mlsdm.security.mtls import (
    ClientCertInfo,
    MTLSConfig,
    MTLSMiddleware,
    create_ssl_context,
    get_client_cert_cn,
    get_client_cert_from_request,
    get_client_cert_info,
    parse_certificate_subject,
)


class TestMTLSConfigFromEnv:
    """Extended tests for MTLSConfig.from_env()."""

    def test_from_env_require_client_cert_true(self) -> None:
        """Test require_client_cert defaults to true."""
        env = {
            "MLSDM_MTLS_ENABLED": "true",
            "MLSDM_MTLS_CA_CERT": "/path/to/ca.crt",
        }
        with patch.dict(os.environ, env, clear=False):
            config = MTLSConfig.from_env()
            assert config.require_client_cert is True

    def test_from_env_require_client_cert_false(self) -> None:
        """Test require_client_cert can be set to false."""
        env = {
            "MLSDM_MTLS_ENABLED": "true",
            "MLSDM_MTLS_CA_CERT": "/path/to/ca.crt",
            "MLSDM_MTLS_REQUIRE_CLIENT_CERT": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            config = MTLSConfig.from_env()
            assert config.require_client_cert is False


class TestParseSubjectExtended:
    """Extended tests for parse_certificate_subject."""

    def test_parse_subject_with_all_fields(self) -> None:
        """Test parsing certificate with all fields."""
        cert = {
            "subject": (
                (("commonName", "client.example.com"),),
                (("organizationName", "Example Corp"),),
                (("organizationalUnitName", "Engineering"),),
                (("countryName", "US"),),
            ),
            "issuer": (
                (("commonName", "Root CA"),),
                (("organizationName", "CA Corp"),),
            ),
            "serialNumber": "1234567890ABCDEF",
            "notBefore": "Jan  1 00:00:00 2024 GMT",
            "notAfter": "Dec 31 23:59:59 2024 GMT",
        }
        info = parse_certificate_subject(cert)
        assert info.common_name == "client.example.com"
        assert info.organization == "Example Corp"
        assert info.organizational_unit == "Engineering"
        assert info.serial_number == "1234567890ABCDEF"
        assert "commonName=Root CA" in info.issuer
        assert "organizationName=CA Corp" in info.issuer
        assert info.not_before == "Jan  1 00:00:00 2024 GMT"
        assert info.not_after == "Dec 31 23:59:59 2024 GMT"

    def test_parse_subject_string_format(self) -> None:
        """Test subject string format construction."""
        cert = {
            "subject": (
                (("commonName", "test.local"),),
                (("organizationName", "Test Org"),),
            ),
            "issuer": (),
        }
        info = parse_certificate_subject(cert)
        assert info.subject is not None
        assert "commonName=test.local" in info.subject
        assert "organizationName=Test Org" in info.subject

    def test_parse_subject_empty_issuer(self) -> None:
        """Test parsing with empty issuer."""
        cert = {
            "subject": ((("commonName", "test"),),),
            "issuer": (),
        }
        info = parse_certificate_subject(cert)
        assert info.issuer is None or info.issuer == ""

    def test_parse_subject_no_serial(self) -> None:
        """Test parsing without serial number."""
        cert = {
            "subject": ((("commonName", "test"),),),
            "issuer": (),
        }
        info = parse_certificate_subject(cert)
        assert info.serial_number == ""


class TestGetClientCertFromRequestExtended:
    """Extended tests for get_client_cert_from_request."""

    def test_no_ssl_object(self) -> None:
        """Test when transport exists but no SSL object."""
        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=None)

        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"transport": mock_transport}

        result = get_client_cert_from_request(mock_request)
        assert result is None

    def test_ssl_object_getpeercert_fails(self) -> None:
        """Test when getpeercert raises exception."""
        mock_ssl = MagicMock()
        mock_ssl.getpeercert = MagicMock(side_effect=Exception("SSL error"))

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=mock_ssl)

        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"transport": mock_transport}

        result = get_client_cert_from_request(mock_request)
        assert result is None

    def test_ssl_object_returns_cert(self) -> None:
        """Test successful certificate retrieval."""
        mock_cert = {"subject": ((("commonName", "test.local"),),)}
        mock_ssl = MagicMock()
        mock_ssl.getpeercert = MagicMock(return_value=mock_cert)

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=mock_ssl)

        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"transport": mock_transport}

        result = get_client_cert_from_request(mock_request)
        assert result == mock_cert


class TestGetClientCertCNExtended:
    """Extended tests for get_client_cert_cn."""

    def test_get_cn_with_valid_cert(self) -> None:
        """Test getting CN from valid certificate."""
        mock_cert = {
            "subject": ((("commonName", "client.example.com"),),),
            "issuer": (),
        }
        mock_ssl = MagicMock()
        mock_ssl.getpeercert = MagicMock(return_value=mock_cert)

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=mock_ssl)

        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"transport": mock_transport}

        result = get_client_cert_cn(mock_request)
        assert result == "client.example.com"


class TestGetClientCertInfoExtended:
    """Extended tests for get_client_cert_info."""

    def test_get_info_with_valid_cert(self) -> None:
        """Test getting full info from valid certificate."""
        mock_cert = {
            "subject": (
                (("commonName", "client.example.com"),),
                (("organizationName", "Test Org"),),
            ),
            "issuer": ((("commonName", "CA"),),),
            "serialNumber": "12345",
        }
        mock_ssl = MagicMock()
        mock_ssl.getpeercert = MagicMock(return_value=mock_cert)

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=mock_ssl)

        mock_request = MagicMock(spec=Request)
        mock_request.scope = {"transport": mock_transport}

        result = get_client_cert_info(mock_request)
        assert result is not None
        assert result.common_name == "client.example.com"
        assert result.organization == "Test Org"


class TestMTLSMiddlewareDispatch:
    """Tests for MTLSMiddleware dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatch_skip_health_path(self) -> None:
        """Test middleware skips health paths."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/health"
        mock_request.state = MagicMock()

        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.client_cert is None
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_dispatch_skip_docs_path(self) -> None:
        """Test middleware skips docs paths."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.client_cert is None

    @pytest.mark.asyncio
    async def test_dispatch_skip_redoc_path(self) -> None:
        """Test middleware skips redoc paths."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/redoc"
        mock_request.state = MagicMock()

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.client_cert is None

    @pytest.mark.asyncio
    async def test_dispatch_healthcheck_not_skipped(self) -> None:
        """Test middleware does not skip /healthcheck prefix collisions."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)
            middleware.config.enabled = True

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/healthcheck"
        mock_request.state = MagicMock()
        mock_request.scope = {}

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_cert_extraction_failure_fails_closed(self) -> None:
        """Test middleware fails closed on cert extraction errors."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)
            middleware.config.enabled = True

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/private"
        mock_request.state = MagicMock()
        mock_request.scope = {}

        mock_call_next = AsyncMock()

        with (
            patch("mlsdm.security.mtls.get_client_cert_info", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError),
        ):
            await middleware.dispatch(mock_request, mock_call_next)
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_docs2_not_skipped(self) -> None:
        """Test middleware does not skip /docs2 prefix collisions."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)
            middleware.config.enabled = True

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/docs2"
        mock_request.state = MagicMock()
        mock_request.scope = {}

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dispatch_mtls_disabled(self) -> None:
        """Test middleware passes through when mTLS disabled."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "false"}, clear=False):
            middleware = MTLSMiddleware(mock_app, require_cert=True)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.state = MagicMock()
        mock_request.scope = {}

        mock_call_next = AsyncMock(return_value=MagicMock())
        await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.client_cert is None

    @pytest.mark.asyncio
    async def test_dispatch_require_cert_missing(self) -> None:
        """Test middleware raises 401 when cert required but missing."""
        mock_app = MagicMock()

        # Create middleware with mTLS enabled
        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)
            middleware.config.enabled = True

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.state = MagicMock()
        mock_request.scope = {}  # No transport means no cert

        mock_call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, mock_call_next)
        assert exc_info.value.status_code == 401
        assert "Client certificate required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dispatch_with_valid_cert(self) -> None:
        """Test middleware accepts valid certificate."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"MLSDM_MTLS_ENABLED": "true"}):
            middleware = MTLSMiddleware(mock_app, require_cert=True)
            middleware.config.enabled = True

        # Mock certificate
        mock_cert = {
            "subject": ((("commonName", "client.local"),),),
            "issuer": (),
        }
        mock_ssl = MagicMock()
        mock_ssl.getpeercert = MagicMock(return_value=mock_cert)

        mock_transport = MagicMock()
        mock_transport.get_extra_info = MagicMock(return_value=mock_ssl)

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/endpoint"
        mock_request.state = MagicMock()
        mock_request.scope = {"transport": mock_transport}

        mock_response = MagicMock()
        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)
        assert mock_request.state.client_cert is not None
        assert mock_request.state.client_cert.common_name == "client.local"
        assert result == mock_response


class TestCreateSSLContext:
    """Tests for create_ssl_context function."""

    def test_create_ssl_context_disabled(self) -> None:
        """Test create_ssl_context returns None when disabled."""
        config = MTLSConfig(enabled=False, ca_cert_path="/path/to/ca.crt")
        result = create_ssl_context(config)
        assert result is None

    def test_create_ssl_context_no_ca_path(self) -> None:
        """Test create_ssl_context returns None without CA path."""
        config = MTLSConfig(enabled=True, ca_cert_path=None)
        result = create_ssl_context(config)
        assert result is None

    def test_create_ssl_context_require_cert_with_mock(self) -> None:
        """Test create_ssl_context with require_client_cert=True using mock."""
        config = MTLSConfig(
            enabled=True,
            ca_cert_path="/path/to/ca.crt",
            require_client_cert=True,
        )

        # Mock ssl.create_default_context to avoid needing real cert
        with patch("mlsdm.security.mtls.ssl.create_default_context") as mock_create:
            mock_context = MagicMock()
            mock_create.return_value = mock_context

            context = create_ssl_context(config)

            assert context is mock_context
            mock_context.load_verify_locations.assert_called_once_with("/path/to/ca.crt")
            assert mock_context.verify_mode == ssl.CERT_REQUIRED

    def test_create_ssl_context_optional_cert_with_mock(self) -> None:
        """Test create_ssl_context with require_client_cert=False using mock."""
        config = MTLSConfig(
            enabled=True,
            ca_cert_path="/path/to/ca.crt",
            require_client_cert=False,
        )

        with patch("mlsdm.security.mtls.ssl.create_default_context") as mock_create:
            mock_context = MagicMock()
            mock_create.return_value = mock_context

            context = create_ssl_context(config)

            assert context is mock_context
            assert mock_context.verify_mode == ssl.CERT_OPTIONAL


class TestMTLSMiddlewareInit:
    """Tests for MTLSMiddleware initialization."""

    def test_init_default_skip_paths(self) -> None:
        """Test default skip paths."""
        mock_app = MagicMock()
        middleware = MTLSMiddleware(mock_app)
        assert "/health" in middleware.skip_paths
        assert "/docs" in middleware.skip_paths
        assert "/redoc" in middleware.skip_paths
        assert "/openapi.json" in middleware.skip_paths

    def test_init_custom_skip_paths(self) -> None:
        """Test custom skip paths."""
        mock_app = MagicMock()
        custom_paths = ["/custom", "/other"]
        middleware = MTLSMiddleware(mock_app, skip_paths=custom_paths)
        assert middleware.skip_paths == custom_paths

    def test_init_require_cert_default(self) -> None:
        """Test require_cert defaults to True."""
        mock_app = MagicMock()
        middleware = MTLSMiddleware(mock_app)
        assert middleware.require_cert is True


class TestClientCertInfoEquality:
    """Tests for ClientCertInfo dataclass."""

    def test_cert_info_equality(self) -> None:
        """Test two ClientCertInfo with same values are equal."""
        info1 = ClientCertInfo(
            common_name="test.local",
            organization="Test",
        )
        info2 = ClientCertInfo(
            common_name="test.local",
            organization="Test",
        )
        assert info1 == info2

    def test_cert_info_inequality(self) -> None:
        """Test two ClientCertInfo with different values are not equal."""
        info1 = ClientCertInfo(common_name="test1.local")
        info2 = ClientCertInfo(common_name="test2.local")
        assert info1 != info2
