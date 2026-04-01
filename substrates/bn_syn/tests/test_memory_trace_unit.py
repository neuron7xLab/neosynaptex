"""Unit tests for memory trace buffer invariants."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.memory.trace import MemoryTrace


def test_trace_empty_buffer_behavior() -> None:
    trace = MemoryTrace(capacity=3)

    assert trace.get_state()["count"] == 0
    assert trace.recall(np.array([1.0, 0.0], dtype=np.float64), threshold=0.5) == []


def test_trace_tagging_to_capacity_preserves_order() -> None:
    trace = MemoryTrace(capacity=3)

    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.1)
    trace.tag(np.array([0.0, 1.0], dtype=np.float64), importance=0.2)
    trace.tag(np.array([1.0, 1.0], dtype=np.float64), importance=0.3)

    assert len(trace.patterns) == 3
    np.testing.assert_allclose(trace.patterns[0], np.array([1.0, 0.0], dtype=np.float64))
    np.testing.assert_allclose(trace.importance, np.array([0.1, 0.2, 0.3], dtype=np.float64))


def test_trace_overflow_drops_oldest_pattern() -> None:
    trace = MemoryTrace(capacity=2)

    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.1)
    trace.tag(np.array([0.0, 1.0], dtype=np.float64), importance=0.2)
    trace.tag(np.array([1.0, 1.0], dtype=np.float64), importance=0.3)

    assert len(trace.patterns) == 2
    np.testing.assert_allclose(trace.patterns[0], np.array([0.0, 1.0], dtype=np.float64))
    np.testing.assert_allclose(trace.patterns[1], np.array([1.0, 1.0], dtype=np.float64))
    np.testing.assert_allclose(trace.importance, np.array([0.2, 0.3], dtype=np.float64))


def test_trace_recall_is_deterministic_and_updates_counters() -> None:
    trace = MemoryTrace(capacity=4)
    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.5)
    trace.tag(np.array([0.8, 0.2], dtype=np.float64), importance=0.6)
    trace.tag(np.array([-1.0, 0.0], dtype=np.float64), importance=0.7)

    cue = np.array([1.0, 0.0], dtype=np.float64)
    first = trace.recall(cue, threshold=0.7)
    second = trace.recall(cue, threshold=0.7)

    assert first == second == [0, 1]
    np.testing.assert_allclose(trace.recall_counters, np.array([2.0, 2.0, 0.0], dtype=np.float64))


def test_trace_rejects_invalid_pattern_shape() -> None:
    trace = MemoryTrace(capacity=2)

    with pytest.raises(ValueError, match="pattern must be 1D array"):
        trace.tag(np.array([[1.0, 2.0]], dtype=np.float64), importance=0.2)


def test_tag_normalizes_patterns_to_float64() -> None:
    trace = MemoryTrace(capacity=2)

    trace.tag(np.array([1.0, 2.0], dtype=np.float32), importance=0.4)

    assert trace.patterns[0].dtype == np.float64



def test_trace_init_with_seeded_state_and_capacity_guards() -> None:
    seeded = MemoryTrace(
        capacity=2,
        patterns=[np.array([1.0, 0.0], dtype=np.float64)],
        importance=np.array([0.3], dtype=np.float64),
        timestamps=np.array([0.0], dtype=np.float64),
        recall_counters=np.array([1.0], dtype=np.float64),
    )

    assert seeded.get_state()["count"] == 1
    np.testing.assert_allclose(seeded.importance, np.array([0.3], dtype=np.float64))
    np.testing.assert_allclose(seeded.timestamps, np.array([0.0], dtype=np.float64))
    np.testing.assert_allclose(seeded.recall_counters, np.array([1.0], dtype=np.float64))

    with pytest.raises(ValueError, match="initial patterns exceed capacity"):
        MemoryTrace(
            capacity=1,
            patterns=[
                np.array([1.0], dtype=np.float64),
                np.array([2.0], dtype=np.float64),
            ],
            importance=np.array([0.1, 0.2], dtype=np.float64),
            timestamps=np.array([0.0, 1.0], dtype=np.float64),
            recall_counters=np.array([0.0, 0.0], dtype=np.float64),
        )

    with pytest.raises(ValueError, match="importance length must match patterns length"):
        MemoryTrace(
            capacity=3,
            patterns=[np.array([1.0], dtype=np.float64)],
            importance=np.array([], dtype=np.float64),
            timestamps=np.array([0.0], dtype=np.float64),
            recall_counters=np.array([0.0], dtype=np.float64),
        )


def test_remove_at_supports_middle_removal_and_invalid_index() -> None:
    trace = MemoryTrace(capacity=4)
    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.1)
    trace.tag(np.array([0.0, 1.0], dtype=np.float64), importance=0.2)
    trace.tag(np.array([1.0, 1.0], dtype=np.float64), importance=0.3)

    trace.remove_at(1)

    assert len(trace.patterns) == 2
    np.testing.assert_allclose(trace.importance, np.array([0.1, 0.3], dtype=np.float64))
    np.testing.assert_allclose(trace.timestamps, np.array([0.0, 2.0], dtype=np.float64))
    np.testing.assert_allclose(trace.recall_counters, np.array([0.0, 0.0], dtype=np.float64))

    with pytest.raises(IndexError, match="memory index out of range"):
        trace.remove_at(5)



def test_trace_init_rejects_timestamp_and_recall_length_mismatch() -> None:
    with pytest.raises(ValueError, match="timestamps length must match patterns length"):
        MemoryTrace(
            capacity=3,
            patterns=[np.array([1.0], dtype=np.float64)],
            importance=np.array([0.1], dtype=np.float64),
            timestamps=np.array([], dtype=np.float64),
            recall_counters=np.array([0.0], dtype=np.float64),
        )

    with pytest.raises(ValueError, match="recall_counters length must match patterns length"):
        MemoryTrace(
            capacity=3,
            patterns=[np.array([1.0], dtype=np.float64)],
            importance=np.array([0.1], dtype=np.float64),
            timestamps=np.array([0.0], dtype=np.float64),
            recall_counters=np.array([], dtype=np.float64),
        )


def test_get_state_returns_safe_copies() -> None:
    trace = MemoryTrace(capacity=2)
    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.5)

    state = trace.get_state()
    state["importance"][0] = 99.0
    state["timestamps"][0] = 88.0
    state["recall_counters"][0] = 77.0

    np.testing.assert_allclose(trace.importance, np.array([0.5], dtype=np.float64))
    np.testing.assert_allclose(trace.timestamps, np.array([0.0], dtype=np.float64))
    np.testing.assert_allclose(trace.recall_counters, np.array([0.0], dtype=np.float64))


def test_remove_at_last_index_covers_tail_zero_path() -> None:
    trace = MemoryTrace(capacity=3)
    trace.tag(np.array([1.0, 0.0], dtype=np.float64), importance=0.1)
    trace.tag(np.array([0.0, 1.0], dtype=np.float64), importance=0.2)

    trace.remove_at(1)

    assert len(trace.patterns) == 1
    np.testing.assert_allclose(trace.importance, np.array([0.1], dtype=np.float64))
    np.testing.assert_allclose(trace.timestamps, np.array([0.0], dtype=np.float64))
    np.testing.assert_allclose(trace.recall_counters, np.array([0.0], dtype=np.float64))
