"""
Tests for Crypto API endpoints.

Verifies the cryptographic API endpoints:
- POST /api/encrypt
- POST /api/decrypt
- POST /api/sign
- POST /api/verify
- POST /api/keypair

Reference: docs/MFN_CRYPTOGRAPHY.md, Step 4: API Integration
"""

from __future__ import annotations

import base64
import os
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from mycelium_fractal_net.integration import (
    reset_config,
    reset_crypto_config,
    reset_key_store,
)


@pytest.fixture(autouse=True)
def reset_all_configs():
    """Reset all configs before and after each test."""
    reset_config()
    reset_crypto_config()
    reset_key_store()
    yield
    reset_config()
    reset_crypto_config()
    reset_key_store()


@pytest.fixture
def client():
    """Create test client with crypto enabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_CRYPTO_ENABLED": "true",
        },
        clear=False,
    ):
        reset_config()
        reset_crypto_config()
        reset_key_store()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


@pytest.fixture
def crypto_disabled_client():
    """Create test client with crypto disabled."""
    with mock.patch.dict(
        os.environ,
        {
            "MFN_ENV": "dev",
            "MFN_API_KEY_REQUIRED": "false",
            "MFN_RATE_LIMIT_ENABLED": "false",
            "MFN_CRYPTO_ENABLED": "false",
        },
        clear=False,
    ):
        reset_config()
        reset_crypto_config()
        reset_key_store()
        from mycelium_fractal_net.api import app

        yield TestClient(app)


class TestEncryptEndpoint:
    """Tests for POST /api/encrypt endpoint."""

    def test_encrypt_basic(self, client: TestClient) -> None:
        """Should encrypt base64-encoded plaintext."""
        plaintext = b"Hello, World!"
        plaintext_b64 = base64.b64encode(plaintext).decode("ascii")

        response = client.post(
            "/api/encrypt",
            json={"plaintext": plaintext_b64},
        )

        assert response.status_code == 200
        data = response.json()
        assert "ciphertext" in data
        assert "key_id" in data
        assert data["algorithm"] == "AES-256-GCM"

        # Ciphertext should be different from plaintext
        ciphertext = base64.b64decode(data["ciphertext"])
        assert ciphertext != plaintext

    def test_encrypt_with_aad(self, client: TestClient) -> None:
        """Should encrypt with associated data."""
        plaintext = b"secret data"
        plaintext_b64 = base64.b64encode(plaintext).decode("ascii")
        aad = b"context:user123"
        aad_b64 = base64.b64encode(aad).decode("ascii")

        response = client.post(
            "/api/encrypt",
            json={
                "plaintext": plaintext_b64,
                "associated_data": aad_b64,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "ciphertext" in data

    def test_encrypt_invalid_base64(self, client: TestClient) -> None:
        """Should reject invalid base64 input."""
        response = client.post(
            "/api/encrypt",
            json={"plaintext": "not-valid-base64!!!"},
        )

        assert response.status_code == 400

    def test_encrypt_empty_plaintext_rejected(self, client: TestClient) -> None:
        """Should reject empty plaintext."""
        response = client.post(
            "/api/encrypt",
            json={"plaintext": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_encrypt_when_disabled(self, crypto_disabled_client: TestClient) -> None:
        """Should return 503 when crypto is disabled."""
        plaintext_b64 = base64.b64encode(b"test").decode("ascii")

        response = crypto_disabled_client.post(
            "/api/encrypt",
            json={"plaintext": plaintext_b64},
        )

        assert response.status_code == 503


class TestDecryptEndpoint:
    """Tests for POST /api/decrypt endpoint."""

    def test_decrypt_basic(self, client: TestClient) -> None:
        """Should decrypt previously encrypted data."""
        plaintext = b"Hello, Decrypt!"
        plaintext_b64 = base64.b64encode(plaintext).decode("ascii")

        # First encrypt
        encrypt_response = client.post(
            "/api/encrypt",
            json={"plaintext": plaintext_b64},
        )
        assert encrypt_response.status_code == 200
        encrypt_data = encrypt_response.json()

        # Then decrypt
        decrypt_response = client.post(
            "/api/decrypt",
            json={
                "ciphertext": encrypt_data["ciphertext"],
                "key_id": encrypt_data["key_id"],
            },
        )

        assert decrypt_response.status_code == 200
        decrypt_data = decrypt_response.json()
        decrypted = base64.b64decode(decrypt_data["plaintext"])
        assert decrypted == plaintext

    def test_decrypt_with_aad(self, client: TestClient) -> None:
        """Should decrypt with correct associated data."""
        plaintext = b"secret with context"
        plaintext_b64 = base64.b64encode(plaintext).decode("ascii")
        aad = b"context:session456"
        aad_b64 = base64.b64encode(aad).decode("ascii")

        # Encrypt with AAD
        encrypt_response = client.post(
            "/api/encrypt",
            json={
                "plaintext": plaintext_b64,
                "associated_data": aad_b64,
            },
        )
        assert encrypt_response.status_code == 200
        encrypt_data = encrypt_response.json()

        # Decrypt with same AAD
        decrypt_response = client.post(
            "/api/decrypt",
            json={
                "ciphertext": encrypt_data["ciphertext"],
                "key_id": encrypt_data["key_id"],
                "associated_data": aad_b64,
            },
        )

        assert decrypt_response.status_code == 200
        decrypt_data = decrypt_response.json()
        decrypted = base64.b64decode(decrypt_data["plaintext"])
        assert decrypted == plaintext

    def test_decrypt_wrong_aad_fails(self, client: TestClient) -> None:
        """Should fail to decrypt with wrong associated data."""
        plaintext = b"secret"
        plaintext_b64 = base64.b64encode(plaintext).decode("ascii")
        aad1 = base64.b64encode(b"context:user1").decode("ascii")
        aad2 = base64.b64encode(b"context:user2").decode("ascii")

        # Encrypt with aad1
        encrypt_response = client.post(
            "/api/encrypt",
            json={
                "plaintext": plaintext_b64,
                "associated_data": aad1,
            },
        )
        encrypt_data = encrypt_response.json()

        # Decrypt with aad2 - should fail
        decrypt_response = client.post(
            "/api/decrypt",
            json={
                "ciphertext": encrypt_data["ciphertext"],
                "key_id": encrypt_data["key_id"],
                "associated_data": aad2,
            },
        )

        assert decrypt_response.status_code == 400

    def test_decrypt_invalid_ciphertext(self, client: TestClient) -> None:
        """Should fail with invalid ciphertext."""
        # First encrypt something to get a valid key_id
        plaintext_b64 = base64.b64encode(b"test").decode("ascii")
        encrypt_response = client.post(
            "/api/encrypt",
            json={"plaintext": plaintext_b64},
        )
        key_id = encrypt_response.json()["key_id"]

        # Try to decrypt garbage
        garbage = base64.b64encode(b"invalid ciphertext data").decode("ascii")
        decrypt_response = client.post(
            "/api/decrypt",
            json={
                "ciphertext": garbage,
                "key_id": key_id,
            },
        )

        assert decrypt_response.status_code == 400


class TestSignEndpoint:
    """Tests for POST /api/sign endpoint."""

    def test_sign_basic(self, client: TestClient) -> None:
        """Should sign a message."""
        message = b"Sign this message"
        message_b64 = base64.b64encode(message).decode("ascii")

        response = client.post(
            "/api/sign",
            json={"message": message_b64},
        )

        assert response.status_code == 200
        data = response.json()
        assert "signature" in data
        assert "key_id" in data
        assert data["algorithm"] == "Ed25519"

        # Signature should be 64 bytes for Ed25519
        signature = base64.b64decode(data["signature"])
        assert len(signature) == 64

    def test_sign_with_key_id(self, client: TestClient) -> None:
        """Should sign using the same key when key_id is provided."""
        message = b"test message"
        message_b64 = base64.b64encode(message).decode("ascii")

        # First sign to get a key_id
        response1 = client.post(
            "/api/sign",
            json={"message": message_b64},
        )
        key_id = response1.json()["key_id"]

        # Sign again with same key_id
        response2 = client.post(
            "/api/sign",
            json={"message": message_b64, "key_id": key_id},
        )

        assert response2.status_code == 200
        # Same key should produce same signature for same message
        assert response1.json()["signature"] == response2.json()["signature"]


class TestVerifyEndpoint:
    """Tests for POST /api/verify endpoint."""

    def test_verify_valid_signature(self, client: TestClient) -> None:
        """Should verify a valid signature."""
        message = b"Verify this message"
        message_b64 = base64.b64encode(message).decode("ascii")

        # First sign
        sign_response = client.post(
            "/api/sign",
            json={"message": message_b64},
        )
        sign_data = sign_response.json()

        # Then verify
        verify_response = client.post(
            "/api/verify",
            json={
                "message": message_b64,
                "signature": sign_data["signature"],
                "key_id": sign_data["key_id"],
            },
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["valid"] is True

    def test_verify_invalid_signature(self, client: TestClient) -> None:
        """Should detect invalid signature."""
        message = b"Original message"
        message_b64 = base64.b64encode(message).decode("ascii")

        # Sign original message
        sign_response = client.post(
            "/api/sign",
            json={"message": message_b64},
        )
        sign_data = sign_response.json()

        # Try to verify with different message
        different_message = b"Different message"
        different_b64 = base64.b64encode(different_message).decode("ascii")

        verify_response = client.post(
            "/api/verify",
            json={
                "message": different_b64,
                "signature": sign_data["signature"],
                "key_id": sign_data["key_id"],
            },
        )

        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["valid"] is False

    def test_verify_with_public_key(self, client: TestClient) -> None:
        """Should verify using provided public key."""
        # Generate a keypair first
        keypair_response = client.post(
            "/api/keypair",
            json={"algorithm": "Ed25519"},
        )
        keypair_data = keypair_response.json()

        # Sign a message
        message = b"test message"
        message_b64 = base64.b64encode(message).decode("ascii")

        sign_response = client.post(
            "/api/sign",
            json={
                "message": message_b64,
                "key_id": keypair_data["key_id"],
            },
        )
        sign_data = sign_response.json()

        # Verify with public key instead of key_id
        verify_response = client.post(
            "/api/verify",
            json={
                "message": message_b64,
                "signature": sign_data["signature"],
                "public_key": keypair_data["public_key"],
            },
        )

        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] is True


class TestKeypairEndpoint:
    """Tests for POST /api/keypair endpoint."""

    def test_generate_ed25519_keypair(self, client: TestClient) -> None:
        """Should generate Ed25519 key pair."""
        response = client.post(
            "/api/keypair",
            json={"algorithm": "Ed25519"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "key_id" in data
        assert "public_key" in data
        assert data["algorithm"] == "Ed25519"

        # Ed25519 public key is 32 bytes
        public_key = base64.b64decode(data["public_key"])
        assert len(public_key) == 32

    def test_generate_ecdh_keypair(self, client: TestClient) -> None:
        """Should generate ECDH (X25519) key pair."""
        response = client.post(
            "/api/keypair",
            json={"algorithm": "ECDH"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "key_id" in data
        assert "public_key" in data
        assert data["algorithm"] == "ECDH"

        # X25519 public key is 32 bytes
        public_key = base64.b64decode(data["public_key"])
        assert len(public_key) == 32

    def test_generate_with_custom_key_id(self, client: TestClient) -> None:
        """Should use provided key_id."""
        custom_id = "my-custom-key-id"

        response = client.post(
            "/api/keypair",
            json={
                "algorithm": "Ed25519",
                "key_id": custom_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key_id"] == custom_id

    def test_generate_invalid_algorithm(self, client: TestClient) -> None:
        """Should reject invalid algorithm."""
        response = client.post(
            "/api/keypair",
            json={"algorithm": "RSA-2048"},  # Not supported
        )

        assert response.status_code == 422  # Validation error


class TestCryptoToggle:
    """Tests for crypto enable/disable toggle."""

    def test_all_endpoints_disabled(self, crypto_disabled_client: TestClient) -> None:
        """All crypto endpoints should return 503 when disabled."""
        # Use properly sized mock values for validation
        plaintext_b64 = base64.b64encode(b"test data for encryption").decode("ascii")
        # Mock ciphertext (needs to be at least nonce + tag = 28 bytes)
        mock_ciphertext = base64.b64encode(b"x" * 30).decode("ascii")
        # Mock signature (Ed25519 signature is 64 bytes)
        mock_signature = base64.b64encode(b"s" * 64).decode("ascii")
        # Mock public key (Ed25519 public key is 32 bytes)
        mock_pubkey = base64.b64encode(b"p" * 32).decode("ascii")

        endpoints = [
            ("/api/encrypt", {"plaintext": plaintext_b64}),
            ("/api/decrypt", {"ciphertext": mock_ciphertext}),
            ("/api/sign", {"message": plaintext_b64}),
            (
                "/api/verify",
                {
                    "message": plaintext_b64,
                    "signature": mock_signature,
                    "public_key": mock_pubkey,
                },
            ),
            ("/api/keypair", {"algorithm": "Ed25519"}),
        ]

        for endpoint, body in endpoints:
            response = crypto_disabled_client.post(endpoint, json=body)
            assert response.status_code == 503, f"Endpoint {endpoint} should be disabled"
