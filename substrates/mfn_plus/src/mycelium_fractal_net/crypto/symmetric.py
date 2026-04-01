"""
AES-256-GCM Symmetric Encryption Module.

This module implements authenticated symmetric encryption using AES-256-GCM,
providing both confidentiality and integrity protection for sensitive data.

Mathematical Foundation:
========================

**AES-256 (Advanced Encryption Standard):**

AES is a symmetric block cipher operating on 128-bit blocks with a 256-bit key.
The cipher uses 14 rounds of:
- SubBytes: Non-linear substitution using an S-box
- ShiftRows: Cyclical byte rotation
- MixColumns: Matrix multiplication in GF(2^8)
- AddRoundKey: XOR with round key

**GCM (Galois/Counter Mode):**

GCM provides authenticated encryption with associated data (AEAD):
- Counter mode (CTR) for encryption: Cᵢ = Pᵢ ⊕ E(K, IV || i)
- GHASH for authentication: Tag = GHASH(H, A, C) ⊕ E(K, IV || 0)

Security Properties:
    - 256-bit key provides 256-bit security against brute force
    - GCM provides IND-CPA and INT-CTXT security
    - Authentication tag detects any modification
    - Each (key, nonce) pair must be unique

Standards Compliance:
    - NIST SP 800-38D (GCM specification)
    - NIST FIPS 197 (AES specification)
    - RFC 5116 (AEAD interface)

Usage:
    >>> from mycelium_fractal_net.crypto.symmetric import (
    ...     AESGCMCipher,
    ...     encrypt_aes_gcm,
    ...     decrypt_aes_gcm,
    ...     generate_aes_key,
    ... )
    >>> key = generate_aes_key()
    >>> ciphertext = encrypt_aes_gcm(b"secret message", key)
    >>> plaintext = decrypt_aes_gcm(ciphertext, key)

Reference: docs/MFN_CRYPTOGRAPHY.md
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class SymmetricEncryptionError(Exception):
    """Raised when symmetric encryption operation fails."""


# Constants
AES_KEY_SIZE = 32  # 256 bits
GCM_NONCE_SIZE = 12  # 96 bits (recommended for GCM)
GCM_TAG_SIZE = 16  # 128 bits (default for AESGCM)


def generate_aes_key(length: int = AES_KEY_SIZE) -> bytes:
    """
    Generate a cryptographically secure AES key.

    Uses Python's secrets module for cryptographically secure
    random number generation.

    Args:
        length: Key length in bytes (default: 32 for AES-256).

    Returns:
        bytes: Random key of specified length.

    Raises:
        SymmetricEncryptionError: If key length is invalid.

    Security Note:
        The key must be stored securely and never logged or exposed.
        Consider using a Key Management System (KMS) in production.

    Example:
        >>> key = generate_aes_key()
        >>> len(key) == 32
        True
    """
    if length not in (16, 24, 32):
        raise SymmetricEncryptionError(
            f"Invalid key length: {length}. Must be 16, 24, or 32 bytes."
        )
    return secrets.token_bytes(length)


def _generate_nonce() -> bytes:
    """
    Generate a random 96-bit nonce for GCM.

    NIST SP 800-38D recommends 96-bit nonces for GCM mode.
    Each nonce must be unique for a given key.

    Returns:
        bytes: 12-byte random nonce.
    """
    return os.urandom(GCM_NONCE_SIZE)


def encrypt_aes_gcm(
    plaintext: Union[bytes, str],
    key: bytes,
    associated_data: bytes | None = None,
    encoding: str = "utf-8",
) -> bytes:
    """
    Encrypt data using AES-256-GCM.

    Provides authenticated encryption with associated data (AEAD).
    The nonce is prepended to the ciphertext for decryption.

    Format: nonce (12 bytes) || ciphertext || tag (16 bytes)

    Args:
        plaintext: Data to encrypt (bytes or string).
        key: 32-byte AES-256 key.
        associated_data: Optional additional authenticated data (AAD).
        encoding: String encoding (default: utf-8).

    Returns:
        bytes: Nonce + encrypted data + authentication tag.

    Raises:
        SymmetricEncryptionError: If encryption fails.

    Security Properties:
        - Confidentiality: AES-256 in counter mode
        - Integrity: 128-bit authentication tag
        - Authenticity: Covers both ciphertext and AAD

    Example:
        >>> key = generate_aes_key()
        >>> ciphertext = encrypt_aes_gcm(b"secret", key)
        >>> len(ciphertext) > len(b"secret")
        True
    """
    try:
        # Convert string to bytes
        if isinstance(plaintext, str):
            plaintext = plaintext.encode(encoding)

        # Validate key
        if len(key) not in (16, 24, 32):
            raise SymmetricEncryptionError(
                f"Invalid key length: {len(key)}. Must be 16, 24, or 32 bytes."
            )

        # Generate random nonce
        nonce = _generate_nonce()

        # Create cipher and encrypt
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

        # Return nonce || ciphertext (tag is appended by AESGCM)
        return nonce + ciphertext

    except SymmetricEncryptionError:
        raise
    except Exception as e:
        raise SymmetricEncryptionError(f"Encryption failed: {e}") from e


def decrypt_aes_gcm(
    ciphertext: bytes,
    key: bytes,
    associated_data: bytes | None = None,
    encoding: str = "utf-8",
    return_bytes: bool = False,
) -> Union[bytes, str]:
    """
    Decrypt AES-256-GCM encrypted data.

    Verifies the authentication tag before returning plaintext.
    Raises an error if authentication fails (tampered data).

    Args:
        ciphertext: Encrypted data (nonce + ciphertext + tag).
        key: 32-byte AES-256 key (same as used for encryption).
        associated_data: Optional AAD (must match encryption).
        encoding: String encoding for result (default: utf-8).
        return_bytes: If True, return bytes instead of string.

    Returns:
        Decrypted plaintext as string or bytes.

    Raises:
        SymmetricEncryptionError: If decryption or authentication fails.

    Security Note:
        Authentication failure indicates potential tampering or
        use of incorrect key. Never ignore this error.

    Example:
        >>> key = generate_aes_key()
        >>> ct = encrypt_aes_gcm(b"secret", key)
        >>> decrypt_aes_gcm(ct, key, return_bytes=True)
        b'secret'
    """
    try:
        # Validate minimum length: nonce (12) + tag (16) = 28 bytes minimum
        if len(ciphertext) < GCM_NONCE_SIZE + GCM_TAG_SIZE:
            raise SymmetricEncryptionError(
                f"Ciphertext too short: {len(ciphertext)} bytes. "
                f"Minimum is {GCM_NONCE_SIZE + GCM_TAG_SIZE} bytes."
            )

        # Validate key
        if len(key) not in (16, 24, 32):
            raise SymmetricEncryptionError(
                f"Invalid key length: {len(key)}. Must be 16, 24, or 32 bytes."
            )

        # Extract nonce and encrypted data
        nonce = ciphertext[:GCM_NONCE_SIZE]
        encrypted_data = ciphertext[GCM_NONCE_SIZE:]

        # Decrypt and verify
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, encrypted_data, associated_data)

        if return_bytes:
            return plaintext
        return plaintext.decode(encoding)

    except SymmetricEncryptionError:
        raise
    except Exception as e:
        # Authentication failure or decryption error
        raise SymmetricEncryptionError(
            f"Decryption failed (possible tampering or wrong key): {e}"
        ) from e


@dataclass
class AESGCMCipher:
    """
    Stateful AES-256-GCM cipher with key management.

    Provides a high-level interface for authenticated encryption
    with automatic key and nonce management.

    Security Properties:
        - IND-CPA (Indistinguishability under chosen-plaintext attack)
        - INT-CTXT (Ciphertext integrity)
        - Key separation via optional context/associated data

    Attributes:
        key: 32-byte AES-256 encryption key.

    Example:
        >>> cipher = AESGCMCipher()
        >>> ct = cipher.encrypt("secret message")
        >>> cipher.decrypt(ct)
        'secret message'
    """

    key: bytes

    def __init__(self, key: bytes | None = None) -> None:
        """
        Initialize cipher with optional existing key.

        Args:
            key: 32-byte AES key. If None, generates a new key.

        Raises:
            SymmetricEncryptionError: If key length is invalid.
        """
        if key is None:
            self.key = generate_aes_key()
        else:
            if len(key) not in (16, 24, 32):
                raise SymmetricEncryptionError(
                    f"Invalid key length: {len(key)}. Must be 16, 24, or 32 bytes."
                )
            self.key = key

    def encrypt(
        self,
        plaintext: Union[bytes, str],
        associated_data: bytes | None = None,
    ) -> bytes:
        """
        Encrypt data using AES-256-GCM.

        Args:
            plaintext: Data to encrypt.
            associated_data: Optional additional authenticated data.

        Returns:
            bytes: Encrypted data with nonce and tag.

        Example:
            >>> cipher = AESGCMCipher()
            >>> ct = cipher.encrypt("secret")
            >>> len(ct) > 0
            True
        """
        return encrypt_aes_gcm(plaintext, self.key, associated_data)

    def decrypt(
        self,
        ciphertext: bytes,
        associated_data: bytes | None = None,
        return_bytes: bool = False,
    ) -> Union[bytes, str]:
        """
        Decrypt AES-256-GCM encrypted data.

        Args:
            ciphertext: Encrypted data with nonce and tag.
            associated_data: Optional AAD (must match encryption).
            return_bytes: If True, return bytes instead of string.

        Returns:
            Decrypted plaintext.

        Raises:
            SymmetricEncryptionError: If decryption fails.
        """
        return decrypt_aes_gcm(ciphertext, self.key, associated_data, return_bytes=return_bytes)

    def encrypt_with_aad(
        self,
        plaintext: Union[bytes, str],
        context: Union[bytes, str],
    ) -> tuple[bytes, bytes]:
        """
        Encrypt with context-bound associated data.

        The context is used as AAD and must be provided for decryption.
        This binds the ciphertext to a specific context/purpose.

        Args:
            plaintext: Data to encrypt.
            context: Context string (e.g., "user:123", "session:abc").

        Returns:
            Tuple of (ciphertext, context_bytes).

        Example:
            >>> cipher = AESGCMCipher()
            >>> ct, ctx = cipher.encrypt_with_aad("secret", "user:123")
            >>> cipher.decrypt_with_aad(ct, ctx)
            'secret'
        """
        if isinstance(context, str):
            context = context.encode("utf-8")
        ciphertext = self.encrypt(plaintext, associated_data=context)
        return ciphertext, context

    def decrypt_with_aad(
        self,
        ciphertext: bytes,
        context: Union[bytes, str],
        return_bytes: bool = False,
    ) -> Union[bytes, str]:
        """
        Decrypt with context verification.

        Args:
            ciphertext: Encrypted data.
            context: Original context used during encryption.
            return_bytes: If True, return bytes instead of string.

        Returns:
            Decrypted plaintext.

        Raises:
            SymmetricEncryptionError: If context doesn't match.
        """
        if isinstance(context, str):
            context = context.encode("utf-8")
        return self.decrypt(ciphertext, associated_data=context, return_bytes=return_bytes)


def derive_key_from_password(
    password: Union[bytes, str],
    salt: bytes | None = None,
    iterations: int = 100_000,
    key_length: int = AES_KEY_SIZE,
) -> tuple[bytes, bytes]:
    """
    Derive an AES key from a password using PBKDF2-HMAC-SHA256.

    Implements secure password-based key derivation following
    NIST SP 800-132 recommendations.

    Args:
        password: User password (bytes or string).
        salt: Random salt (generated if not provided).
        iterations: PBKDF2 iterations (default: 100,000).
        key_length: Derived key length (default: 32 bytes).

    Returns:
        Tuple of (derived_key, salt).

    Security Note:
        Store the salt alongside the encrypted data.
        Increase iterations for higher security (at cost of speed).

    Example:
        >>> key, salt = derive_key_from_password("mypassword")
        >>> len(key) == 32
        True
    """
    if isinstance(password, str):
        password = password.encode("utf-8")

    if salt is None:
        salt = secrets.token_bytes(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password,
        salt,
        iterations=iterations,
        dklen=key_length,
    )

    return key, salt


def derive_key_scrypt(
    password: Union[bytes, str],
    salt: bytes | None = None,
    n: int = 2**14,  # CPU/memory cost parameter
    r: int = 8,  # Block size
    p: int = 1,  # Parallelization parameter
    key_length: int = AES_KEY_SIZE,
) -> tuple[bytes, bytes]:
    """
    Derive an AES key from a password using scrypt.

    Scrypt is a memory-hard key derivation function that provides
    stronger resistance to hardware brute-force attacks than PBKDF2.

    Args:
        password: User password (bytes or string).
        salt: Random salt (generated if not provided).
        n: CPU/memory cost (power of 2, default: 2^14).
        r: Block size parameter (default: 8).
        p: Parallelization parameter (default: 1).
        key_length: Derived key length (default: 32 bytes).

    Returns:
        Tuple of (derived_key, salt).

    Security Note:
        Higher n values increase memory requirements exponentially.
        For interactive logins, use n=2^14; for file encryption, n=2^20.

    Example:
        >>> key, salt = derive_key_scrypt("mypassword")
        >>> len(key) == 32
        True
    """
    if isinstance(password, str):
        password = password.encode("utf-8")

    if salt is None:
        salt = secrets.token_bytes(16)

    kdf = Scrypt(salt=salt, length=key_length, n=n, r=r, p=p)
    key = kdf.derive(password)

    return key, salt


__all__ = [
    "AES_KEY_SIZE",
    "GCM_NONCE_SIZE",
    "GCM_TAG_SIZE",
    "AESGCMCipher",
    "SymmetricEncryptionError",
    "decrypt_aes_gcm",
    "derive_key_from_password",
    "derive_key_scrypt",
    "encrypt_aes_gcm",
    "generate_aes_key",
]
