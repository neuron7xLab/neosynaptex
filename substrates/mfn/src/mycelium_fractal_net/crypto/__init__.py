"""
Cryptographic Module for MyceliumFractalNet.

Provides cryptographic primitives with formal mathematical proofs of security:
    - ECDH (Elliptic Curve Diffie-Hellman) key exchange using X25519
    - EdDSA (Ed25519) digital signatures
    - AES-256-GCM authenticated symmetric encryption
    - Secure key derivation functions (HKDF, PBKDF2, scrypt)

Mathematical Security Foundations:
    - Discrete Logarithm Problem (DLP) hardness on elliptic curves
    - Collision resistance of SHA-512
    - Computational indistinguishability under CDH assumption
    - AES-256 provides 256-bit security against brute force

Security Standards:
    - RFC 7748 (X25519 key exchange)
    - RFC 8032 (Ed25519 signatures)
    - NIST SP 800-38D (AES-GCM)
    - NIST SP 800-56A (key derivation)
    - RFC 5869 (HKDF)

Usage:
    >>> from mycelium_fractal_net.crypto import (
    ...     ECDHKeyExchange,
    ...     EdDSASignature,
    ...     AESGCMCipher,
    ...     derive_symmetric_key,
    ... )

Reference: docs/MFN_CRYPTOGRAPHY.md
"""

from .key_exchange import (
    ECDHKeyExchange,
    ECDHKeyPair,
    KeyExchangeError,
    derive_symmetric_key,
    generate_ecdh_keypair,
)
from .signatures import (
    EdDSASignature,
    SignatureError,
    SignatureKeyPair,
    generate_signature_keypair,
    sign_message,
    verify_signature,
)
from .symmetric import (
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

__all__ = [
    "AES_KEY_SIZE",
    "GCM_NONCE_SIZE",
    "GCM_TAG_SIZE",
    # Symmetric Encryption (AES-256-GCM)
    "AESGCMCipher",
    # Key Exchange
    "ECDHKeyExchange",
    "ECDHKeyPair",
    # Digital Signatures
    "EdDSASignature",
    "KeyExchangeError",
    "SignatureError",
    "SignatureKeyPair",
    "SymmetricEncryptionError",
    "decrypt_aes_gcm",
    # Key Derivation
    "derive_key_from_password",
    "derive_key_scrypt",
    "derive_symmetric_key",
    "encrypt_aes_gcm",
    "generate_aes_key",
    "generate_ecdh_keypair",
    "generate_signature_keypair",
    "sign_message",
    "verify_signature",
]
