"""Tests for request signing module (SEC-007).

Tests the request signing functionality including:
- SigningConfig creation and from_env loading
- SignatureInfo dataclass
- Signature generation and verification
- Replay attack prevention
- RequestSigner client helper
"""

from __future__ import annotations

import base64
import os
import time
from unittest.mock import patch

from mlsdm.security.signing import (
    RequestSigner,
    SignatureInfo,
    SigningConfig,
    compute_signature,
    generate_signature,
    parse_signature_header,
    verify_signature,
)


class TestSigningConfig:
    """Tests for SigningConfig dataclass."""

    def test_default_values(self) -> None:
        """Test SigningConfig default values."""
        config = SigningConfig()
        assert config.enabled is False
        assert config.secret_key is None
        assert config.max_age_seconds == 300
        assert config.keys == {}

    def test_custom_values(self) -> None:
        """Test SigningConfig with custom values."""
        config = SigningConfig(
            enabled=True,
            secret_key="my-secret-key",
            max_age_seconds=600,
            keys={"key1": "secret1", "key2": "secret2"},
        )
        assert config.enabled is True
        assert config.secret_key == "my-secret-key"
        assert config.max_age_seconds == 600
        assert config.keys == {"key1": "secret1", "key2": "secret2"}

    def test_from_env_defaults(self) -> None:
        """Test SigningConfig.from_env() with default values."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("MLSDM_SIGNING")}
        with patch.dict(os.environ, env, clear=True):
            config = SigningConfig.from_env()
            assert config.enabled is False
            assert config.secret_key is None
            assert config.max_age_seconds == 300

    def test_from_env_enabled(self) -> None:
        """Test SigningConfig.from_env() with signing enabled."""
        env = {
            "MLSDM_SIGNING_ENABLED": "true",
            "MLSDM_SIGNING_KEY": "my-secret-key",
            "MLSDM_SIGNING_MAX_AGE": "600",
        }
        with patch.dict(os.environ, env, clear=False):
            config = SigningConfig.from_env()
            assert config.enabled is True
            assert config.secret_key == "my-secret-key"
            assert config.max_age_seconds == 600


class TestSignatureInfo:
    """Tests for SignatureInfo dataclass."""

    def test_signature_info(self) -> None:
        """Test SignatureInfo creation."""
        info = SignatureInfo(
            timestamp=1699123456,
            signature="abc123",
            key_id="key1",
        )
        assert info.timestamp == 1699123456
        assert info.signature == "abc123"
        assert info.key_id == "key1"

    def test_signature_info_no_key_id(self) -> None:
        """Test SignatureInfo without key_id."""
        info = SignatureInfo(
            timestamp=1699123456,
            signature="abc123",
        )
        assert info.timestamp == 1699123456
        assert info.signature == "abc123"
        assert info.key_id is None


class TestComputeSignature:
    """Tests for compute_signature function."""

    def test_compute_signature(self) -> None:
        """Test computing HMAC-SHA256 signature."""
        method = "POST"
        path = "/generate"
        timestamp = 1699123456
        body = b'{"prompt":"Hello"}'
        secret_key = "test-secret-key"

        signature = compute_signature(method, path, timestamp, body, secret_key)

        # Verify it's a valid base64 string
        assert signature
        base64.b64decode(signature)  # Should not raise

    def test_compute_signature_consistency(self) -> None:
        """Test that same inputs produce same signature."""
        method = "GET"
        path = "/health"
        timestamp = 1699123456
        body = b""
        secret_key = "secret"

        sig1 = compute_signature(method, path, timestamp, body, secret_key)
        sig2 = compute_signature(method, path, timestamp, body, secret_key)
        assert sig1 == sig2

    def test_compute_signature_different_inputs(self) -> None:
        """Test that different inputs produce different signatures."""
        timestamp = 1699123456
        body = b"test"
        secret = "secret"

        sig1 = compute_signature("GET", "/path1", timestamp, body, secret)
        sig2 = compute_signature("GET", "/path2", timestamp, body, secret)
        assert sig1 != sig2

        sig3 = compute_signature("GET", "/path1", timestamp, body, "other-secret")
        assert sig1 != sig3


class TestGenerateSignature:
    """Tests for generate_signature function."""

    def test_generate_signature_format(self) -> None:
        """Test generated signature header format."""
        signature = generate_signature(
            method="POST",
            path="/generate",
            body=b'{"prompt":"Hello"}',
            secret_key="my-secret",
        )
        # Format: timestamp=123456,signature=abc...
        assert "timestamp=" in signature
        assert ",signature=" in signature

    def test_generate_signature_with_key_id(self) -> None:
        """Test generated signature with key_id."""
        signature = generate_signature(
            method="POST",
            path="/generate",
            body=b"{}",
            secret_key="my-secret",
            key_id="key1",
        )
        assert "key_id=key1," in signature
        assert "timestamp=" in signature
        assert ",signature=" in signature


class TestParseSignatureHeader:
    """Tests for parse_signature_header function."""

    def test_parse_valid_header(self) -> None:
        """Test parsing valid signature header."""
        header = "timestamp=1699123456,signature=abc123def"
        info = parse_signature_header(header)
        assert info is not None
        assert info.timestamp == 1699123456
        assert info.signature == "abc123def"
        assert info.key_id is None

    def test_parse_header_with_key_id(self) -> None:
        """Test parsing header with key_id."""
        header = "key_id=mykey,timestamp=1699123456,signature=abc123"
        info = parse_signature_header(header)
        assert info is not None
        assert info.key_id == "mykey"
        assert info.timestamp == 1699123456
        assert info.signature == "abc123"

    def test_parse_invalid_header_missing_timestamp(self) -> None:
        """Test parsing header missing timestamp."""
        header = "signature=abc123"
        info = parse_signature_header(header)
        assert info is None

    def test_parse_invalid_header_missing_signature(self) -> None:
        """Test parsing header missing signature."""
        header = "timestamp=1699123456"
        info = parse_signature_header(header)
        assert info is None

    def test_parse_malformed_header(self) -> None:
        """Test parsing malformed header."""
        info = parse_signature_header("not-a-valid-header")
        assert info is None


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_valid_signature(self) -> None:
        """Test verifying a valid signature."""
        method = "POST"
        path = "/generate"
        body = b'{"prompt":"Hello"}'
        secret = "my-secret"
        current_time = int(time.time())

        # Generate signature
        expected_sig = compute_signature(method, path, current_time, body, secret)
        sig_info = SignatureInfo(timestamp=current_time, signature=expected_sig)

        # Verify
        result = verify_signature(
            method=method,
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,
        )
        assert result is True

    def test_verify_expired_signature(self) -> None:
        """Test rejecting expired signature."""
        method = "POST"
        path = "/test"
        body = b"test"
        secret = "secret"
        old_time = int(time.time()) - 600  # 10 minutes ago

        sig = compute_signature(method, path, old_time, body, secret)
        sig_info = SignatureInfo(timestamp=old_time, signature=sig)

        result = verify_signature(
            method=method,
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key=secret,
            max_age_seconds=300,  # 5 minutes
        )
        assert result is False

    def test_verify_future_signature(self) -> None:
        """Test rejecting signature from the future."""
        method = "POST"
        path = "/test"
        body = b"test"
        secret = "secret"
        future_time = int(time.time()) + 600  # 10 minutes in future

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
        assert result is False

    def test_verify_invalid_signature(self) -> None:
        """Test rejecting invalid signature."""
        method = "POST"
        path = "/test"
        body = b"test"
        current_time = int(time.time())

        sig_info = SignatureInfo(timestamp=current_time, signature="invalid-signature")

        result = verify_signature(
            method=method,
            path=path,
            body=body,
            signature_info=sig_info,
            secret_key="secret",
            max_age_seconds=300,
        )
        assert result is False


class TestRequestSigner:
    """Tests for RequestSigner helper class."""

    def test_sign_request(self) -> None:
        """Test signing a request."""
        signer = RequestSigner(secret_key="my-secret")
        headers = signer.sign_request(
            method="POST",
            path="/generate",
            body=b'{"prompt":"Hello"}',
        )
        assert "X-MLSDM-Signature" in headers
        assert "timestamp=" in headers["X-MLSDM-Signature"]
        assert ",signature=" in headers["X-MLSDM-Signature"]

    def test_sign_request_with_key_id(self) -> None:
        """Test signing with key_id."""
        signer = RequestSigner(secret_key="my-secret", key_id="key1")
        headers = signer.sign_request(
            method="POST",
            path="/generate",
            body="test",
        )
        assert "X-MLSDM-Signature" in headers
        assert "X-MLSDM-Key-ID" in headers
        assert headers["X-MLSDM-Key-ID"] == "key1"

    def test_sign_request_string_body(self) -> None:
        """Test signing with string body (auto-encoded)."""
        signer = RequestSigner(secret_key="secret")
        headers = signer.sign_request(
            method="GET",
            path="/health",
            body="string body",
        )
        assert "X-MLSDM-Signature" in headers
