from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.evidence.capture_evidence import SCHEMA_VERSION
from scripts.evidence.verify_evidence_snapshot import EvidenceError, verify_snapshot


def _hash_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(evidence_dir: Path, failures: list[str] | None = None, schema: str = SCHEMA_VERSION) -> None:
    manifest = {
        "schema_version": schema,
        "git_sha": "abcdef1234567890",
        "short_sha": "abcdef123456",
        "created_utc": "2025-01-01T00:00:00Z",
        "source_ref": "refs/heads/test",
        "commands": ["pytest --cov"],
        "outputs": {
            "coverage_xml": "coverage/coverage.xml",
            "junit_xml": "pytest/junit.xml",
            "coverage_log": "logs/coverage_gate.log",
        },
        "status": {
            "ok": not failures,
            "partial": bool(failures),
            "failures": failures or [],
        },
        "file_index": [],
    }
    files = [p for p in evidence_dir.rglob("*") if p.is_file() and p.name != "manifest.json"]
    for path in sorted(files):
        manifest["file_index"].append(
            {
                "path": str(path.relative_to(evidence_dir)),
                "sha256": _hash_file(path),
                "bytes": path.stat().st_size,
                "mime_guess": "text/xml" if path.suffix == ".xml" else "text/plain",
            }
        )
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _build_snapshot(tmp_path: Path, *, schema: str = SCHEMA_VERSION, failures: list[str] | None = None) -> Path:
    evidence_dir = tmp_path / "artifacts" / "evidence" / "2025-01-01" / "abcdef123456"
    (evidence_dir / "coverage").mkdir(parents=True, exist_ok=True)
    (evidence_dir / "pytest").mkdir(parents=True, exist_ok=True)
    (evidence_dir / "logs").mkdir(parents=True, exist_ok=True)
    (evidence_dir / "env").mkdir(parents=True, exist_ok=True)

    (evidence_dir / "coverage" / "coverage.xml").write_text(
        '<coverage line-rate="0.80" branch-rate="0.0"></coverage>', encoding="utf-8"
    )
    (evidence_dir / "pytest" / "junit.xml").write_text(
        '<testsuite name="unit" tests="2" failures="0" errors="0" skipped="0"></testsuite>',
        encoding="utf-8",
    )
    (evidence_dir / "logs" / "coverage_gate.log").write_text("ok", encoding="utf-8")
    (evidence_dir / "env" / "python_version.txt").write_text("3.11.0\n", encoding="utf-8")
    (evidence_dir / "env" / "uv_lock_sha256.txt").write_text("hash\n", encoding="utf-8")
    _write_manifest(evidence_dir, failures=failures, schema=schema)
    return evidence_dir


def test_verifier_rejects_unknown_schema_version(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path, schema="unknown-v0")
    with pytest.raises(EvidenceError):
        verify_snapshot(snapshot)


def test_verifier_rejects_missing_required_file(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path)
    (snapshot / "coverage" / "coverage.xml").unlink()
    with pytest.raises(EvidenceError):
        verify_snapshot(snapshot)


def test_verifier_rejects_path_traversal_in_manifest(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path)
    manifest_path = snapshot / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["outputs"]["coverage_xml"] = "../escape.xml"
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(EvidenceError):
        verify_snapshot(snapshot)


def test_verifier_rejects_secret_like_content(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path)
    (snapshot / "logs" / "unit_tests.log").write_text("Authorization: Bearer SECRET-TOKEN-ABC", encoding="utf-8")
    manifest_path = snapshot / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["file_index"].append(
        {
            "path": "logs/unit_tests.log",
            "sha256": _hash_file(snapshot / "logs" / "unit_tests.log"),
            "bytes": (snapshot / "logs" / "unit_tests.log").stat().st_size,
            "mime_guess": "text/plain",
        }
    )
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(EvidenceError):
        verify_snapshot(snapshot)


def test_verifier_rejects_total_size_overflow(tmp_path: Path) -> None:
    snapshot = _build_snapshot(tmp_path)
    big_file = snapshot / "logs" / "big.bin"
    big_file.write_bytes(b"0" * (6 * 1024 * 1024))
    manifest_path = snapshot / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["file_index"].append(
        {
            "path": "logs/big.bin",
            "sha256": _hash_file(big_file),
            "bytes": big_file.stat().st_size,
            "mime_guess": "application/octet-stream",
        }
    )
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(EvidenceError):
        verify_snapshot(snapshot)


def test_capture_pack_mode_creates_manifest_with_file_index(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    coverage_xml = tmp_path / "coverage.xml"
    junit_xml = tmp_path / "junit.xml"
    coverage_log = tmp_path / "coverage.log"
    coverage_xml.write_text('<coverage line-rate="0.90"></coverage>', encoding="utf-8")
    junit_xml.write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"></testsuite>', encoding="utf-8")
    coverage_log.write_text("ok", encoding="utf-8")
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(
        json.dumps(
            {
                "coverage_xml": str(coverage_xml),
                "coverage_log": str(coverage_log),
                "junit_xml": str(junit_xml),
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/evidence/capture_evidence.py",
            "--mode",
            "pack",
            "--inputs",
            str(inputs_file),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr

    evidence_root = repo_root / "artifacts" / "evidence"
    date_dirs = sorted([d for d in evidence_root.iterdir() if d.is_dir()])
    assert date_dirs
    latest_date = date_dirs[-1]
    sha_dirs = sorted([d for d in latest_date.iterdir() if d.is_dir()])
    assert sha_dirs
    snapshot_dir = sha_dirs[-1]

    try:
        manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["file_index"], "file_index should not be empty"
        verify_snapshot(snapshot_dir)
    finally:
        shutil.rmtree(snapshot_dir.parent, ignore_errors=True)
