"""
Tests for Ed25519 digital signature functionality.

Verifies the Ed25519 signature implementation including:
- Key generation
- Message signing
- Signature verification
- Error handling
- Security properties
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.crypto.signatures import (
    EdDSASignature,
    SignatureError,
    SignatureKeyPair,
    generate_signature_keypair,
    sign_message,
    verify_signature,
)


class TestGenerateSignatureKeypair:
    """Tests for Ed25519 key pair generation."""

    def test_generate_keypair_sizes(self) -> None:
        """Generated keys should be 32 bytes each."""
        keypair = generate_signature_keypair()
        assert len(keypair.private_key) == 32
        assert len(keypair.public_key) == 32

    def test_generate_keypair_unique(self) -> None:
        """Each generated keypair should be unique."""
        keypairs = [generate_signature_keypair() for _ in range(10)]
        private_keys = [k.private_key for k in keypairs]
        public_keys = [k.public_key for k in keypairs]
        assert len(set(private_keys)) == 10
        assert len(set(public_keys)) == 10

    def test_keypair_types(self) -> None:
        """Keys should be bytes."""
        keypair = generate_signature_keypair()
        assert isinstance(keypair.private_key, bytes)
        assert isinstance(keypair.public_key, bytes)

    def test_keypair_validation(self) -> None:
        """SignatureKeyPair should validate key sizes."""
        with pytest.raises(SignatureError, match="Private key must be 32 bytes"):
            SignatureKeyPair(private_key=b"short", public_key=b"x" * 32)

        with pytest.raises(SignatureError, match="Public key must be 32 bytes"):
            SignatureKeyPair(private_key=b"x" * 32, public_key=b"short")


class TestSignMessage:
    """Tests for message signing."""

    def test_sign_message_bytes(self) -> None:
        """Should sign bytes message."""
        keypair = generate_signature_keypair()
        signature = sign_message(b"Hello, World!", keypair.private_key)
        assert len(signature) == 64

    def test_sign_message_string(self) -> None:
        """Should sign string message."""
        keypair = generate_signature_keypair()
        signature = sign_message("Hello, World!", keypair.private_key)
        assert len(signature) == 64

    def test_sign_message_unicode(self) -> None:
        """Should sign unicode message."""
        keypair = generate_signature_keypair()
        signature = sign_message("Привіт, світ! 你好世界 🌍", keypair.private_key)
        assert len(signature) == 64

    def test_sign_empty_message(self) -> None:
        """Should sign empty message."""
        keypair = generate_signature_keypair()
        signature = sign_message(b"", keypair.private_key)
        assert len(signature) == 64

    def test_sign_large_message(self) -> None:
        """Should sign large message."""
        keypair = generate_signature_keypair()
        message = b"x" * 10000
        signature = sign_message(message, keypair.private_key)
        assert len(signature) == 64

    def test_sign_deterministic(self) -> None:
        """Same message and key should produce same signature."""
        keypair = generate_signature_keypair()
        sig1 = sign_message(b"test", keypair.private_key)
        sig2 = sign_message(b"test", keypair.private_key)
        assert sig1 == sig2

    def test_sign_different_messages(self) -> None:
        """Different messages should produce different signatures."""
        keypair = generate_signature_keypair()
        sig1 = sign_message(b"message1", keypair.private_key)
        sig2 = sign_message(b"message2", keypair.private_key)
        assert sig1 != sig2

    def test_sign_different_keys(self) -> None:
        """Different keys should produce different signatures."""
        keypair1 = generate_signature_keypair()
        keypair2 = generate_signature_keypair()
        sig1 = sign_message(b"test", keypair1.private_key)
        sig2 = sign_message(b"test", keypair2.private_key)
        assert sig1 != sig2

    def test_sign_invalid_key_size(self) -> None:
        """Should reject invalid private key size."""
        with pytest.raises(SignatureError, match="Private key must be 32 bytes"):
            sign_message(b"test", b"short key")


class TestVerifySignature:
    """Tests for signature verification."""

    def test_verify_valid_signature(self) -> None:
        """Should verify valid signature."""
        keypair = generate_signature_keypair()
        message = b"Hello, World!"
        signature = sign_message(message, keypair.private_key)

        assert verify_signature(message, signature, keypair.public_key) is True

    def test_verify_string_message(self) -> None:
        """Should verify signature on string message."""
        keypair = generate_signature_keypair()
        message = "Hello, World!"
        signature = sign_message(message, keypair.private_key)

        assert verify_signature(message, signature, keypair.public_key) is True

    def test_verify_unicode_message(self) -> None:
        """Should verify signature on unicode message."""
        keypair = generate_signature_keypair()
        message = "Привіт, світ! 🌍"
        signature = sign_message(message, keypair.private_key)

        assert verify_signature(message, signature, keypair.public_key) is True

    def test_verify_empty_message(self) -> None:
        """Should verify signature on empty message."""
        keypair = generate_signature_keypair()
        message = b""
        signature = sign_message(message, keypair.private_key)

        assert verify_signature(message, signature, keypair.public_key) is True

    def test_reject_wrong_message(self) -> None:
        """Should reject signature for different message."""
        keypair = generate_signature_keypair()
        signature = sign_message(b"original", keypair.private_key)

        assert verify_signature(b"modified", signature, keypair.public_key) is False

    def test_reject_wrong_public_key(self) -> None:
        """Should reject signature with wrong public key."""
        keypair1 = generate_signature_keypair()
        keypair2 = generate_signature_keypair()

        signature = sign_message(b"test", keypair1.private_key)

        assert verify_signature(b"test", signature, keypair2.public_key) is False

    def test_reject_tampered_signature(self) -> None:
        """Should reject tampered signature."""
        keypair = generate_signature_keypair()
        message = b"test"
        signature = sign_message(message, keypair.private_key)

        # Tamper with signature
        tampered = bytes([signature[0] ^ 1]) + signature[1:]

        assert verify_signature(message, tampered, keypair.public_key) is False

    def test_reject_invalid_signature_size(self) -> None:
        """Should reject signature of wrong size."""
        keypair = generate_signature_keypair()

        assert verify_signature(b"test", b"short", keypair.public_key) is False
        assert verify_signature(b"test", b"x" * 100, keypair.public_key) is False

    def test_reject_invalid_public_key_size(self) -> None:
        """Should reject public key of wrong size."""
        keypair = generate_signature_keypair()
        signature = sign_message(b"test", keypair.private_key)

        assert verify_signature(b"test", signature, b"short") is False


class TestEdDSASignature:
    """Tests for EdDSASignature class."""

    def test_auto_generate_keypair(self) -> None:
        """Should auto-generate keypair if not provided."""
        signer = EdDSASignature()
        assert len(signer.public_key) == 32
        assert len(signer.private_key) == 32

    def test_use_provided_keypair(self) -> None:
        """Should use provided keypair."""
        keypair = generate_signature_keypair()
        signer = EdDSASignature(keypair)

        assert signer.public_key == keypair.public_key
        assert signer.private_key == keypair.private_key

    def test_sign_and_verify(self) -> None:
        """Should sign and verify messages."""
        signer = EdDSASignature()
        message = b"test message"

        signature = signer.sign(message)
        assert signer.verify(message, signature) is True

    def test_verify_with_explicit_key(self) -> None:
        """Should verify with explicitly provided public key."""
        signer1 = EdDSASignature()
        signer2 = EdDSASignature()

        message = b"test"
        signature = signer1.sign(message)

        # Verify with own key
        assert signer1.verify(message, signature) is True

        # Verify with other's key should fail
        assert signer1.verify(message, signature, signer2.public_key) is False

    def test_cross_instance_verification(self) -> None:
        """Signature from one instance should verify with another using same key."""
        keypair = generate_signature_keypair()
        signer1 = EdDSASignature(keypair)
        signer2 = EdDSASignature(keypair)

        message = b"shared secret"
        signature = signer1.sign(message)

        assert signer2.verify(message, signature) is True


class TestSecurityProperties:
    """Tests for security properties of Ed25519 implementation."""

    def test_signature_non_malleability(self) -> None:
        """Each message should have exactly one valid signature per key."""
        keypair = generate_signature_keypair()
        message = b"test"

        # Sign multiple times - should always be the same
        signatures = [sign_message(message, keypair.private_key) for _ in range(5)]

        assert len(set(signatures)) == 1  # All signatures should be identical

    def test_no_signature_reuse(self) -> None:
        """Signature for one message should not work for another."""
        keypair = generate_signature_keypair()

        sig1 = sign_message(b"message1", keypair.private_key)
        sig2 = sign_message(b"message2", keypair.private_key)

        # Cross-verify should fail
        assert verify_signature(b"message2", sig1, keypair.public_key) is False
        assert verify_signature(b"message1", sig2, keypair.public_key) is False

    def test_public_key_independence(self) -> None:
        """Different keys should produce independent signatures."""
        keypair1 = generate_signature_keypair()
        keypair2 = generate_signature_keypair()
        message = b"test"

        sig1 = sign_message(message, keypair1.private_key)
        sig2 = sign_message(message, keypair2.private_key)

        # Each signature should only verify with its own key
        assert verify_signature(message, sig1, keypair1.public_key) is True
        assert verify_signature(message, sig2, keypair2.public_key) is True
        assert verify_signature(message, sig1, keypair2.public_key) is False
        assert verify_signature(message, sig2, keypair1.public_key) is False

    def test_signature_components_independent(self) -> None:
        """Both R and S components should be needed for valid signature."""
        keypair = generate_signature_keypair()
        message = b"test"
        signature = sign_message(message, keypair.private_key)

        # Modify only R component
        modified_r = bytes([signature[0] ^ 1]) + signature[1:]
        assert verify_signature(message, modified_r, keypair.public_key) is False

        # Modify only S component
        modified_s = signature[:32] + bytes([signature[32] ^ 1]) + signature[33:]
        assert verify_signature(message, modified_s, keypair.public_key) is False
