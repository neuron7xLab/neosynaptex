from __future__ import annotations

from pathlib import Path

import pytest

import tools.verify_authorship_compiler as vac


def test_i1_rejects_disallowed_path() -> None:
    with pytest.raises(vac.InvariantError):
        vac._check_i1(["bad/file.txt"], ["core/"])


def test_i2_rejects_forbidden_pattern(tmp_path: Path) -> None:
    f = tmp_path / "a.md"
    f.write_text("seamless integration", encoding="utf-8")
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        with pytest.raises(vac.InvariantError):
            vac._check_i2(["a.md"], ["(?i)seamless integration"])
    finally:
        os.chdir(cwd)


def test_i6_fails_when_no_verified_edges(tmp_path: Path) -> None:
    f = tmp_path / "README.md"
    f.write_text("hello world", encoding="utf-8")
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        with pytest.raises(vac.InvariantError):
            vac._check_i6(["README.md"], min_verified_edges=1, max_public_tokens=100)
    finally:
        os.chdir(cwd)


def test_i7_passes_when_no_runtime_changes(tmp_path: Path) -> None:
    snap = tmp_path / ".repo" / "public_symbols.sha256"
    snap.parent.mkdir(parents=True)
    snap.write_text("x", encoding="utf-8")
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        vac._check_i7(["README.md"], ".repo/public_symbols.sha256", ["core/"], ["README.md"])
    finally:
        os.chdir(cwd)
