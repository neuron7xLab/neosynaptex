"""
Cryptographic configuration for MyceliumFractalNet API.

Provides configuration management for cryptographic operations including
symmetric encryption, key management, and digital signatures.

Environment Variables:
    MFN_CRYPTO_ENABLED       - Enable/disable crypto layer (default: true)
    MFN_CRYPTO_ALGORITHM     - Cipher suite: AES-256-GCM or ChaCha20-Poly1305 (default: AES-256-GCM)
    MFN_CRYPTO_KEY_SIZE      - Key size in bits: 128, 192, 256 (default: 256)
    MFN_CRYPTO_SIGNATURE_ALG - Signature algorithm: Ed25519 or ECDSA (default: Ed25519)
    MFN_CRYPTO_AUDIT_LOG     - Enable audit logging for crypto operations (default: true)

Reference: docs/MFN_CRYPTOGRAPHY.md, Step 4: API Integration & System Compatibility
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api_config import Environment


@dataclass
class CryptoConfig:
    """
    Cryptographic configuration for the API.

    Attributes:
        enabled: Whether cryptographic operations are enabled.
        cipher_suite: Symmetric cipher algorithm (AES-256-GCM, ChaCha20-Poly1305).
        key_size_bits: Key size in bits (128, 192, 256).
        signature_algorithm: Digital signature algorithm (Ed25519, ECDSA).
        audit_logging: Whether to log cryptographic operations.
        max_plaintext_size: Maximum plaintext size in bytes (default: 1 MB).
        max_keys_per_user: Maximum stored keys per user (default: 100).
    """

    enabled: bool = True
    cipher_suite: str = "AES-256-GCM"
    key_size_bits: int = 256
    signature_algorithm: str = "Ed25519"
    audit_logging: bool = True
    max_plaintext_size: int = 1048576  # 1 MB
    max_keys_per_user: int = 100

    @classmethod
    def from_env(cls, env: Environment | None = None) -> CryptoConfig:
        """
        Create CryptoConfig from environment variables.

        Args:
            env: Current environment (dev/staging/prod). Not used but kept for consistency.

        Returns:
            CryptoConfig: Configured cryptography settings.
        """
        # Check if crypto is enabled
        enabled_env = os.getenv("MFN_CRYPTO_ENABLED", "true").lower()
        enabled = enabled_env in ("true", "1", "yes")

        # Cipher suite selection
        cipher_suite = os.getenv("MFN_CRYPTO_ALGORITHM", "AES-256-GCM")
        if cipher_suite not in ("AES-256-GCM", "ChaCha20-Poly1305"):
            cipher_suite = "AES-256-GCM"

        # Key size
        key_size_str = os.getenv("MFN_CRYPTO_KEY_SIZE", "256")
        try:
            key_size_bits = int(key_size_str)
            if key_size_bits not in (128, 192, 256):
                key_size_bits = 256
        except ValueError:
            key_size_bits = 256

        # Signature algorithm
        sig_alg = os.getenv("MFN_CRYPTO_SIGNATURE_ALG", "Ed25519")
        if sig_alg not in ("Ed25519", "ECDSA"):
            sig_alg = "Ed25519"

        # Audit logging
        audit_env = os.getenv("MFN_CRYPTO_AUDIT_LOG", "true").lower()
        audit_logging = audit_env in ("true", "1", "yes")

        return cls(
            enabled=enabled,
            cipher_suite=cipher_suite,
            key_size_bits=key_size_bits,
            signature_algorithm=sig_alg,
            audit_logging=audit_logging,
        )


# In-memory key store for server-managed keys
@dataclass
class KeyStore:
    """
    In-memory key store for server-managed cryptographic keys.

    This is a simple implementation for development/testing.
    In production, use a proper Key Management System (KMS).

    Attributes:
        encryption_keys: Mapping of key_id to AES keys.
        signature_keys: Mapping of key_id to (private_key, public_key) tuples.
        ecdh_keys: Mapping of key_id to (private_key, public_key) tuples.
    """

    encryption_keys: dict[str, bytes] = field(default_factory=dict)
    signature_keys: dict[str, tuple[bytes, bytes]] = field(default_factory=dict)
    ecdh_keys: dict[str, tuple[bytes, bytes]] = field(default_factory=dict)
    _default_encryption_key_id: str | None = None
    _default_signature_key_id: str | None = None

    def set_default_encryption_key(self, key_id: str) -> None:
        """Set the default encryption key ID."""
        if key_id in self.encryption_keys:
            self._default_encryption_key_id = key_id

    def set_default_signature_key(self, key_id: str) -> None:
        """Set the default signature key ID."""
        if key_id in self.signature_keys:
            self._default_signature_key_id = key_id

    @property
    def default_encryption_key_id(self) -> str | None:
        """Get the default encryption key ID."""
        return self._default_encryption_key_id

    @property
    def default_signature_key_id(self) -> str | None:
        """Get the default signature key ID."""
        return self._default_signature_key_id


# Singleton instances
_crypto_config: CryptoConfig | None = None
_key_store: KeyStore | None = None


def get_crypto_config() -> CryptoConfig:
    """
    Get the crypto configuration singleton.

    Returns:
        CryptoConfig: Current crypto configuration.
    """
    global _crypto_config
    if _crypto_config is None:
        _crypto_config = CryptoConfig.from_env()
    return _crypto_config


def get_key_store() -> KeyStore:
    """
    Get the key store singleton.

    Returns:
        KeyStore: Current key store instance.
    """
    global _key_store
    if _key_store is None:
        _key_store = KeyStore()
    return _key_store


def reset_crypto_config() -> None:
    """Reset the crypto configuration singleton (useful for testing)."""
    global _crypto_config
    _crypto_config = None


def reset_key_store() -> None:
    """Reset the key store singleton (useful for testing)."""
    global _key_store
    _key_store = None


__all__ = [
    "CryptoConfig",
    "KeyStore",
    "get_crypto_config",
    "get_key_store",
    "reset_crypto_config",
    "reset_key_store",
]
