"""
Unit Tests for SQLite Memory Store

Tests for the SQLiteMemoryStore implementation including:
- Basic CRUD operations (put, get, query)
- TTL-based eviction
- Encryption-at-rest (when cryptography is available)
- PII scrubbing
- Storage statistics and compaction
"""

import os
import time
from datetime import datetime

import pytest

from mlsdm.memory.provenance import MemoryProvenance, MemoryProvenanceError, MemorySource
from mlsdm.memory.sqlite_store import _CRYPTOGRAPHY_AVAILABLE, SQLiteMemoryStore
from mlsdm.memory.store import MemoryItem, compute_content_hash
from mlsdm.utils.errors import ConfigurationError


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


class TestSQLiteMemoryStoreInit:
    """Test SQLiteMemoryStore initialization."""

    def test_basic_initialization(self, tmp_path):
        """Test store can be initialized with just a db path."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        assert store.db_path == db_path
        assert store.store_raw is False  # Default: scrubbing enabled
        assert store._cipher is None  # No encryption by default
        store.close()

    def test_initialization_with_store_raw(self, tmp_path):
        """Test store can be initialized with store_raw=True."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path, store_raw=True)

        assert store.store_raw is True
        store.close()

    def test_lazy_database_initialization(self, tmp_path):
        """Test database is not created until first use."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Database file should not exist yet (lazy init)
        assert not os.path.exists(db_path)

        # First operation triggers initialization
        store._get_connection()
        assert os.path.exists(db_path)
        store.close()

    @pytest.mark.skipif(not _CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
    def test_initialization_with_valid_encryption_key(self, tmp_path):
        """Test store initializes with valid 32-byte encryption key."""
        db_path = str(tmp_path / "test.db")
        encryption_key = os.urandom(32)

        store = SQLiteMemoryStore(db_path=db_path, encryption_key=encryption_key)

        assert store._cipher is not None
        store.close()

    @pytest.mark.skipif(not _CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
    def test_initialization_with_invalid_encryption_key_length(self, tmp_path):
        """Test store rejects encryption keys that are not 32 bytes."""
        db_path = str(tmp_path / "test.db")
        bad_key = os.urandom(16)  # 16 bytes instead of 32

        with pytest.raises(ConfigurationError) as exc_info:
            SQLiteMemoryStore(db_path=db_path, encryption_key=bad_key)

        assert "32 bytes" in str(exc_info.value)

    def test_initialization_encryption_without_cryptography(self, tmp_path, monkeypatch):
        """Test store raises error when encryption requested but cryptography unavailable."""
        # Skip if cryptography is actually available
        if _CRYPTOGRAPHY_AVAILABLE:
            # We can test this by patching the availability flag
            import mlsdm.memory.sqlite_store as store_module

            original_value = store_module._CRYPTOGRAPHY_AVAILABLE
            try:
                monkeypatch.setattr(store_module, "_CRYPTOGRAPHY_AVAILABLE", False)

                db_path = str(tmp_path / "test.db")
                encryption_key = b"x" * 32

                with pytest.raises(ConfigurationError) as exc_info:
                    SQLiteMemoryStore(db_path=db_path, encryption_key=encryption_key)

                assert "cryptography package" in str(exc_info.value)
            finally:
                # Restore original value
                monkeypatch.setattr(store_module, "_CRYPTOGRAPHY_AVAILABLE", original_value)


class TestSQLiteMemoryStorePut:
    """Test SQLiteMemoryStore put operation."""

    def test_put_basic_item(self, tmp_path):
        """Test putting a basic memory item."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        content = "Hello world"
        item = MemoryItem(
            id="test_id_1",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )

        result_id = store.put(item)

        assert result_id == "test_id_1"
        store.close()

    def test_put_requires_provenance(self, tmp_path):
        """Test that provenance is required for persistent storage."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        content = "Missing provenance"
        item = MemoryItem(
            id="no_prov",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
        )

        with pytest.raises(MemoryProvenanceError, match="provenance is required"):
            store.put(item)

        store.close()

    def test_put_with_pii_scrubbing(self, tmp_path):
        """Test PII is scrubbed when store_raw=False (default)."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path, store_raw=False)

        content = "Contact me at test@example.com for details"
        item = MemoryItem(
            id="test_pii",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )

        store.put(item)
        retrieved = store.get("test_pii")

        # Email should be scrubbed
        assert "test@example.com" not in retrieved.content
        store.close()

    def test_put_without_pii_scrubbing(self, tmp_path):
        """Test PII is preserved when store_raw=True."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path, store_raw=True)

        original_content = "Contact me at test@example.com for details"
        item = MemoryItem(
            id="test_raw",
            ts=time.time(),
            content=original_content,
            content_hash=compute_content_hash(original_content),
            provenance=build_provenance(original_content),
        )

        store.put(item)
        retrieved = store.get("test_raw")

        # Email should be preserved
        assert "test@example.com" in retrieved.content
        store.close()

    def test_put_with_provenance(self, tmp_path):
        """Test storing item with provenance metadata."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        provenance = MemoryProvenance(
            source=MemorySource.SYSTEM_PROMPT,
            confidence=0.95,
            timestamp=datetime.now(),
            llm_model="gpt-4",
            parent_id="parent_123",
            content_hash=compute_content_hash("Test content with provenance"),
        )

        item = MemoryItem(
            id="test_prov",
            ts=time.time(),
            content="Test content with provenance",
            content_hash=compute_content_hash("Test content with provenance"),
            provenance=provenance,
        )

        store.put(item)
        retrieved = store.get("test_prov")

        assert retrieved.provenance is not None
        assert retrieved.provenance.source == MemorySource.SYSTEM_PROMPT
        assert retrieved.provenance.confidence == 0.95
        assert retrieved.provenance.llm_model == "gpt-4"
        assert retrieved.provenance.parent_id == "parent_123"
        store.close()

    def test_put_with_ttl(self, tmp_path):
        """Test storing item with TTL."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        content = "Temporary content"
        item = MemoryItem(
            id="test_ttl",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
            ttl_s=3600.0,  # 1 hour TTL
        )

        store.put(item)
        retrieved = store.get("test_ttl")

        assert retrieved.ttl_s == 3600.0
        store.close()

    def test_put_with_pii_flags(self, tmp_path):
        """Test storing item with PII flags."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        pii_flags = {"email": True, "phone": False}
        content = "Content with PII flags"
        item = MemoryItem(
            id="test_flags",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
            pii_flags=pii_flags,
        )

        store.put(item)
        retrieved = store.get("test_flags")

        assert retrieved.pii_flags == {"email": True, "phone": False}
        store.close()

    def test_put_upsert_existing(self, tmp_path):
        """Test putting with same ID replaces existing item."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # First insert
        content = "Original content"
        item1 = MemoryItem(
            id="same_id",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )
        store.put(item1)

        # Update
        updated_content = "Updated content"
        item2 = MemoryItem(
            id="same_id",
            ts=time.time(),
            content=updated_content,
            content_hash=compute_content_hash(updated_content),
            provenance=build_provenance(updated_content),
        )
        store.put(item2)

        retrieved = store.get("same_id")
        assert "Updated" in retrieved.content
        store.close()


class TestSQLiteMemoryStoreGet:
    """Test SQLiteMemoryStore get operation."""

    def test_get_existing_item(self, tmp_path):
        """Test getting an existing item by ID."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        content = "Content to retrieve"
        item = MemoryItem(
            id="get_test",
            ts=1234567890.0,
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )
        store.put(item)

        retrieved = store.get("get_test")

        assert retrieved is not None
        assert retrieved.id == "get_test"
        assert retrieved.ts == 1234567890.0
        store.close()

    def test_get_nonexistent_item(self, tmp_path):
        """Test getting a non-existent item returns None."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        result = store.get("nonexistent_id")

        assert result is None
        store.close()


class TestSQLiteMemoryStoreQuery:
    """Test SQLiteMemoryStore query operation."""

    def test_query_basic_text_search(self, tmp_path):
        """Test basic text search query."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Insert multiple items
        for i, content in enumerate(["Hello world", "Goodbye world", "Hello universe"]):
            item = MemoryItem(
                id=f"query_{i}",
                ts=time.time() + i,
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        # Query for "Hello"
        results = store.query("Hello")

        assert len(results) == 2
        assert all("Hello" in r.content for r in results)
        store.close()

    def test_query_with_limit(self, tmp_path):
        """Test query respects limit parameter."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Insert 10 items
        for i in range(10):
            content = f"Test content {i}"
            item = MemoryItem(
                id=f"limit_{i}",
                ts=time.time() + i,
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        results = store.query("Test", limit=3)

        assert len(results) == 3
        store.close()

    def test_query_with_since_ts(self, tmp_path):
        """Test query filters by timestamp."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        base_ts = 1000000.0

        # Insert items at different timestamps
        for i in range(5):
            content = f"Content at time {i}"
            item = MemoryItem(
                id=f"ts_{i}",
                ts=base_ts + i * 100,
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        # Query only recent items
        results = store.query("Content", since_ts=base_ts + 250)

        assert len(results) == 2  # Items 3 and 4
        store.close()

    def test_query_returns_ordered_by_recency(self, tmp_path):
        """Test query results are ordered by timestamp (most recent first)."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Insert items with specific timestamps
        for i in range(3):
            content = f"Search term {i}"
            item = MemoryItem(
                id=f"order_{i}",
                ts=1000 + i * 100,  # 1000, 1100, 1200
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        results = store.query("Search")

        # Most recent first
        assert results[0].id == "order_2"
        assert results[-1].id == "order_0"
        store.close()

    def test_query_no_results(self, tmp_path):
        """Test query returns empty list when no matches."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        content = "Hello world"
        item = MemoryItem(
            id="no_match",
            ts=time.time(),
            content=content,
            content_hash=compute_content_hash(content),
            provenance=build_provenance(content),
        )
        store.put(item)

        results = store.query("xyz123nonexistent")

        assert results == []
        store.close()


class TestSQLiteMemoryStoreEviction:
    """Test TTL-based eviction."""

    def test_evict_expired_items(self, tmp_path):
        """Test evict_expired removes items past TTL."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        now = time.time()

        # Insert expired item (TTL already passed)
        expired_content = "Expired content"
        expired_item = MemoryItem(
            id="expired",
            ts=now - 100,  # 100 seconds ago
            content=expired_content,
            content_hash=compute_content_hash(expired_content),
            provenance=build_provenance(expired_content),
            ttl_s=50.0,  # 50 second TTL (already expired)
        )
        store.put(expired_item)

        # Insert non-expired item
        valid_content = "Valid content"
        valid_item = MemoryItem(
            id="valid",
            ts=now,
            content=valid_content,
            content_hash=compute_content_hash(valid_content),
            provenance=build_provenance(valid_content),
            ttl_s=3600.0,  # 1 hour TTL
        )
        store.put(valid_item)

        # Insert item without TTL (never expires)
        permanent_content = "Permanent content"
        permanent_item = MemoryItem(
            id="permanent",
            ts=now - 1000,
            content=permanent_content,
            content_hash=compute_content_hash(permanent_content),
            provenance=build_provenance(permanent_content),
        )
        store.put(permanent_item)

        # Evict expired
        evicted_count = store.evict_expired(now)

        assert evicted_count == 1  # Only expired item
        assert store.get("expired") is None
        assert store.get("valid") is not None
        assert store.get("permanent") is not None
        store.close()

    def test_evict_expired_returns_zero_when_none_expired(self, tmp_path):
        """Test evict_expired returns 0 when no items are expired."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        now = time.time()

        # Insert non-expired item
        fresh_content = "Fresh content"
        item = MemoryItem(
            id="fresh",
            ts=now,
            content=fresh_content,
            content_hash=compute_content_hash(fresh_content),
            provenance=build_provenance(fresh_content),
            ttl_s=3600.0,
        )
        store.put(item)

        evicted_count = store.evict_expired(now)

        assert evicted_count == 0
        store.close()


class TestSQLiteMemoryStoreStats:
    """Test storage statistics."""

    def test_stats_basic(self, tmp_path):
        """Test stats returns expected structure."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        stats = store.stats()

        assert "total_items" in stats
        assert "db_size_bytes" in stats
        assert "oldest_ts" in stats
        assert "newest_ts" in stats
        store.close()

    def test_stats_empty_store(self, tmp_path):
        """Test stats on empty store."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Initialize by calling get (triggers lazy init)
        store.get("nonexistent")

        stats = store.stats()

        assert stats["total_items"] == 0
        assert stats["oldest_ts"] is None
        assert stats["newest_ts"] is None
        store.close()

    def test_stats_with_items(self, tmp_path):
        """Test stats with items."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Insert items
        for i in range(5):
            content = f"Content {i}"
            item = MemoryItem(
                id=f"stats_{i}",
                ts=1000.0 + i * 10,
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        stats = store.stats()

        assert stats["total_items"] == 5
        assert stats["oldest_ts"] == 1000.0
        assert stats["newest_ts"] == 1040.0
        assert stats["db_size_bytes"] > 0
        store.close()


class TestSQLiteMemoryStoreCompact:
    """Test storage compaction."""

    def test_compact_runs_without_error(self, tmp_path):
        """Test compact operation runs successfully."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Insert and delete some items
        for i in range(10):
            content = f"Temporary content {i}"
            item = MemoryItem(
                id=f"compact_{i}",
                ts=time.time(),
                content=content,
                content_hash=compute_content_hash(content),
                provenance=build_provenance(content),
            )
            store.put(item)

        # Compact should run without error
        store.compact()
        store.close()


class TestSQLiteMemoryStoreEncryption:
    """Test encryption-at-rest functionality."""

    @pytest.mark.skipif(not _CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
    def test_encrypted_put_and_get(self, tmp_path):
        """Test put/get with encryption enabled."""
        db_path = str(tmp_path / "encrypted.db")
        encryption_key = os.urandom(32)

        store = SQLiteMemoryStore(db_path=db_path, encryption_key=encryption_key)

        original_content = "This is secret content"
        item = MemoryItem(
            id="encrypted_1",
            ts=time.time(),
            content=original_content,
            content_hash=compute_content_hash(original_content),
            provenance=build_provenance(original_content),
        )
        store.put(item)

        retrieved = store.get("encrypted_1")

        assert retrieved.content == original_content
        store.close()

    @pytest.mark.skipif(not _CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
    def test_encrypted_content_stored_as_ciphertext(self, tmp_path):
        """Test that encrypted content is actually stored as ciphertext."""
        import sqlite3

        db_path = str(tmp_path / "encrypted.db")
        encryption_key = os.urandom(32)

        store = SQLiteMemoryStore(db_path=db_path, encryption_key=encryption_key)

        original_content = "This is plaintext secret"
        item = MemoryItem(
            id="cipher_check",
            ts=time.time(),
            content=original_content,
            content_hash=compute_content_hash(original_content),
            provenance=build_provenance(original_content),
        )
        store.put(item)
        store.close()

        # Directly read database to verify ciphertext
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content, ciphertext FROM memories WHERE id = ?", ("cipher_check",))
        row = cursor.fetchone()
        conn.close()

        # Content column should show "<encrypted>"
        assert row[0] == "<encrypted>"
        # Ciphertext should not be None
        assert row[1] is not None

    @pytest.mark.skipif(not _CRYPTOGRAPHY_AVAILABLE, reason="cryptography not installed")
    def test_encrypted_get_with_provenance(self, tmp_path):
        """Test get returns properly decrypted content with provenance."""
        db_path = str(tmp_path / "encrypted.db")
        encryption_key = os.urandom(32)

        store = SQLiteMemoryStore(db_path=db_path, encryption_key=encryption_key)

        provenance = MemoryProvenance(
            source=MemorySource.USER_INPUT,
            confidence=0.8,
            timestamp=datetime.now(),
            content_hash=compute_content_hash("Encrypted with provenance"),
        )
        item = MemoryItem(
            id="enc_prov",
            ts=time.time(),
            content="Encrypted with provenance",
            content_hash=compute_content_hash("Encrypted with provenance"),
            provenance=provenance,
        )
        store.put(item)

        retrieved = store.get("enc_prov")

        assert retrieved.provenance is not None
        assert retrieved.provenance.source == MemorySource.USER_INPUT
        store.close()


class TestSQLiteMemoryStoreClose:
    """Test connection closing."""

    def test_close_connection(self, tmp_path):
        """Test close properly closes database connection."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Trigger connection
        store._get_connection()
        assert store._conn is not None

        # Close
        store.close()
        assert store._conn is None

    def test_double_close_safe(self, tmp_path):
        """Test closing twice doesn't cause error."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        store._get_connection()
        store.close()
        store.close()  # Second close should be safe

    def test_destructor_closes_connection(self, tmp_path):
        """Test __del__ closes connection."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        store._get_connection()
        assert store._conn is not None

        # Manually call __del__
        store.__del__()
        assert store._conn is None


class TestSQLiteMemoryStoreSchemaInit:
    """Test schema initialization."""

    def test_schema_created_on_first_use(self, tmp_path):
        """Test tables and indexes are created on first use."""
        import sqlite3

        db_path = str(tmp_path / "schema_test.db")
        store = SQLiteMemoryStore(db_path=db_path)

        # Trigger schema creation
        store._get_connection()
        store.close()

        # Verify schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        )
        assert cursor.fetchone() is not None

        # Check indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_memories_ts'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_memories_content_hash'"
        )
        assert cursor.fetchone() is not None

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
