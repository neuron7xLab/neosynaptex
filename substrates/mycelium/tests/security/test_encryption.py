"""
Tests for data encryption functionality.

Verifies that sensitive data can be securely encrypted and decrypted.
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.security.encryption import (
    DataEncryptor,
    EncryptionError,
    decrypt_data,
    encrypt_data,
    generate_key,
)


class TestGenerateKey:
    """Tests for key generation."""

    def test_generate_key_length(self) -> None:
        """Generated key should be 32 bytes."""
        key = generate_key()
        assert len(key) == 32

    def test_generate_key_random(self) -> None:
        """Each generated key should be unique."""
        keys = [generate_key() for _ in range(10)]
        unique_keys = set(keys)
        assert len(unique_keys) == 10

    def test_generate_key_bytes(self) -> None:
        """Generated key should be bytes."""
        key = generate_key()
        assert isinstance(key, bytes)


class TestEncryptDecrypt:
    """Tests for encryption and decryption."""

    def test_encrypt_decrypt_string(self) -> None:
        """Encrypt and decrypt a string successfully."""
        key = generate_key()
        plaintext = "sensitive data"

        ciphertext = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, key)

        assert decrypted == plaintext

    def test_encrypt_decrypt_bytes(self) -> None:
        """Encrypt and decrypt bytes successfully."""
        key = generate_key()
        plaintext = b"binary data"

        ciphertext = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, key)

        assert decrypted == plaintext.decode("utf-8")

    def test_encrypt_decrypt_unicode(self) -> None:
        """Encrypt and decrypt unicode string successfully."""
        key = generate_key()
        plaintext = "Привіт, світ! 你好世界 🌍"

        ciphertext = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, key)

        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext(self) -> None:
        """Same plaintext should produce different ciphertext each time."""
        key = generate_key()
        plaintext = "test data"

        ciphertext1 = encrypt_data(plaintext, key)
        ciphertext2 = encrypt_data(plaintext, key)

        # Same plaintext should decrypt to same result
        assert decrypt_data(ciphertext1, key) == decrypt_data(ciphertext2, key)
        # But ciphertext should be different due to random IV/salt
        assert ciphertext1 != ciphertext2

    def test_encrypt_decrypt_with_aad(self) -> None:
        """AAD should be required to decrypt when provided."""
        key = generate_key()
        plaintext = "context bound"
        aad = "session-123"

        ciphertext = encrypt_data(plaintext, key, associated_data=aad)
        decrypted = decrypt_data(ciphertext, key, associated_data=aad)

        assert decrypted == plaintext

        with pytest.raises(EncryptionError, match="authentication error"):
            decrypt_data(ciphertext, key, associated_data="wrong-aad")

    def test_ciphertext_is_base64(self) -> None:
        """Ciphertext should be URL-safe base64 encoded."""
        key = generate_key()
        plaintext = "test"

        ciphertext = encrypt_data(plaintext, key)

        # Should be ASCII (base64)
        assert ciphertext.isascii()
        # Should not contain characters that aren't URL-safe
        assert "+" not in ciphertext
        assert "/" not in ciphertext

    def test_decrypt_wrong_key_fails(self) -> None:
        """Decryption with wrong key should fail."""
        key1 = generate_key()
        key2 = generate_key()
        plaintext = "secret"

        ciphertext = encrypt_data(plaintext, key1)

        with pytest.raises(EncryptionError, match="authentication error"):
            decrypt_data(ciphertext, key2)

    def test_decrypt_tampered_data_fails(self) -> None:
        """Decryption of tampered data should fail."""
        key = generate_key()
        plaintext = "secret"

        ciphertext = encrypt_data(plaintext, key)
        # Tamper with the ciphertext
        tampered = ciphertext[:-5] + "XXXXX"

        with pytest.raises(EncryptionError):
            decrypt_data(tampered, key)

    def test_decrypt_invalid_base64_fails(self) -> None:
        """Decryption of invalid base64 should fail."""
        key = generate_key()

        with pytest.raises(EncryptionError):
            decrypt_data("not valid base64!!!", key)

    def test_decrypt_short_data_fails(self) -> None:
        """Decryption of too-short data should fail."""
        key = generate_key()

        with pytest.raises(EncryptionError, match="too short"):
            decrypt_data("dG9vIHNob3J0", key)  # "too short" in base64

    def test_empty_string_encryption(self) -> None:
        """Empty string should encrypt and decrypt correctly."""
        key = generate_key()
        plaintext = ""

        ciphertext = encrypt_data(plaintext, key)
        decrypted = decrypt_data(ciphertext, key)

        assert decrypted == plaintext

    def test_encrypt_rejects_short_key(self) -> None:
        """Encryption should fail fast when key length is insufficient."""
        with pytest.raises(EncryptionError, match="exactly 32 bytes"):
            encrypt_data("data", b"short-key")

    def test_encrypt_rejects_wrong_key_type(self) -> None:
        """Encryption should validate key type is bytes-like."""
        with pytest.raises(EncryptionError, match="must be bytes"):
            encrypt_data("data", "not-bytes")  # type: ignore[arg-type]


class TestDataEncryptor:
    """Tests for DataEncryptor class."""

    def test_encryptor_auto_key(self) -> None:
        """DataEncryptor should auto-generate key if not provided."""
        encryptor = DataEncryptor()
        assert encryptor.key is not None
        assert len(encryptor.key) == 32

    def test_encryptor_custom_key(self) -> None:
        """DataEncryptor should use provided key."""
        key = generate_key()
        encryptor = DataEncryptor(key=key)
        assert encryptor.key == key

    def test_encryptor_encrypt_decrypt(self) -> None:
        """DataEncryptor should encrypt and decrypt correctly."""
        encryptor = DataEncryptor()
        plaintext = "test data"

        ciphertext = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryptor_cross_instance(self) -> None:
        """Data encrypted by one instance should decrypt by another with same key."""
        key = generate_key()
        encryptor1 = DataEncryptor(key=key)
        encryptor2 = DataEncryptor(key=key)

        plaintext = "shared secret"
        ciphertext = encryptor1.encrypt(plaintext)
        decrypted = encryptor2.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_encryptor_rejects_short_custom_key(self) -> None:
        """Custom keys must meet minimum length requirements."""
        with pytest.raises(EncryptionError, match="exactly 32 bytes"):
            DataEncryptor(key=b"too-short-key")
