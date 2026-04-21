"""Anti-tautology battery tests (AT-1..AT-4)."""

from __future__ import annotations

import math

from probe.anti_tautology import (
    AntiTautologyResult,
    run_anti_tautology,
)
from probe.dialogue_adapter import Turn
from probe.session import MIN_TURNS, ProbeSession


def _growing_session(n: int, seed: int = 7) -> ProbeSession:
    import random

    rng = random.Random(seed)
    session = ProbeSession(window=16, seed=seed)
    for i in range(n):
        content = " ".join(
            "".join(rng.choice("abcdefghij") for _ in range(5)) for _ in range(8 + i)
        )
        session.push_turn(
            Turn(
                role="human" if i % 2 == 0 else "assistant",
                content=content,
                token_count=30 + 2 * i,
            )
        )
    return session


def _flat_vocab_session(n: int, seed: int = 7) -> ProbeSession:
    vocab = ["foo", "bar", "baz", "qux"]
    session = ProbeSession(window=16, seed=seed)
    import random

    rng = random.Random(seed)
    for i in range(n):
        content = " ".join(rng.choice(vocab) for _ in range(10 + i))
        session.push_turn(
            Turn(
                role="human" if i % 2 == 0 else "assistant",
                content=content,
                token_count=30 + 2 * i,
            )
        )
    return session


def test_result_is_frozen_dataclass() -> None:
    session = _growing_session(MIN_TURNS + 6)
    result = run_anti_tautology(session, seed=7)
    assert isinstance(result, AntiTautologyResult)


def test_passed_only_if_all_flags_false() -> None:
    session = _growing_session(MIN_TURNS + 6)
    result = run_anti_tautology(session, seed=7)
    if result.passed:
        assert not result.tautology_flag
        assert not result.instability_flag
        assert not result.outlier_flag
        assert not result.surrogate_flag
        assert not math.isnan(result.gamma_original)


def test_piecewise_delta_is_numeric_or_nan() -> None:
    session = _growing_session(MIN_TURNS * 2 + 2)
    result = run_anti_tautology(session, seed=7)
    assert isinstance(result.piecewise_delta, float)


def test_loto_max_sensitivity_nonnegative() -> None:
    session = _growing_session(MIN_TURNS + 4)
    result = run_anti_tautology(session, seed=7)
    assert math.isnan(result.max_loto_sensitivity) or result.max_loto_sensitivity >= 0.0


def test_shuffled_delta_nonnegative_or_nan() -> None:
    session = _growing_session(MIN_TURNS + 4)
    result = run_anti_tautology(session, seed=7)
    assert math.isnan(result.shuffled_delta) or result.shuffled_delta >= 0.0


def test_at_battery_runs_on_flat_vocab_session() -> None:
    """AT battery must execute (not crash) even on degenerate sessions."""
    session = _flat_vocab_session(MIN_TURNS + 4)
    result = run_anti_tautology(session, seed=7)
    # Cannot assert specific flag values here (adaptive gamma gates may
    # return NaN for flat-vocab sessions), but the result dataclass must
    # still be well-formed.
    assert isinstance(result.passed, bool)
    assert isinstance(result.notes, tuple)


def test_battery_rejects_short_sessions() -> None:
    import pytest

    session = _growing_session(MIN_TURNS - 1)
    with pytest.raises(ValueError):
        run_anti_tautology(session, seed=7)
