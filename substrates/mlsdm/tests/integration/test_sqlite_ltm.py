"""Integration tests for SQLite LTM backend.

Tests cover:
- Put/get roundtrip with PII scrubbing
- TTL-based eviction
- Compaction
- Optional encryption-at-rest
"""

import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from mlsdm.memory.provenance import MemoryProvenance, MemorySource
from mlsdm.memory.sqlite_store import SQLiteMemoryStore
from mlsdm.memory.store import MemoryItem, compute_content_hash

# Check if cryptography is available for encryption tests
try:
    import cryptography.hazmat.primitives.ciphers.aead  # noqa: F401
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database file path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_ltm.db"


@pytest.fixture
def store(temp_db_path: Path) -> SQLiteMemoryStore:
    """Create a SQLiteMemoryStore instance for testing."""
    store = SQLiteMemoryStore(str(temp_db_path), store_raw=False)
    yield store
    store.close()


@pytest.fixture
def store_with_encryption(temp_db_path: Path) -> SQLiteMemoryStore:
    """Create an encrypted SQLiteMemoryStore instance."""
    if not CRYPTOGRAPHY_AVAILABLE:
        pytest.skip("cryptography not available")

    # Generate a random 32-byte key
    encryption_key = os.urandom(32)
    store = SQLiteMemoryStore(
        str(temp_db_path),
        encryption_key=encryption_key,
        store_raw=False,
    )
    yield store
    store.close()


def build_provenance(
    content: str,
    *,
    source: MemorySource = MemorySource.USER_INPUT,
    confidence: float = 0.95,
) -> MemoryProvenance:
    return MemoryProvenance(
        source=source,
        confidence=confidence,
        timestamp=datetime.now(),
        content_hash=compute_content_hash(content),
    )


def test_put_get_roundtrip_scrubbed(store: SQLiteMemoryStore) -> None:
    """Test storing and retrieving memory with PII scrubbing.

    Verifies that:
    1. Content with PII (email, token-like) is scrubbed before storage
    2. Retrieved content does NOT contain raw secret patterns
    """
    # Create memory item with obvious PII
    original_content = (
        "Contact user@example.com for access. "
        "Use API key sk-1234567890abcdefghij for authentication."
    )

    item = MemoryItem(
        id="test-001",
        ts=time.time(),
        content=original_content,
        content_hash=compute_content_hash(original_content),
        ttl_s=3600.0,  # 1 hour
        provenance=build_provenance(original_content),
    )

    # Store item
    item_id = store.put(item)
    assert item_id == "test-001"

    # Retrieve item
    retrieved = store.get(item_id)
    assert retrieved is not None
    assert retrieved.id == "test-001"

    # Verify scrubbing occurred
    # Email should be scrubbed
    assert "user@example.com" not in retrieved.content

    # API key should be scrubbed
    assert "sk-1234567890abcdefghij" not in retrieved.content
    assert "sk-***REDACTED***" in retrieved.content or "***@***.***" in retrieved.content

    # Content hash should match original (not scrubbed version)
    assert retrieved.content_hash == compute_content_hash(original_content)


def test_put_get_with_provenance(store: SQLiteMemoryStore) -> None:
    """Test storing and retrieving memory with provenance metadata."""
    content = "Test content with provenance"
    provenance = MemoryProvenance(
        source=MemorySource.USER_INPUT,
        confidence=0.95,
        timestamp=datetime.now(),
        content_hash=compute_content_hash(content),
    )

    item = MemoryItem(
        id="test-002",
        ts=time.time(),
        content=content,
        content_hash=compute_content_hash(content),
        provenance=provenance,
    )

    # Store and retrieve
    store.put(item)
    retrieved = store.get("test-002")

    assert retrieved is not None
    assert retrieved.provenance is not None
    assert retrieved.provenance.source == MemorySource.USER_INPUT
    assert retrieved.provenance.confidence == 0.95


def test_ttl_evict(store: SQLiteMemoryStore) -> None:
    """Test TTL-based eviction of expired memories.

    Uses explicit now_ts parameter to avoid sleep-based timing issues.
    """
    now = time.time()

    # Create items with different TTLs
    content1 = "This should expire soon"
    item1 = MemoryItem(
        id="expire-soon",
        ts=now - 100,  # Created 100 seconds ago
        content=content1,
        content_hash=compute_content_hash(content1),
        ttl_s=50.0,  # Expires at now - 100 + 50 = now - 50 (already expired)
        provenance=build_provenance(content1),
    )

    content2 = "This should not expire yet"
    item2 = MemoryItem(
        id="expire-later",
        ts=now,
        content=content2,
        content_hash=compute_content_hash(content2),
        ttl_s=3600.0,  # Expires at now + 3600 (not expired)
        provenance=build_provenance(content2),
    )

    content3 = "This has no TTL"
    item3 = MemoryItem(
        id="no-ttl",
        ts=now,
        content=content3,
        content_hash=compute_content_hash(content3),
        ttl_s=None,  # Never expires
        provenance=build_provenance(content3),
    )

    # Store items
    store.put(item1)
    store.put(item2)
    store.put(item3)

    # Verify all items exist
    assert store.get("expire-soon") is not None
    assert store.get("expire-later") is not None
    assert store.get("no-ttl") is not None

    # Evict expired items at current time
    evicted_count = store.evict_expired(now)

    # Should have evicted 1 item (expire-soon)
    assert evicted_count == 1

    # Verify correct items remain
    assert store.get("expire-soon") is None
    assert store.get("expire-later") is not None
    assert store.get("no-ttl") is not None


def test_query_text_search(store: SQLiteMemoryStore) -> None:
    """Test LIKE-based text search."""
    now = time.time()

    # Create several memories
    items = [
        MemoryItem(
            id=f"item-{i}",
            ts=now + i,
            content=f"Memory about {topic}",
            content_hash=compute_content_hash(f"Memory about {topic}"),
            provenance=build_provenance(f"Memory about {topic}"),
        )
        for i, topic in enumerate(["cats", "dogs", "cats and dogs", "birds"])
    ]

    for item in items:
        store.put(item)

    # Query for "cats"
    results = store.query("cats", limit=10)
    assert len(results) == 2  # "cats" and "cats and dogs"
    assert all("cats" in r.content.lower() for r in results)

    # Query for "dogs"
    results = store.query("dogs", limit=10)
    assert len(results) == 2  # "dogs" and "cats and dogs"

    # Query with limit
    results = store.query("Memory", limit=2)
    assert len(results) == 2

    # Query with since_ts filter
    results = store.query("Memory", since_ts=now + 2)
    assert len(results) == 2  # Only items 2 and 3


def test_compact_runs(store: SQLiteMemoryStore) -> None:
    """Test that compact/vacuum runs without error."""
    now = time.time()

    # Add some items
    for i in range(10):
        content = f"Content {i}"
        item = MemoryItem(
            id=f"item-{i}",
            ts=now,
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )
        store.put(item)

    # Delete some items to create fragmentation
    for i in range(5):
        content = f"Content {i}"
        # Evict by setting TTL to 0 and running eviction
        item = MemoryItem(
            id=f"item-{i}",
            ts=now - 100,
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
            ttl_s=0.1,
        )
        store.put(item)

    store.evict_expired(now)

    # Run compact - should not raise
    store.compact()

    # Verify remaining items still accessible
    assert store.get("item-5") is not None
    assert store.get("item-9") is not None


def test_stats(store: SQLiteMemoryStore) -> None:
    """Test statistics reporting."""
    now = time.time()

    # Initially empty
    stats = store.stats()
    assert stats["total_items"] == 0
    assert stats["oldest_ts"] is None
    assert stats["newest_ts"] is None

    # Add items
    for i in range(5):
        content = f"Content {i}"
        item = MemoryItem(
            id=f"item-{i}",
            ts=now + i,
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )
        store.put(item)

    # Check stats
    stats = store.stats()
    assert stats["total_items"] == 5
    assert stats["oldest_ts"] == pytest.approx(now, abs=0.1)
    assert stats["newest_ts"] == pytest.approx(now + 4, abs=0.1)
    assert stats["db_size_bytes"] > 0


@pytest.mark.skipif(not CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
def test_encryption_at_rest_optional(
    store_with_encryption: SQLiteMemoryStore,
    temp_db_path: Path,
) -> None:
    """Test optional encryption-at-rest.

    Verifies that:
    1. Content can be stored and retrieved with encryption
    2. Plaintext is NOT present in raw database bytes
    """
    original_content = "This is secret content that should be encrypted"

    item = MemoryItem(
        id="encrypted-001",
        ts=time.time(),
        content=original_content,
        content_hash=compute_content_hash(original_content),
        provenance=build_provenance(original_content),
    )

    # Store encrypted
    store_with_encryption.put(item)

    # Retrieve and verify decryption works
    retrieved = store_with_encryption.get("encrypted-001")
    assert retrieved is not None
    # Content should be decrypted on retrieval
    # Note: scrubbing happens before encryption, so check for scrubbed version
    assert "secret" in retrieved.content.lower()

    # Verify plaintext NOT in database file
    store_with_encryption.close()

    with open(temp_db_path, "rb") as f:
        db_bytes = f.read()

    # Original plaintext should NOT be in the file
    # (except possibly in SQLite metadata/headers, so check for the unique phrase)
    assert b"This is secret content that should be encrypted" not in db_bytes


def test_encryption_disabled_by_default(temp_db_path: Path) -> None:
    """Test that encryption is disabled by default."""
    store = SQLiteMemoryStore(str(temp_db_path))

    # Should be able to store and retrieve without encryption
    item = MemoryItem(
        id="plain-001",
        ts=time.time(),
        content="Plain text content",
        content_hash=compute_content_hash("Plain text content"),
        provenance=build_provenance("Plain text content"),
    )

    store.put(item)
    retrieved = store.get("plain-001")

    assert retrieved is not None
    assert "Plain text content" in retrieved.content

    store.close()


@pytest.mark.skipif(CRYPTOGRAPHY_AVAILABLE, reason="Test only when cryptography is NOT available")
def test_encryption_requires_cryptography(temp_db_path: Path) -> None:
    """Test that enabling encryption without cryptography raises ConfigurationError."""
    from mlsdm.utils.errors import ConfigurationError

    encryption_key = os.urandom(32)

    with pytest.raises(ConfigurationError) as exc_info:
        SQLiteMemoryStore(
            str(temp_db_path),
            encryption_key=encryption_key,
        )

    assert "cryptography package" in str(exc_info.value).lower()
    assert "ltm" in str(exc_info.value).lower()


def test_store_raw_option(temp_db_path: Path) -> None:
    """Test that store_raw=True bypasses PII scrubbing."""
    store = SQLiteMemoryStore(str(temp_db_path), store_raw=True)

    original_content = "Contact user@example.com with API key sk-1234567890abcdefghij"

    item = MemoryItem(
        id="raw-001",
        ts=time.time(),
        content=original_content,
        content_hash=compute_content_hash(original_content),
        provenance=build_provenance(original_content),
    )

    store.put(item)
    retrieved = store.get("raw-001")

    assert retrieved is not None
    # With store_raw=True, content should NOT be scrubbed
    assert "user@example.com" in retrieved.content
    assert "sk-1234567890abcdefghij" in retrieved.content

    store.close()
