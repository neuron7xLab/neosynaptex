"""Smoke tests for MemoryConsolidator.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests memory tagging, consolidation, recall, and eviction.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.memory import MemoryConsolidator


def test_consolidator_creation() -> None:
    """Test MemoryConsolidator initialization."""
    cons = MemoryConsolidator(capacity=10)
    stats = cons.stats()
    assert stats["count"] == 0
    assert stats["consolidated_count"] == 0

    # invalid capacity
    with pytest.raises(ValueError, match="capacity must be positive"):
        MemoryConsolidator(capacity=0)


def test_tag_and_stats() -> None:
    """Test tagging patterns and stats."""
    cons = MemoryConsolidator(capacity=10)

    pattern1 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    trace1 = cons.tag(pattern1, importance=0.8)

    assert trace1.importance == 0.8
    assert trace1.consolidated is False
    assert trace1.strength == 0.0
    assert trace1.recall_count == 0

    stats = cons.stats()
    assert stats["count"] == 1
    assert stats["consolidated_count"] == 0
    assert stats["mean_importance"] == 0.8


def test_tag_validation() -> None:
    """Test tag input validation."""
    cons = MemoryConsolidator(capacity=10)

    # invalid pattern dimension
    with pytest.raises(ValueError, match="pattern must be 1D"):
        cons.tag(np.array([[1.0, 2.0]], dtype=np.float64), importance=0.5)

    # invalid importance
    with pytest.raises(ValueError, match="importance must be in"):
        cons.tag(np.array([1.0, 2.0], dtype=np.float64), importance=1.5)


def test_consolidation() -> None:
    """Test consolidation dynamics."""
    cons = MemoryConsolidator(capacity=10)

    pattern = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    cons.tag(pattern, importance=0.8)

    # low protein, no consolidation
    consolidated = cons.consolidate(protein_level=0.1, temperature=0.5)
    assert len(consolidated) == 0

    # high protein and temperature, consolidation occurs over multiple calls
    for _ in range(5):  # multiple consolidation steps
        cons.consolidate(protein_level=0.9, temperature=1.0)

    stats = cons.stats()
    assert stats["consolidated_count"] > 0
    assert stats["mean_strength"] > 0.5


def test_recall() -> None:
    """Test pattern recall."""
    cons = MemoryConsolidator(capacity=10)

    pattern1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    pattern2 = np.array([0.0, 1.0, 0.0], dtype=np.float64)

    cons.tag(pattern1, importance=0.8)
    cons.tag(pattern2, importance=0.6)

    # recall with similar cue
    cue1 = np.array([0.9, 0.1, 0.0], dtype=np.float64)
    recalled = cons.recall(cue1, threshold=0.5)

    assert recalled is not None
    assert recalled.recall_count == 1

    # recall with no match
    cue2 = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    recalled2 = cons.recall(cue2, threshold=0.9)
    assert recalled2 is None


def test_recall_validation() -> None:
    """Test recall input validation."""
    cons = MemoryConsolidator(capacity=10)

    pattern = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    cons.tag(pattern, importance=0.5)

    # invalid cue dimension
    with pytest.raises(ValueError, match="cue must be 1D"):
        cons.recall(np.array([[1.0, 2.0]], dtype=np.float64), threshold=0.5)

    # zero norm cue
    with pytest.raises(ValueError, match="cue must have non-zero norm"):
        cons.recall(np.array([0.0, 0.0, 0.0], dtype=np.float64), threshold=0.5)

    # invalid threshold
    with pytest.raises(ValueError, match="threshold must be in"):
        cons.recall(pattern, threshold=1.5)


def test_eviction_at_capacity() -> None:
    """Test eviction when capacity is reached."""
    cons = MemoryConsolidator(capacity=3)

    # add 3 patterns
    pattern1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    pattern2 = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    pattern3 = np.array([0.0, 0.0, 1.0], dtype=np.float64)

    cons.tag(pattern1, importance=0.5)
    cons.tag(pattern2, importance=0.8)  # high importance
    cons.tag(pattern3, importance=0.3)

    assert cons.stats()["count"] == 3

    # add 4th pattern, should evict pattern3 (lowest importance)
    pattern4 = np.array([1.0, 1.0, 0.0], dtype=np.float64)
    cons.tag(pattern4, importance=0.7)

    assert cons.stats()["count"] == 3


def test_determinism() -> None:
    """Test that consolidator produces deterministic results."""
    seed_pattern = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)

    # First run
    cons1 = MemoryConsolidator(capacity=10)
    cons1.tag(seed_pattern, importance=0.5)
    cons1.consolidate(protein_level=0.8, temperature=1.0)
    stats1 = cons1.stats()

    # Second run
    cons2 = MemoryConsolidator(capacity=10)
    cons2.tag(seed_pattern.copy(), importance=0.5)
    cons2.consolidate(protein_level=0.8, temperature=1.0)
    stats2 = cons2.stats()

    # Results should be identical
    assert stats1["mean_strength"] == stats2["mean_strength"]
    assert stats1["consolidated_count"] == stats2["consolidated_count"]
