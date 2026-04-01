"""Smoke tests for memory trace and consolidation ledger.

Parameters
----------
None

Returns
-------
None

Notes
-----
Tests memory tagging, recall, consolidation, and ledger.

References
----------
docs/features/memory.md
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.memory import ConsolidationLedger, MemoryTrace


def test_memory_trace_basic() -> None:
    """Test basic MemoryTrace functionality."""
    trace = MemoryTrace(capacity=10)
    state = trace.get_state()
    assert state["count"] == 0

    # tag a pattern
    pattern = np.ones(5)
    trace.tag(pattern, importance=0.5)
    state = trace.get_state()
    assert state["count"] == 1
    assert len(trace.patterns) == 1


def test_memory_trace_invalid_capacity() -> None:
    """Test invalid capacity rejection."""
    with pytest.raises(ValueError, match="capacity must be positive"):
        MemoryTrace(capacity=0)


def test_memory_tag_validation() -> None:
    """Test validation in MemoryTrace.tag."""
    trace = MemoryTrace(capacity=2)

    with pytest.raises(ValueError, match="pattern must be 1D array"):
        trace.tag(np.zeros((2, 2)), importance=0.1)

    with pytest.raises(ValueError, match="importance must be non-negative"):
        trace.tag(np.zeros(2), importance=-0.1)


def test_memory_capacity() -> None:
    """Test capacity enforcement."""
    trace = MemoryTrace(capacity=3)

    for i in range(5):
        pattern = np.ones(5) * i
        trace.tag(pattern, importance=0.5)

    state = trace.get_state()
    assert state["count"] == 3  # capped at capacity


def test_memory_recall() -> None:
    """Test pattern recall."""
    trace = MemoryTrace(capacity=10)

    target = np.array([1.0, 0.0, 0.0])
    trace.tag(target, importance=0.8)

    # recall with exact match
    recalled = trace.recall(target, threshold=0.9)
    assert len(recalled) > 0


def test_memory_recall_validation() -> None:
    """Test recall validation and edge cases."""
    trace = MemoryTrace(capacity=3)

    with pytest.raises(ValueError, match="cue must be 1D array"):
        trace.recall(np.zeros((1, 2)), threshold=0.0)

    with pytest.raises(ValueError, match="cue must have non-zero norm"):
        trace.recall(np.zeros(2), threshold=0.0)

    with pytest.raises(ValueError, match="threshold must be in"):
        trace.recall(np.ones(2), threshold=2.0)

    assert trace.recall(np.ones(2), threshold=0.0) == []


def test_memory_recall_shape_mismatch_and_zero_norm() -> None:
    """Test recall behavior with shape mismatch and zero-norm patterns."""
    trace = MemoryTrace(capacity=5)
    trace.tag(np.array([1.0, 0.0]), importance=0.5)
    trace.tag(np.array([0.0, 0.0]), importance=0.2)
    trace.tag(np.array([1.0, 0.0, 0.0]), importance=0.3)

    indices = trace.recall(np.array([1.0, 0.0]), threshold=0.5)

    assert indices == [0]
    assert trace.recall_counters[0] == 1.0
    assert trace.recall_counters[1] == 0.0
    assert trace.recall_counters[2] == 0.0


def test_memory_consolidation() -> None:
    """Test consolidation."""
    trace = MemoryTrace(capacity=10)

    pattern = np.ones(5)
    trace.tag(pattern, importance=0.5)

    # consolidate
    trace.consolidate(protein_level=0.9, temperature=1.0)

    state = trace.get_state()
    # importance should increase
    assert state["importance"][0] > 0.5


def test_memory_consolidation_validation() -> None:
    """Test consolidation parameter validation."""
    trace = MemoryTrace(capacity=3)

    with pytest.raises(ValueError, match="protein_level must be in"):
        trace.consolidate(protein_level=1.5, temperature=0.0)

    with pytest.raises(ValueError, match="temperature must be non-negative"):
        trace.consolidate(protein_level=0.2, temperature=-1.0)

    trace.consolidate(protein_level=0.2, temperature=0.0)
    assert trace.get_state()["count"] == 0


def test_ledger_basic() -> None:
    """Test basic ConsolidationLedger functionality."""
    ledger = ConsolidationLedger()
    assert len(ledger.get_history()) == 0

    # record event
    ledger.record_event(gate=0.8, temperature=1.0, step=100)

    history = ledger.get_history()
    assert len(history) == 1
    assert history[0]["gate"] == 0.8


def test_ledger_hash() -> None:
    """Test ledger hash stability."""
    ledger1 = ConsolidationLedger()
    ledger2 = ConsolidationLedger()

    ledger1.record_event(gate=0.5, temperature=1.0, step=100)
    ledger2.record_event(gate=0.5, temperature=1.0, step=100)

    # hashes should match for identical events
    assert ledger1.compute_hash() == ledger2.compute_hash()


def test_ledger_with_dualweights() -> None:
    """Test ledger with DualWeights info."""
    ledger = ConsolidationLedger()

    # record with tags
    ledger.record_event(
        gate=0.9,
        temperature=0.8,
        step=200,
        dw_tags=np.array([True, False, True]),
        dw_protein=0.75,
    )

    history = ledger.get_history()
    assert len(history) == 1
    assert history[0]["dw_protein"] == 0.75
