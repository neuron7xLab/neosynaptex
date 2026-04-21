"""ProbeSession tests: gamma trajectory wiring, MIN_TURNS gate, seed log."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from probe.dialogue_adapter import Turn
from probe.session import (
    MIN_TURNS,
    InsufficientDataError,
    ProbeSession,
    load_seed_ledger,
    log_seed,
)


def _make_turns(n: int, start: int = 0) -> list[Turn]:
    turns: list[Turn] = []
    for i in range(n):
        content = " ".join(f"w{start + i}_{j}" for j in range(6 + i))
        turns.append(
            Turn(
                role="human" if i % 2 == 0 else "assistant",
                content=content,
                token_count=20 + 2 * i,
            )
        )
    return turns


def test_gamma_trajectory_length_matches_push_count() -> None:
    session = ProbeSession(window=16, seed=7)
    for t in _make_turns(12):
        session.push_turn(t)
    traj = session.gamma_trajectory()
    assert len(traj) == 12
    assert session.n_turns == 12


def test_insufficient_data_raises() -> None:
    session = ProbeSession(window=16, seed=7)
    for t in _make_turns(MIN_TURNS - 1):
        session.push_turn(t)
    with pytest.raises(InsufficientDataError):
        session.export_evidence()


def test_export_evidence_contains_seed_and_fields() -> None:
    session = ProbeSession(window=16, seed=13)
    for t in _make_turns(MIN_TURNS + 4):
        session.push_turn(t)
    ev = session.export_evidence()
    assert ev["seed"] == 13
    assert ev["n_turns"] == MIN_TURNS + 4
    assert isinstance(ev["gamma_trajectory"], list)
    assert len(ev["gamma_trajectory"]) == MIN_TURNS + 4
    assert "final_state" in ev
    for key in ("gamma_mean", "phase", "cross_coherence"):
        assert key in ev["final_state"]


def test_state_is_frozen() -> None:
    session = ProbeSession(window=16, seed=7)
    for t in _make_turns(MIN_TURNS):
        session.push_turn(t)
    state = session.states()[-1]
    with pytest.raises(FrozenInstanceError):
        state.gamma_mean = 42.0  # type: ignore[misc]


def test_seed_ledger_logging(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    ProbeSession(window=16, seed=7, seed_ledger_path=ledger)
    ProbeSession(window=16, seed=11, seed_ledger_path=ledger)
    entries = load_seed_ledger(ledger)
    assert len(entries) == 2
    assert {e.seed for e in entries} == {7, 11}


def test_seed_ledger_append_explicit(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    log_seed(ledger, 42, "unit-test-hash")
    entries = load_seed_ledger(ledger)
    assert len(entries) == 1
    assert entries[0].seed == 42
    assert entries[0].session_hash == "unit-test-hash"


def test_invalid_window_rejected() -> None:
    with pytest.raises(ValueError):
        ProbeSession(window=4, seed=7)


def test_phase_trajectory_strings() -> None:
    session = ProbeSession(window=16, seed=7)
    for t in _make_turns(MIN_TURNS + 2):
        session.push_turn(t)
    phases = session.phase_trajectory()
    assert len(phases) == MIN_TURNS + 2
    for p in phases:
        assert isinstance(p, str)
