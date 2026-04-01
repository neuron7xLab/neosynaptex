"""Tests for mTLS authentication module (SEC-006).

Tests the mTLS functionality including:
- MTLSConfig creation and from_env loading
- ClientCertInfo dataclass
- Certificate parsing utilities
- MTLSMiddleware behavior
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fastapi import Request

from mlsdm.security.mtls import (
    ClientCertInfo,
    MTLSConfig,
    get_client_cert_cn,
    get_client_cert_from_request,
    get_client_cert_info,
    parse_certificate_subject,
)


class TestMTLSConfig:
    """Tests for MTLSConfig dataclass."""

    def test_default_values(self) -> None:
        """Test MTLSConfig default values."""
        config = MTLSConfig()
        assert config.enabled is False
        assert config.ca_cert_path is None
        assert config.require_client_cert is True
        assert config.verify_depth == 3

    def test_custom_values(self) -> None:
        """Test MTLSConfig with custom values."""
        config = MTLSConfig(
            enabled=True,
            ca_cert_path="/path/to/ca.crt",
            require_client_cert=False,
            verify_depth=5,
        )
        assert config.enabled is True
        assert config.ca_cert_path == "/path/to/ca.crt"
        assert config.require_client_cert is False
        assert config.verify_depth == 5

    def test_from_env_defaults(self) -> None:
        """Test MTLSConfig.from_env() with default values."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("MLSDM_MTLS")}
        with patch.dict(os.environ, env, clear=True):
            config = MTLSConfig.from_env()
            assert config.enabled is False
            assert config.ca_cert_path is None
            assert config.require_client_cert is True
            assert config.verify_depth == 3

    def test_from_env_enabled(self) -> None:
        """Test MTLSConfig.from_env() with mTLS enabled."""
        env = {
            "MLSDM_MTLS_ENABLED": "true",
            "MLSDM_MTLS_CA_CERT": "/etc/certs/ca.crt",
            "MLSDM_MTLS_REQUIRE_CLIENT_CERT": "false",
            "MLSDM_MTLS_VERIFY_DEPTH": "5",
        }
        with patch.dict(os.environ, env, clear=False):
            config = MTLSConfig.from_env()
            assert config.enabled is True
            assert config.ca_cert_path == "/etc/certs/ca.crt"
            assert config.require_client_cert is False
            assert config.verify_depth == 5


class TestClientCertInfo:
    """Tests for ClientCertInfo dataclass."""

    def test_default_values(self) -> None:
        """Test ClientCertInfo default values."""
        info = ClientCertInfo()
        assert info.common_name is None
        assert info.organization is None
        assert info.organizational_unit is None
        assert info.serial_number is None
        assert info.subject is None
        assert info.issuer is None
        assert info.not_before is None
        assert info.not_after is None

    def test_full_cert_info(self) -> None:
        """Test ClientCertInfo with all fields."""
        info = ClientCertInfo(
            common_name="client.example.com",
            organization="Example Corp",
            organizational_unit="Engineering",
            serial_number="123456",
            subject="CN=client.example.com, O=Example Corp",
            issuer="CN=CA, O=Example Corp",
            not_before="Jan  1 00:00:00 2024 GMT",
            not_after="Jan  1 00:00:00 2025 GMT",
        )
        assert info.common_name == "client.example.com"
        assert info.organization == "Example Corp"
        assert info.organizational_unit == "Engineering"
        assert info.serial_number == "123456"


class TestCertificateParsing:
    """Tests for certificate parsing utilities."""

    def test_parse_certificate_subject(self) -> None:
        """Test parsing certificate subject."""
        # Simulated SSL certificate dict format
        cert = {
            "subject": (
                (("commonName", "test.example.com"),),
                (("organizationName", "Test Org"),),
                (("organizationalUnitName", "Test Unit"),),
            ),
            "issuer": (
                (("commonName", "CA"),),
                (("organizationName", "CA Org"),),
            ),
            "serialNumber": "ABCD1234",
            "notBefore": "Jan  1 00:00:00 2024 GMT",
            "notAfter": "Dec 31 23:59:59 2024 GMT",
        }
        info = parse_certificate_subject(cert)
        assert info.common_name == "test.example.com"
        assert info.organization == "Test Org"
        assert info.organizational_unit == "Test Unit"
        assert info.serial_number == "ABCD1234"
        assert info.not_before == "Jan  1 00:00:00 2024 GMT"
        assert info.not_after == "Dec 31 23:59:59 2024 GMT"

    def test_parse_empty_certificate(self) -> None:
        """Test parsing empty certificate."""
        info = parse_certificate_subject({})
        assert info.common_name is None
        assert info.organization is None
        assert info.subject is None

    def test_get_client_cert_from_request_no_transport(self) -> None:
        """Test get_client_cert_from_request with no transport."""
        request = MagicMock(spec=Request)
        request.scope = {}
        result = get_client_cert_from_request(request)
        assert result is None

    def test_get_client_cert_cn_no_cert(self) -> None:
        """Test get_client_cert_cn with no certificate."""
        request = MagicMock(spec=Request)
        request.scope = {}
        result = get_client_cert_cn(request)
        assert result is None

    def test_get_client_cert_info_no_cert(self) -> None:
        """Test get_client_cert_info with no certificate."""
        request = MagicMock(spec=Request)
        request.scope = {}
        result = get_client_cert_info(request)
        assert result is None
