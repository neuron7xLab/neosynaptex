from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import scripts.evidence.capture_evidence as capture_evidence


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


def _file_index_entry(evidence_dir: Path, rel_path: Path) -> dict[str, object]:
    data = (evidence_dir / rel_path).read_bytes()
    mime, _ = mimetypes.guess_type(str(rel_path))
    return {
        "path": str(rel_path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mime_guess": mime or "application/octet-stream",
    }


def test_makefile_evidence_target_passes_mode_build() -> None:
    makefile = (_repo_root() / "Makefile").read_text(encoding="utf-8")
    assert "scripts/evidence/capture_evidence.py --mode build" in makefile


def test_capture_evidence_default_mode_build(monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = str(_repo_root() / "scripts" / "evidence" / "capture_evidence.py")
    monkeypatch.setattr(sys, "argv", [script_path])
    args = capture_evidence.parse_args()
    assert args.mode == "build"


def test_verify_snapshot_smoke(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "artifacts" / "evidence" / "2026-01-01" / "deadbeef"
    coverage_dir = evidence_dir / "coverage"
    pytest_dir = evidence_dir / "pytest"
    coverage_dir.mkdir(parents=True)
    pytest_dir.mkdir(parents=True)

    coverage_xml = coverage_dir / "coverage.xml"
    coverage_xml.write_text('<coverage line-rate="0.80"></coverage>\n', encoding="utf-8")

    junit_xml = pytest_dir / "junit.xml"
    junit_xml.write_text(
        '<testsuite name="suite" tests="1" failures="0" errors="0" skipped="0">'
        "<testcase name=\"test_example\"/>"
        "</testsuite>\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "evidence-v1",
        "git_sha": "deadbeef00000000000000000000000000000000",
        "short_sha": "deadbeef",
        "created_utc": "2026-01-01T00:00:00Z",
        "source_ref": "refs/heads/test",
        "commands": [],
        "outputs": {"coverage_xml": "coverage/coverage.xml", "junit_xml": "pytest/junit.xml"},
        "status": {"ok": True, "partial": False, "failures": []},
        "file_index": [
            _file_index_entry(evidence_dir, Path("coverage/coverage.xml")),
            _file_index_entry(evidence_dir, Path("pytest/junit.xml")),
        ],
    }
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/evidence/verify_evidence_snapshot.py",
            "--evidence-dir",
            str(evidence_dir),
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Verifier failed: {result.stderr}\nSTDOUT:\n{result.stdout}"
