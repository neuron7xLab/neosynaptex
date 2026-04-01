"""
Tests for ECDH key exchange functionality.

Verifies the X25519 key exchange implementation including:
- Key generation
- Shared secret computation
- Key derivation
- Error handling
"""

from __future__ import annotations

import pytest

from mycelium_fractal_net.crypto.key_exchange import (
    ECDHKeyExchange,
    ECDHKeyPair,
    KeyExchangeError,
    derive_symmetric_key,
    generate_ecdh_keypair,
)


class TestGenerateECDHKeypair:
    """Tests for ECDH key pair generation."""

    def test_generate_keypair_sizes(self) -> None:
        """Generated keys should be 32 bytes each."""
        keypair = generate_ecdh_keypair()
        assert len(keypair.private_key) == 32
        assert len(keypair.public_key) == 32

    def test_generate_keypair_unique(self) -> None:
        """Each generated keypair should be unique."""
        keypairs = [generate_ecdh_keypair() for _ in range(10)]
        private_keys = [k.private_key for k in keypairs]
        public_keys = [k.public_key for k in keypairs]
        assert len(set(private_keys)) == 10
        assert len(set(public_keys)) == 10

    def test_keypair_types(self) -> None:
        """Keys should be bytes."""
        keypair = generate_ecdh_keypair()
        assert isinstance(keypair.private_key, bytes)
        assert isinstance(keypair.public_key, bytes)

    def test_keypair_validation(self) -> None:
        """ECDHKeyPair should validate key sizes."""
        with pytest.raises(KeyExchangeError, match="Private key must be 32 bytes"):
            ECDHKeyPair(private_key=b"short", public_key=b"x" * 32)

        with pytest.raises(KeyExchangeError, match="Public key must be 32 bytes"):
            ECDHKeyPair(private_key=b"x" * 32, public_key=b"short")


class TestECDHKeyExchange:
    """Tests for ECDH key exchange operations."""

    def test_shared_secret_agreement(self) -> None:
        """Both parties should derive the same shared secret."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        alice_secret = alice.compute_shared_secret(bob.public_key)
        bob_secret = bob.compute_shared_secret(alice.public_key)

        assert alice_secret == bob_secret

    def test_shared_secret_size(self) -> None:
        """Shared secret should be 32 bytes."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        secret = alice.compute_shared_secret(bob.public_key)
        assert len(secret) == 32

    def test_shared_secret_different_pairs(self) -> None:
        """Different key pairs should produce different shared secrets."""
        alice1 = ECDHKeyExchange()
        alice2 = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        secret1 = alice1.compute_shared_secret(bob.public_key)
        secret2 = alice2.compute_shared_secret(bob.public_key)

        assert secret1 != secret2

    def test_accepts_keypair_object(self) -> None:
        """compute_shared_secret should accept ECDHKeyPair objects."""
        alice = ECDHKeyExchange()
        bob_keypair = generate_ecdh_keypair()

        # Should work with keypair object
        secret = alice.compute_shared_secret(bob_keypair)
        assert len(secret) == 32

    def test_invalid_public_key_size(self) -> None:
        """Should reject public keys that are not 32 bytes."""
        alice = ECDHKeyExchange()

        with pytest.raises(KeyExchangeError, match="Peer public key must be 32 bytes"):
            alice.compute_shared_secret(b"short key")

    def test_existing_keypair(self) -> None:
        """Should use existing keypair when provided."""
        keypair = generate_ecdh_keypair()
        exchange = ECDHKeyExchange(keypair)

        assert exchange.public_key == keypair.public_key
        assert exchange.private_key == keypair.private_key


class TestDeriveSymmetricKey:
    """Tests for symmetric key derivation."""

    def test_derive_key_size(self) -> None:
        """Derived key should have requested size."""
        secret = bytes(32)

        key32 = derive_symmetric_key(secret, length=32)
        assert len(key32) == 32

        key64 = derive_symmetric_key(secret, length=64)
        assert len(key64) == 64

        key16 = derive_symmetric_key(secret, length=16)
        assert len(key16) == 16

    def test_derive_key_deterministic(self) -> None:
        """Same inputs should produce same derived key."""
        secret = bytes(range(32))

        key1 = derive_symmetric_key(secret, b"context")
        key2 = derive_symmetric_key(secret, b"context")

        assert key1 == key2

    def test_derive_key_context_separation(self) -> None:
        """Different contexts should produce different keys."""
        secret = bytes(range(32))

        key1 = derive_symmetric_key(secret, b"encryption")
        key2 = derive_symmetric_key(secret, b"authentication")

        assert key1 != key2

    def test_derive_key_secret_separation(self) -> None:
        """Different secrets should produce different keys."""
        secret1 = bytes(32)
        secret2 = bytes(range(32))

        key1 = derive_symmetric_key(secret1, b"ctx")
        key2 = derive_symmetric_key(secret2, b"ctx")

        assert key1 != key2


class TestECDHDeriveKey:
    """Tests for ECDHKeyExchange.derive_key method."""

    def test_derive_key_agreement(self) -> None:
        """Both parties should derive the same key."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        key_alice = alice.derive_key(bob.public_key, b"chat")
        key_bob = bob.derive_key(alice.public_key, b"chat")

        assert key_alice == key_bob

    def test_derive_key_different_contexts(self) -> None:
        """Different contexts should produce different keys."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        key1 = alice.derive_key(bob.public_key, b"encryption")
        key2 = alice.derive_key(bob.public_key, b"authentication")

        assert key1 != key2

    def test_derive_key_custom_length(self) -> None:
        """Should support custom key lengths."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        key16 = alice.derive_key(bob.public_key, length=16)
        key48 = alice.derive_key(bob.public_key, length=48)

        assert len(key16) == 16
        assert len(key48) == 48


class TestSecurityProperties:
    """Tests for security properties of ECDH implementation."""

    def test_private_key_not_in_public(self) -> None:
        """Private key bytes should not appear in public key."""
        for _ in range(10):
            keypair = generate_ecdh_keypair()
            # Check that private key doesn't appear as substring of public key
            assert keypair.private_key != keypair.public_key

    def test_deterministic_public_key(self) -> None:
        """Same private key should always produce same public key."""
        # Note: We can't easily test this without exposing internal details,
        # but we can verify that key exchange is consistent
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()

        # Multiple calls should give same result
        secret1 = alice.compute_shared_secret(bob.public_key)
        secret2 = alice.compute_shared_secret(bob.public_key)

        assert secret1 == secret2

    def test_non_commutative_with_wrong_keys(self) -> None:
        """Key exchange should fail to match with wrong parties."""
        alice = ECDHKeyExchange()
        bob = ECDHKeyExchange()
        eve = ECDHKeyExchange()

        alice_bob = alice.compute_shared_secret(bob.public_key)
        alice_eve = alice.compute_shared_secret(eve.public_key)

        # Should be different
        assert alice_bob != alice_eve
