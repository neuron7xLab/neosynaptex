"""
Unit Tests for Memory Store

Tests for memory store protocols and utilities.
"""

from mlsdm.memory.store import MemoryItem, compute_content_hash


class TestMemoryItem:
    """Test MemoryItem dataclass."""

    def test_memory_item_creation(self):
        """Test creating a MemoryItem with required fields."""
        item = MemoryItem(
            id="test_id",
            ts=1234567890.0,
            content="test content",
            content_hash="abc123"
        )

        assert item.id == "test_id"
        assert item.ts == 1234567890.0
        assert item.content == "test content"
        assert item.content_hash == "abc123"
        assert item.ttl_s is None
        assert item.pii_flags == {}
        assert item.provenance is None

    def test_memory_item_with_optional_fields(self):
        """Test creating a MemoryItem with optional fields."""
        pii_flags = {"email": True}
        item = MemoryItem(
            id="test_id",
            ts=1234567890.0,
            content="test content",
            content_hash="abc123",
            ttl_s=3600.0,
            pii_flags=pii_flags
        )

        assert item.ttl_s == 3600.0
        assert item.pii_flags == {"email": True}


class TestComputeContentHash:
    """Test compute_content_hash function."""

    def test_compute_content_hash_basic(self):
        """Test that compute_content_hash returns a valid SHA256 hash."""
        content = "test content"
        hash_result = compute_content_hash(content)

        # SHA256 hash should be 64 characters (hex)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
        # Should be all hex characters
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_compute_content_hash_deterministic(self):
        """Test that compute_content_hash is deterministic."""
        content = "test content"
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        assert hash1 == hash2

    def test_compute_content_hash_different_content(self):
        """Test that different content produces different hashes."""
        hash1 = compute_content_hash("content1")
        hash2 = compute_content_hash("content2")

        assert hash1 != hash2

    def test_compute_content_hash_empty_string(self):
        """Test compute_content_hash with empty string."""
        hash_result = compute_content_hash("")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64
