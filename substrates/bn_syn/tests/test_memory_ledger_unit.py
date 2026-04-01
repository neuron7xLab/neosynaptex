"""Unit tests for consolidation ledger invariants."""

from __future__ import annotations

import numpy as np

from bnsyn.memory.ledger import ConsolidationLedger


def test_ledger_empty_init_invariants() -> None:
    ledger = ConsolidationLedger()

    state = ledger.get_state()
    assert state["event_count"] == 0
    assert ledger.get_history() == []
    assert isinstance(state["hash"], str)
    assert len(state["hash"]) == 64


def test_record_event_preserves_count_and_order() -> None:
    ledger = ConsolidationLedger()

    for step in range(3):
        ledger.record_event(
            gate=0.2 + 0.1 * step,
            temperature=0.5 + 0.05 * step,
            step=step,
            timestamp=0.25 * step,
        )

    history = ledger.get_history()
    assert [event["step"] for event in history] == [0, 1, 2]
    assert ledger.get_state()["event_count"] == 3


def test_duplicate_step_is_recorded_as_separate_event() -> None:
    ledger = ConsolidationLedger()

    ledger.record_event(gate=0.4, temperature=0.6, step=7, timestamp=1.0)
    ledger.record_event(gate=0.5, temperature=0.7, step=7, timestamp=2.0)

    history = ledger.get_history()
    assert len(history) == 2
    assert [event["step"] for event in history] == [7, 7]
    assert history[0]["timestamp"] == 1.0
    assert history[1]["timestamp"] == 2.0


def test_ledger_history_roundtrip_via_get_history() -> None:
    tags = np.array([True, False, True, True], dtype=np.bool_)

    ledger = ConsolidationLedger()
    ledger.record_event(
        gate=0.9,
        temperature=0.2,
        step=4,
        timestamp=1.5,
        dw_tags=tags,
        dw_protein=0.8,
    )
    ledger.record_event(gate=0.3, temperature=0.7, step=5, timestamp=1.75)

    history = ledger.get_history()
    assert history == [
        {
            "step": 4,
            "timestamp": 1.5,
            "gate": 0.9,
            "temperature": 0.2,
            "dw_tags_sum": 3.0,
            "dw_protein": 0.8,
            "tag_count": 3,
        },
        {
            "step": 5,
            "timestamp": 1.75,
            "gate": 0.3,
            "temperature": 0.7,
            "dw_tags_sum": None,
            "dw_protein": None,
            "tag_count": None,
        },
    ]


def test_compute_hash_is_deterministic_for_identical_sequences() -> None:
    first = ConsolidationLedger()
    second = ConsolidationLedger()

    for ledger in (first, second):
        ledger.record_event(gate=0.75, temperature=0.25, step=12, timestamp=3.0)
        ledger.record_event(gate=0.55, temperature=0.4, step=13, timestamp=3.5)

    assert first.compute_hash() == second.compute_hash()
