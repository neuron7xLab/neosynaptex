from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


def _latest_snapshot() -> Path:
    evidence_root = _repo_root() / "artifacts" / "evidence"
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    dated_dirs = sorted(
        [p for p in evidence_root.iterdir() if p.is_dir() and date_pattern.match(p.name)],
        key=lambda path: datetime.strptime(path.name, "%Y-%m-%d"),
    )
    if not dated_dirs:
        msg = f"No dated evidence directories in {evidence_root}"
        raise AssertionError(msg)
    latest_date = dated_dirs[-1]
    sha_dirs = sorted([p for p in latest_date.iterdir() if p.is_dir()], key=lambda path: path.name)
    if not sha_dirs:
        msg = f"No SHA directories in {latest_date}"
        raise AssertionError(msg)
    return sha_dirs[-1]


def _run_verifier(snapshot: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/evidence/verify_evidence_snapshot.py",
            "--evidence-dir",
            str(snapshot),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_verifier_passes_on_committed_snapshot() -> None:
    snapshot = _latest_snapshot()
    result = _run_verifier(snapshot)
    assert result.returncode == 0, f"Verifier failed: {result.stderr}"


def test_verifier_fails_when_required_file_missing(tmp_path: Path) -> None:
    snapshot = _latest_snapshot()
    temp_snapshot = tmp_path / snapshot.name
    shutil.copytree(snapshot, temp_snapshot)
    (temp_snapshot / "manifest.json").unlink()

    result = _run_verifier(temp_snapshot)
    assert result.returncode != 0
    assert "manifest" in result.stderr.lower()
