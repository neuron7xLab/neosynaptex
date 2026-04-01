"""
Crypto API adapters for MyceliumFractalNet.

Provides adapter functions that bridge API requests to the crypto module.
Handles key management, audit logging, and error handling.

Reference: docs/MFN_CRYPTOGRAPHY.md, Step 4: API Integration
"""

from __future__ import annotations

import base64
import secrets

from mycelium_fractal_net.crypto import (
    AESGCMCipher,
    EdDSASignature,
    KeyExchangeError,
    SignatureError,
    SignatureKeyPair,
    SymmetricEncryptionError,
    generate_aes_key,
    generate_ecdh_keypair,
    generate_signature_keypair,
)

from .crypto_config import get_crypto_config, get_key_store
from .logging_config import get_logger
from .schemas import (
    DecryptRequest,
    DecryptResponse,
    EncryptRequest,
    EncryptResponse,
    KeypairRequest,
    KeypairResponse,
    SignRequest,
    SignResponse,
    VerifyRequest,
    VerifyResponse,
)

logger = get_logger("crypto_api")


class CryptoAPIError(Exception):
    """Base exception for crypto API operations."""


def _generate_key_id() -> str:
    """Generate a unique key identifier."""
    return f"key_{secrets.token_hex(16)}"


def _log_crypto_operation(
    operation: str,
    key_id: str,
    algorithm: str,
    success: bool,
    error: str | None = None,
) -> None:
    """
    Log a cryptographic operation for audit purposes.

    Logs only non-sensitive metadata (key IDs, algorithms) - never keys or plaintext.

    Args:
        operation: Type of operation (encrypt, decrypt, sign, verify, keypair).
        key_id: Key identifier used.
        algorithm: Algorithm used.
        success: Whether operation succeeded.
        error: Error message if operation failed.
    """
    config = get_crypto_config()
    if not config.audit_logging:
        return

    log_data = {
        "operation": operation,
        "key_id": key_id,
        "algorithm": algorithm,
        "success": success,
    }

    if success:
        logger.info(f"Crypto operation: {operation}", extra=log_data)
    else:
        log_data["error"] = error or "Unknown error"
        logger.warning(f"Crypto operation failed: {operation}", extra=log_data)


def encrypt_data_adapter(request: EncryptRequest) -> EncryptResponse:
    """
    Handle encryption API request.

    Args:
        request: Encryption request with plaintext data.

    Returns:
        EncryptResponse: Encrypted ciphertext.

    Raises:
        CryptoAPIError: If encryption fails or crypto is disabled.
    """
    config = get_crypto_config()
    if not config.enabled:
        raise CryptoAPIError("Cryptographic operations are disabled")

    key_store = get_key_store()
    key_id = request.key_id

    try:
        # Decode base64 plaintext
        try:
            plaintext = base64.b64decode(request.plaintext)
        except Exception as exc:
            raise CryptoAPIError("Invalid base64-encoded plaintext") from exc

        # Validate size
        if len(plaintext) > config.max_plaintext_size:
            raise CryptoAPIError(
                f"Plaintext exceeds maximum size of {config.max_plaintext_size} bytes"
            )

        # Get or create encryption key
        if key_id and key_id in key_store.encryption_keys:
            key = key_store.encryption_keys[key_id]
        elif key_store.default_encryption_key_id:
            key_id = key_store.default_encryption_key_id
            key = key_store.encryption_keys[key_id]
        else:
            # Create a new default key
            key_id = _generate_key_id()
            key = generate_aes_key(config.key_size_bits // 8)
            key_store.encryption_keys[key_id] = key
            key_store.set_default_encryption_key(key_id)

        # Parse associated data if provided
        aad = None
        if request.associated_data:
            try:
                aad = base64.b64decode(request.associated_data)
            except Exception as exc:
                raise CryptoAPIError("Invalid base64-encoded associated data") from exc

        # Encrypt
        cipher = AESGCMCipher(key=key)
        ciphertext = cipher.encrypt(plaintext, associated_data=aad)

        # Encode result
        ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")

        _log_crypto_operation("encrypt", key_id, config.cipher_suite, True)

        return EncryptResponse(
            ciphertext=ciphertext_b64,
            key_id=key_id,
            algorithm=config.cipher_suite,
        )

    except CryptoAPIError:
        raise
    except SymmetricEncryptionError as e:
        _log_crypto_operation("encrypt", key_id or "unknown", config.cipher_suite, False, str(e))
        raise CryptoAPIError(f"Encryption failed: {e}")
    except Exception as e:
        _log_crypto_operation("encrypt", key_id or "unknown", config.cipher_suite, False, str(e))
        raise CryptoAPIError(f"Encryption failed: {e}")


def decrypt_data_adapter(request: DecryptRequest) -> DecryptResponse:
    """
    Handle decryption API request.

    Args:
        request: Decryption request with ciphertext.

    Returns:
        DecryptResponse: Decrypted plaintext.

    Raises:
        CryptoAPIError: If decryption fails or key not found.
    """
    config = get_crypto_config()
    if not config.enabled:
        raise CryptoAPIError("Cryptographic operations are disabled")

    key_store = get_key_store()
    key_id = request.key_id

    try:
        # Decode base64 ciphertext
        try:
            ciphertext = base64.b64decode(request.ciphertext)
        except Exception as exc:
            raise CryptoAPIError("Invalid base64-encoded ciphertext") from exc

        # Get decryption key
        if key_id and key_id in key_store.encryption_keys:
            key = key_store.encryption_keys[key_id]
        elif key_store.default_encryption_key_id:
            key_id = key_store.default_encryption_key_id
            key = key_store.encryption_keys[key_id]
        else:
            raise CryptoAPIError("No encryption key available for decryption")

        # Parse associated data if provided
        aad = None
        if request.associated_data:
            try:
                aad = base64.b64decode(request.associated_data)
            except Exception as exc:
                raise CryptoAPIError("Invalid base64-encoded associated data") from exc

        # Decrypt
        cipher = AESGCMCipher(key=key)
        plaintext_bytes = cipher.decrypt(ciphertext, associated_data=aad, return_bytes=True)

        # Encode result - ensure we have bytes for b64encode
        if isinstance(plaintext_bytes, str):
            plaintext_bytes = plaintext_bytes.encode("utf-8")
        plaintext_b64 = base64.b64encode(plaintext_bytes).decode("ascii")

        _log_crypto_operation("decrypt", key_id, config.cipher_suite, True)

        return DecryptResponse(
            plaintext=plaintext_b64,
            key_id=key_id,
        )

    except CryptoAPIError:
        raise
    except SymmetricEncryptionError as e:
        _log_crypto_operation("decrypt", key_id or "unknown", config.cipher_suite, False, str(e))
        raise CryptoAPIError(f"Decryption failed: {e}")
    except Exception as e:
        _log_crypto_operation("decrypt", key_id or "unknown", config.cipher_suite, False, str(e))
        raise CryptoAPIError(f"Decryption failed: {e}")


def sign_message_adapter(request: SignRequest) -> SignResponse:
    """
    Handle signing API request.

    Args:
        request: Signing request with message.

    Returns:
        SignResponse: Digital signature.

    Raises:
        CryptoAPIError: If signing fails.
    """
    config = get_crypto_config()
    if not config.enabled:
        raise CryptoAPIError("Cryptographic operations are disabled")

    key_store = get_key_store()
    key_id = request.key_id

    try:
        # Decode base64 message
        try:
            message = base64.b64decode(request.message)
        except Exception as exc:
            raise CryptoAPIError("Invalid base64-encoded message") from exc

        # Validate size
        if len(message) > config.max_plaintext_size:
            raise CryptoAPIError(
                f"Message exceeds maximum size of {config.max_plaintext_size} bytes"
            )

        # Get or create signing key
        if key_id and key_id in key_store.signature_keys:
            private_key, public_key = key_store.signature_keys[key_id]
        elif key_store.default_signature_key_id:
            key_id = key_store.default_signature_key_id
            private_key, public_key = key_store.signature_keys[key_id]
        else:
            # Create a new default signing key
            key_id = _generate_key_id()
            keypair = generate_signature_keypair()
            key_store.signature_keys[key_id] = (keypair.private_key, keypair.public_key)
            key_store.set_default_signature_key(key_id)
            private_key = keypair.private_key
            public_key = keypair.public_key

        # Sign using proper keypair initialization
        keypair = SignatureKeyPair(private_key=private_key, public_key=public_key)
        signer = EdDSASignature(keypair=keypair)
        signature = signer.sign(message)

        # Encode result
        signature_b64 = base64.b64encode(signature).decode("ascii")

        _log_crypto_operation("sign", key_id, config.signature_algorithm, True)

        return SignResponse(
            signature=signature_b64,
            key_id=key_id,
            algorithm=config.signature_algorithm,
        )

    except CryptoAPIError:
        raise
    except SignatureError as e:
        _log_crypto_operation(
            "sign", key_id or "unknown", config.signature_algorithm, False, str(e)
        )
        raise CryptoAPIError(f"Signing failed: {e}")
    except Exception as e:
        _log_crypto_operation(
            "sign", key_id or "unknown", config.signature_algorithm, False, str(e)
        )
        raise CryptoAPIError(f"Signing failed: {e}")


def verify_signature_adapter(request: VerifyRequest) -> VerifyResponse:
    """
    Handle signature verification API request.

    Args:
        request: Verification request with message and signature.

    Returns:
        VerifyResponse: Verification result.

    Raises:
        CryptoAPIError: If verification fails due to an error.
    """
    config = get_crypto_config()
    if not config.enabled:
        raise CryptoAPIError("Cryptographic operations are disabled")

    key_store = get_key_store()
    key_id = request.key_id

    try:
        # Decode base64 message
        try:
            message = base64.b64decode(request.message)
        except Exception as exc:
            raise CryptoAPIError("Invalid base64-encoded message") from exc

        # Decode base64 signature
        try:
            signature = base64.b64decode(request.signature)
        except Exception as exc:
            raise CryptoAPIError("Invalid base64-encoded signature") from exc

        # Get public key
        public_key: bytes | None = None

        if request.public_key:
            # Use provided public key
            try:
                public_key = base64.b64decode(request.public_key)
            except Exception as exc:
                raise CryptoAPIError("Invalid base64-encoded public key") from exc
        elif key_id and key_id in key_store.signature_keys:
            _, public_key = key_store.signature_keys[key_id]
        elif key_store.default_signature_key_id:
            key_id = key_store.default_signature_key_id
            _, public_key = key_store.signature_keys[key_id]
        else:
            raise CryptoAPIError("No public key provided and no key_id matches stored keys")

        # Verify
        verifier = EdDSASignature()
        valid = verifier.verify(message, signature, public_key)

        _log_crypto_operation("verify", key_id or "external", config.signature_algorithm, True)

        return VerifyResponse(
            valid=valid,
            key_id=key_id,
            algorithm=config.signature_algorithm,
        )

    except CryptoAPIError:
        raise
    except SignatureError as e:
        _log_crypto_operation(
            "verify", key_id or "unknown", config.signature_algorithm, False, str(e)
        )
        raise CryptoAPIError(f"Verification failed: {e}")
    except Exception as e:
        _log_crypto_operation(
            "verify", key_id or "unknown", config.signature_algorithm, False, str(e)
        )
        raise CryptoAPIError(f"Verification failed: {e}")


def generate_keypair_adapter(request: KeypairRequest) -> KeypairResponse:
    """
    Handle key pair generation API request.

    Args:
        request: Key generation request.

    Returns:
        KeypairResponse: Generated public key and key ID.

    Raises:
        CryptoAPIError: If key generation fails.
    """
    config = get_crypto_config()
    if not config.enabled:
        raise CryptoAPIError("Cryptographic operations are disabled")

    key_store = get_key_store()
    key_id = request.key_id or _generate_key_id()

    try:
        algorithm = request.algorithm
        public_key_b64: str = ""

        if algorithm == "Ed25519":
            # Generate Ed25519 signature key pair
            sig_keypair = generate_signature_keypair()
            key_store.signature_keys[key_id] = (
                sig_keypair.private_key,
                sig_keypair.public_key,
            )
            public_key_b64 = base64.b64encode(sig_keypair.public_key).decode("ascii")

            # Set as default if no default exists
            if not key_store.default_signature_key_id:
                key_store.set_default_signature_key(key_id)

        elif algorithm == "ECDH":
            # Generate X25519 key exchange key pair
            ecdh_keypair = generate_ecdh_keypair()
            key_store.ecdh_keys[key_id] = (
                ecdh_keypair.private_key,
                ecdh_keypair.public_key,
            )
            public_key_b64 = base64.b64encode(ecdh_keypair.public_key).decode("ascii")

        else:
            raise CryptoAPIError(f"Unsupported algorithm: {algorithm}")

        _log_crypto_operation("keypair", key_id, algorithm, True)

        return KeypairResponse(
            key_id=key_id,
            public_key=public_key_b64,
            algorithm=algorithm,
        )

    except CryptoAPIError:
        raise
    except (KeyExchangeError, SignatureError) as e:
        _log_crypto_operation("keypair", key_id, request.algorithm, False, str(e))
        raise CryptoAPIError(f"Key generation failed: {e}")
    except Exception as e:
        _log_crypto_operation("keypair", key_id, request.algorithm, False, str(e))
        raise CryptoAPIError(f"Key generation failed: {e}")


__all__ = [
    "CryptoAPIError",
    "decrypt_data_adapter",
    "encrypt_data_adapter",
    "generate_keypair_adapter",
    "sign_message_adapter",
    "verify_signature_adapter",
]
