"""
Tests for AES-256-GCM symmetric encryption functionality.

Verifies the AES-256-GCM implementation including:
- Key generation
- Encryption and decryption
- Associated data (AAD) support
- Key derivation functions (PBKDF2, scrypt)
- Error handling
- Security properties
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.crypto.symmetric import (
    AES_KEY_SIZE,
    GCM_NONCE_SIZE,
    GCM_TAG_SIZE,
    AESGCMCipher,
    SymmetricEncryptionError,
    decrypt_aes_gcm,
    derive_key_from_password,
    derive_key_scrypt,
    encrypt_aes_gcm,
    generate_aes_key,
)


class TestGenerateAESKey:
    """Tests for AES key generation."""

    def test_generate_key_default_size(self) -> None:
        """Generated key should be 32 bytes by default (AES-256)."""
        key = generate_aes_key()
        assert len(key) == 32

    def test_generate_key_various_sizes(self) -> None:
        """Should support AES-128, AES-192, and AES-256."""
        key_128 = generate_aes_key(16)
        key_192 = generate_aes_key(24)
        key_256 = generate_aes_key(32)

        assert len(key_128) == 16
        assert len(key_192) == 24
        assert len(key_256) == 32

    def test_generate_key_unique(self) -> None:
        """Each generated key should be unique."""
        keys = [generate_aes_key() for _ in range(10)]
        unique_keys = set(keys)
        assert len(unique_keys) == 10

    def test_generate_key_invalid_size(self) -> None:
        """Should reject invalid key sizes."""
        with pytest.raises(SymmetricEncryptionError, match="Invalid key length"):
            generate_aes_key(20)  # Invalid size

    def test_generate_key_bytes(self) -> None:
        """Generated key should be bytes."""
        key = generate_aes_key()
        assert isinstance(key, bytes)


class TestEncryptAESGCM:
    """Tests for AES-GCM encryption."""

    def test_encrypt_bytes(self) -> None:
        """Should encrypt bytes data."""
        key = generate_aes_key()
        plaintext = b"Hello, World!"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)

    def test_encrypt_string(self) -> None:
        """Should encrypt string data."""
        key = generate_aes_key()
        plaintext = "Hello, World!"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        assert isinstance(ciphertext, bytes)
        assert len(ciphertext) > len(plaintext)

    def test_encrypt_unicode(self) -> None:
        """Should encrypt unicode string."""
        key = generate_aes_key()
        plaintext = "Привіт, світ! 你好世界 🌍"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        assert isinstance(ciphertext, bytes)

    def test_encrypt_empty(self) -> None:
        """Should encrypt empty data."""
        key = generate_aes_key()
        ciphertext = encrypt_aes_gcm(b"", key)

        # Should still have nonce + tag
        assert len(ciphertext) >= GCM_NONCE_SIZE + GCM_TAG_SIZE

    def test_encrypt_large_data(self) -> None:
        """Should encrypt large data."""
        key = generate_aes_key()
        plaintext = b"x" * 1_000_000  # 1 MB

        ciphertext = encrypt_aes_gcm(plaintext, key)

        assert len(ciphertext) > len(plaintext)

    def test_encrypt_different_outputs(self) -> None:
        """Same plaintext should produce different ciphertext (different nonce)."""
        key = generate_aes_key()
        plaintext = b"test"

        ct1 = encrypt_aes_gcm(plaintext, key)
        ct2 = encrypt_aes_gcm(plaintext, key)

        assert ct1 != ct2  # Different nonces

    def test_encrypt_invalid_key_size(self) -> None:
        """Should reject invalid key sizes."""
        key = b"short"
        plaintext = b"test"

        with pytest.raises(SymmetricEncryptionError, match="Invalid key length"):
            encrypt_aes_gcm(plaintext, key)


class TestDecryptAESGCM:
    """Tests for AES-GCM decryption."""

    def test_decrypt_bytes(self) -> None:
        """Should decrypt to original bytes."""
        key = generate_aes_key()
        plaintext = b"Hello, World!"

        ciphertext = encrypt_aes_gcm(plaintext, key)
        decrypted = decrypt_aes_gcm(ciphertext, key, return_bytes=True)

        assert decrypted == plaintext

    def test_decrypt_string(self) -> None:
        """Should decrypt to string by default."""
        key = generate_aes_key()
        plaintext = "Hello, World!"

        ciphertext = encrypt_aes_gcm(plaintext, key)
        decrypted = decrypt_aes_gcm(ciphertext, key)

        assert decrypted == plaintext
        assert isinstance(decrypted, str)

    def test_decrypt_unicode(self) -> None:
        """Should decrypt unicode correctly."""
        key = generate_aes_key()
        plaintext = "Привіт, світ! 你好世界 🌍"

        ciphertext = encrypt_aes_gcm(plaintext, key)
        decrypted = decrypt_aes_gcm(ciphertext, key)

        assert decrypted == plaintext

    def test_decrypt_empty(self) -> None:
        """Should decrypt empty data."""
        key = generate_aes_key()

        ciphertext = encrypt_aes_gcm(b"", key)
        decrypted = decrypt_aes_gcm(ciphertext, key, return_bytes=True)

        assert decrypted == b""

    def test_decrypt_wrong_key(self) -> None:
        """Should fail with wrong key."""
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        plaintext = b"secret"

        ciphertext = encrypt_aes_gcm(plaintext, key1)

        with pytest.raises(SymmetricEncryptionError, match="Decryption failed"):
            decrypt_aes_gcm(ciphertext, key2)

    def test_decrypt_tampered_data(self) -> None:
        """Should fail with tampered ciphertext."""
        key = generate_aes_key()
        plaintext = b"secret"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[GCM_NONCE_SIZE] ^= 1  # Flip a bit
        tampered = bytes(tampered)

        with pytest.raises(SymmetricEncryptionError, match="Decryption failed"):
            decrypt_aes_gcm(tampered, key)

    def test_decrypt_truncated_data(self) -> None:
        """Should fail with truncated ciphertext."""
        key = generate_aes_key()

        with pytest.raises(SymmetricEncryptionError, match="too short"):
            decrypt_aes_gcm(b"short", key)

    def test_decrypt_invalid_key_size(self) -> None:
        """Should reject invalid key sizes."""
        key = generate_aes_key()
        plaintext = b"test"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        with pytest.raises(SymmetricEncryptionError, match="Invalid key length"):
            decrypt_aes_gcm(ciphertext, b"short")


class TestAssociatedData:
    """Tests for associated data (AAD) functionality."""

    def test_encrypt_with_aad(self) -> None:
        """Should encrypt with associated data."""
        key = generate_aes_key()
        plaintext = b"secret"
        aad = b"context:user123"

        ciphertext = encrypt_aes_gcm(plaintext, key, associated_data=aad)
        decrypted = decrypt_aes_gcm(ciphertext, key, associated_data=aad, return_bytes=True)

        assert decrypted == plaintext

    def test_decrypt_wrong_aad_fails(self) -> None:
        """Should fail with wrong associated data."""
        key = generate_aes_key()
        plaintext = b"secret"
        aad1 = b"context:user123"
        aad2 = b"context:user456"

        ciphertext = encrypt_aes_gcm(plaintext, key, associated_data=aad1)

        with pytest.raises(SymmetricEncryptionError, match="Decryption failed"):
            decrypt_aes_gcm(ciphertext, key, associated_data=aad2)

    def test_decrypt_missing_aad_fails(self) -> None:
        """Should fail if AAD was used but not provided for decryption."""
        key = generate_aes_key()
        plaintext = b"secret"
        aad = b"context:user123"

        ciphertext = encrypt_aes_gcm(plaintext, key, associated_data=aad)

        with pytest.raises(SymmetricEncryptionError, match="Decryption failed"):
            decrypt_aes_gcm(ciphertext, key)  # No AAD


class TestAESGCMCipher:
    """Tests for AESGCMCipher class."""

    def test_cipher_auto_key(self) -> None:
        """AESGCMCipher should auto-generate key if not provided."""
        cipher = AESGCMCipher()
        assert cipher.key is not None
        assert len(cipher.key) == 32

    def test_cipher_custom_key(self) -> None:
        """AESGCMCipher should use provided key."""
        key = generate_aes_key()
        cipher = AESGCMCipher(key=key)
        assert cipher.key == key

    def test_cipher_invalid_key(self) -> None:
        """AESGCMCipher should reject invalid key."""
        with pytest.raises(SymmetricEncryptionError, match="Invalid key length"):
            AESGCMCipher(key=b"short")

    def test_cipher_encrypt_decrypt(self) -> None:
        """AESGCMCipher should encrypt and decrypt correctly."""
        cipher = AESGCMCipher()
        plaintext = "test message"

        ciphertext = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_cipher_cross_instance(self) -> None:
        """Data encrypted by one instance should decrypt by another with same key."""
        key = generate_aes_key()
        cipher1 = AESGCMCipher(key=key)
        cipher2 = AESGCMCipher(key=key)

        plaintext = "shared secret"
        ciphertext = cipher1.encrypt(plaintext)
        decrypted = cipher2.decrypt(ciphertext)

        assert decrypted == plaintext

    def test_cipher_with_aad(self) -> None:
        """AESGCMCipher should support context-bound encryption."""
        cipher = AESGCMCipher()
        plaintext = "secret"
        context = "user:123"

        ciphertext, ctx = cipher.encrypt_with_aad(plaintext, context)
        decrypted = cipher.decrypt_with_aad(ciphertext, ctx)

        assert decrypted == plaintext

    def test_cipher_aad_wrong_context_fails(self) -> None:
        """AESGCMCipher should fail with wrong context."""
        cipher = AESGCMCipher()
        plaintext = "secret"

        ciphertext, _ = cipher.encrypt_with_aad(plaintext, "user:123")

        with pytest.raises(SymmetricEncryptionError):
            cipher.decrypt_with_aad(ciphertext, "user:456")


class TestKeyDerivation:
    """Tests for key derivation functions."""

    def test_pbkdf2_derive_key(self) -> None:
        """PBKDF2 should derive consistent key from password."""
        password = "mypassword"

        key1, salt = derive_key_from_password(password)
        key2, _ = derive_key_from_password(password, salt=salt)

        assert key1 == key2
        assert len(key1) == 32

    def test_pbkdf2_different_salts(self) -> None:
        """PBKDF2 should produce different keys with different salts."""
        password = "mypassword"

        key1, salt1 = derive_key_from_password(password)
        key2, salt2 = derive_key_from_password(password)

        assert salt1 != salt2
        assert key1 != key2

    def test_pbkdf2_different_passwords(self) -> None:
        """PBKDF2 should produce different keys for different passwords."""
        salt = b"fixed_salt_12345"

        key1, _ = derive_key_from_password("password1", salt=salt)
        key2, _ = derive_key_from_password("password2", salt=salt)

        assert key1 != key2

    def test_pbkdf2_custom_iterations(self) -> None:
        """PBKDF2 should accept custom iterations."""
        password = "mypassword"
        salt = b"fixed_salt_12345"

        key1, _ = derive_key_from_password(password, salt=salt, iterations=10_000)
        key2, _ = derive_key_from_password(password, salt=salt, iterations=20_000)

        assert key1 != key2

    def test_scrypt_derive_key(self) -> None:
        """scrypt should derive consistent key from password."""
        password = "mypassword"

        key1, salt = derive_key_scrypt(password)
        key2, _ = derive_key_scrypt(password, salt=salt)

        assert key1 == key2
        assert len(key1) == 32

    def test_scrypt_different_salts(self) -> None:
        """scrypt should produce different keys with different salts."""
        password = "mypassword"

        key1, salt1 = derive_key_scrypt(password)
        key2, salt2 = derive_key_scrypt(password)

        assert salt1 != salt2
        assert key1 != key2

    def test_scrypt_different_passwords(self) -> None:
        """scrypt should produce different keys for different passwords."""
        salt = b"fixed_salt_12345"

        key1, _ = derive_key_scrypt("password1", salt=salt)
        key2, _ = derive_key_scrypt("password2", salt=salt)

        assert key1 != key2


class TestSecurityProperties:
    """Tests for security properties of AES-GCM."""

    def test_ciphertext_indistinguishable(self) -> None:
        """Ciphertext should not reveal plaintext patterns."""
        key = generate_aes_key()

        # Encrypt repeated pattern
        ct1 = encrypt_aes_gcm(b"AAAA", key)
        ct2 = encrypt_aes_gcm(b"AAAA", key)

        # Should be different (different nonces)
        assert ct1 != ct2

    def test_nonce_uniqueness(self) -> None:
        """Each encryption should use unique nonce."""
        key = generate_aes_key()
        plaintext = b"test"

        nonces = []
        for _ in range(100):
            ct = encrypt_aes_gcm(plaintext, key)
            nonce = ct[:GCM_NONCE_SIZE]
            nonces.append(nonce)

        # All nonces should be unique
        assert len(set(nonces)) == 100

    def test_tag_verification(self) -> None:
        """Tampering with tag should fail decryption."""
        key = generate_aes_key()
        plaintext = b"secret"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        # Tamper with tag (last 16 bytes)
        tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])

        with pytest.raises(SymmetricEncryptionError):
            decrypt_aes_gcm(tampered, key)

    def test_nonce_tampering(self) -> None:
        """Tampering with nonce should fail decryption."""
        key = generate_aes_key()
        plaintext = b"secret"

        ciphertext = encrypt_aes_gcm(plaintext, key)

        # Tamper with nonce
        tampered = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]

        with pytest.raises(SymmetricEncryptionError):
            decrypt_aes_gcm(tampered, key)


class TestConstants:
    """Tests for module constants."""

    def test_aes_key_size(self) -> None:
        """AES_KEY_SIZE should be 32 (256 bits)."""
        assert AES_KEY_SIZE == 32

    def test_gcm_nonce_size(self) -> None:
        """GCM_NONCE_SIZE should be 12 (96 bits)."""
        assert GCM_NONCE_SIZE == 12

    def test_gcm_tag_size(self) -> None:
        """GCM_TAG_SIZE should be 16 (128 bits)."""
        assert GCM_TAG_SIZE == 16
