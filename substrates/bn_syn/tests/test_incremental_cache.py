"""Tests for incremental caching utilities."""

from __future__ import annotations

from pathlib import Path

from bnsyn.incremental import cached, clear_cache, compute_file_hash


def test_compute_file_hash_changes(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    assert compute_file_hash(target) == ""

    target.write_text("one")
    first = compute_file_hash(target)
    target.write_text("two")
    second = compute_file_hash(target)
    assert first != second


def test_cached_respects_dependency_hash(tmp_path: Path) -> None:
    clear_cache()
    target = tmp_path / "config.txt"
    target.write_text("alpha")
    calls: list[int] = []

    @cached(depends_on=target)
    def compute(value: int, _dep_hash: str | None = None) -> int:
        calls.append(value)
        return value * 2

    assert compute(3) == 6
    assert compute(3) == 6
    assert calls == [3]

    target.write_text("beta")
    assert compute(3) == 6
    assert calls == [3, 3]
