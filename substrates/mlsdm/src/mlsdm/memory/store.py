"""MemoryStore Protocol and Data Structures for Persistent LTM.

This module provides the stable interface for long-term memory (LTM) storage
backends. It defines protocols, dataclasses, and utilities for storing and
retrieving memory items with metadata including provenance, TTL, and PII flags.

The design follows these principles:
- Protocol-based for flexibility (multiple backends possible)
- Type-safe with full type hints
- Separation of concerns (storage abstraction)
- AI Safety: built-in PII scrubbing and provenance tracking
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from mlsdm.memory.provenance import MemoryProvenance


@dataclass
class MemoryItem:
    """A memory item with metadata for persistent storage.

    Attributes:
        id: Unique identifier for this memory
        ts: Unix timestamp when memory was created
        content: Memory content (text, may be scrubbed)
        content_hash: SHA256 hash of original content for deduplication
        ttl_s: Time-to-live in seconds (None = no expiration)
        pii_flags: Dictionary of detected PII types and their status
        provenance: Optional memory provenance metadata (required for persistent LTM)
    """

    id: str
    ts: float
    content: str
    content_hash: str
    ttl_s: float | None = None
    pii_flags: dict[str, Any] = field(default_factory=dict)
    provenance: MemoryProvenance | None = None


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for deduplication and audit.

    Args:
        content: Text content to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class MemoryStore(Protocol):
    """Protocol for long-term memory storage backends.

    This protocol defines the stable interface that all LTM storage
    implementations must provide. It supports:
    - Basic CRUD operations (put/get)
    - Text-based querying (LIKE search in v1)
    - TTL-based eviction
    - Compaction/vacuum
    - Statistics/observability
    """

    def put(self, item: MemoryItem) -> str:
        """Store a memory item.

        Args:
            item: Memory item to store

        Returns:
            The ID of the stored item (usually item.id)

        Raises:
            Exception: On storage failure
        """
        ...

    def get(self, item_id: str) -> MemoryItem | None:
        """Retrieve a memory item by ID.

        Args:
            item_id: Unique identifier of the memory

        Returns:
            MemoryItem if found, None otherwise
        """
        ...

    def query(
        self,
        text: str,
        *,
        limit: int = 10,
        since_ts: float | None = None,
        tags: list[str] | None = None,
    ) -> list[MemoryItem]:
        """Query memories by text content.

        In v1, this uses simple LIKE-based text search.
        Future versions may support vector similarity search.

        Args:
            text: Text to search for in content
            limit: Maximum number of results to return
            since_ts: Only return memories created after this timestamp
            tags: Reserved for future use (tag-based filtering)

        Returns:
            List of matching MemoryItem objects, ordered by relevance/recency
        """
        ...

    def evict_expired(self, now_ts: float) -> int:
        """Remove expired memories based on TTL.

        Removes all memories where ts + ttl_s < now_ts.

        Args:
            now_ts: Current timestamp for comparison

        Returns:
            Number of items evicted
        """
        ...

    def compact(self) -> None:
        """Perform storage compaction/vacuum.

        For SQLite: runs VACUUM to reclaim space.
        For other backends: implementation-specific cleanup.
        """
        ...

    def stats(self) -> dict[str, Any]:
        """Get storage statistics for observability.

        Returns:
            Dictionary with statistics such as:
            - total_items: Number of stored items
            - db_size_bytes: Storage size in bytes
            - oldest_ts: Timestamp of oldest item
            - newest_ts: Timestamp of newest item
        """
        ...
