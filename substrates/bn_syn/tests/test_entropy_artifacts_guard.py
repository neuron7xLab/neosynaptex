from __future__ import annotations

from pathlib import Path

from entropy.guards.check_entropy_artifacts import run_guard


def test_entropy_artifacts_guard_passes() -> None:
    errors = run_guard(Path('.'))
    assert errors == []
