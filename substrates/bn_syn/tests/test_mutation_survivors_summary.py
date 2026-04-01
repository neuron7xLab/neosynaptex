"""Contract tests for mutation survivor reporting helpers."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_mutation_survivors_summary_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.mutation_survivors_summary as survivors_summary

    summary_path = tmp_path / "summary.md"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    assert survivors_summary.main() == 0
    content = summary_path.read_text(encoding="utf-8")
    assert "## Surviving Mutants" in content
    assert "No surviving mutants!" in content


def test_mutation_survivors_summary_with_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.mutation_survivors_summary as survivors_summary

    summary_path = tmp_path / "summary.md"
    survivors_path = tmp_path / "survived_mutants.txt"
    survivors_path.write_text("".join([f"m{i}\n" for i in range(60)]), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))

    assert survivors_summary.main() == 0
    content = summary_path.read_text(encoding="utf-8")
    assert "m0" in content
    assert "m49" in content
    assert "m50" not in content
