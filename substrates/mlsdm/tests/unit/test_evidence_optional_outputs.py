from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


def _latest_snapshot(paths: set[Path]) -> Path:
    existing: list[tuple[float, Path]] = []
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        existing.append((stat.st_mtime, path))
    if not existing:
        raise AssertionError("No evidence snapshot produced")
    return max(existing)[1]


def _run_capture(evidence_dir: Path, inputs: dict[str, str]) -> Path:
    inputs_path = evidence_dir / "inputs.json"
    inputs_path.parent.mkdir(parents=True, exist_ok=True)
    inputs_path.write_text(json.dumps(inputs), encoding="utf-8")
    evidence_root = _repo_root() / "artifacts" / "evidence"

    def _snapshot_set(root: Path) -> set[Path]:
        # Snapshots live under artifacts/evidence/<date>/<short_sha>
        return set(root.glob("*/*")) if root.exists() else set()

    before = _snapshot_set(evidence_root)
    subprocess.check_call(
        [
            sys.executable,
            "scripts/evidence/capture_evidence.py",
            "--mode",
            "pack",
            "--inputs",
            str(inputs_path),
        ],
        cwd=_repo_root(),
    )
    after = _snapshot_set(evidence_root)
    new_snapshots = after - before
    candidates = new_snapshots if new_snapshots else after
    return _latest_snapshot(candidates)


def _run_verify(snapshot: Path) -> subprocess.CompletedProcess[str]:
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


def test_optional_outputs_verified_when_present(tmp_path: Path) -> None:
    evidence_root = tmp_path / "artifacts" / "evidence"
    snapshot = evidence_root / "2026-01-01" / "abc123"
    coverage = tmp_path / "coverage.xml"
    junit = tmp_path / "junit.xml"
    bench = tmp_path / "benchmark-metrics.json"
    latency = tmp_path / "raw_neuro_engine_latency.json"
    memory = tmp_path / "memory_footprint.json"
    iteration_metrics = tmp_path / "iteration-metrics.jsonl"

    coverage.write_text('<coverage line-rate="0.5"></coverage>', encoding="utf-8")
    junit.write_text('<testsuite name="t" tests="1" failures="0" errors="0" skipped="0"><testcase name="ok"/></testsuite>', encoding="utf-8")
    bench.write_text('{"metric": 1}', encoding="utf-8")
    latency.write_text('{"p50": 1}', encoding="utf-8")
    memory.write_text('{"rss": 1}', encoding="utf-8")
    iteration_metrics.write_text('{"delta": 0.1}\n', encoding="utf-8")

    produced = _run_capture(
        snapshot.parent,
        {
            "coverage_xml": str(coverage),
            "junit_xml": str(junit),
            "benchmark_metrics": str(bench),
            "raw_latency": str(latency),
            "memory_footprint": str(memory),
            "iteration_metrics": str(iteration_metrics),
        },
    )

    result = _run_verify(produced)
    assert result.returncode == 0, result.stderr


def test_required_only_still_passes(tmp_path: Path) -> None:
    evidence_root = tmp_path / "artifacts" / "evidence"
    snapshot = evidence_root / "2026-01-02" / "abc123"
    coverage = tmp_path / "coverage.xml"
    junit = tmp_path / "junit.xml"

    coverage.write_text('<coverage line-rate="0.5"></coverage>', encoding="utf-8")
    junit.write_text('<testsuite name="t" tests="1" failures="0" errors="0" skipped="0"><testcase name="ok"/></testsuite>', encoding="utf-8")

    produced = _run_capture(
        snapshot.parent,
        {
            "coverage_xml": str(coverage),
            "junit_xml": str(junit),
        },
    )

    result = _run_verify(produced)
    assert result.returncode == 0, result.stderr


def test_optional_output_outside_dir_fails(tmp_path: Path) -> None:
    evidence_root = tmp_path / "artifacts" / "evidence"
    snapshot = evidence_root / "2026-01-03" / "abc123"
    coverage = tmp_path / "coverage.xml"
    junit = tmp_path / "junit.xml"
    bad = tmp_path / "outside.json"

    coverage.write_text('<coverage line-rate="0.5"></coverage>', encoding="utf-8")
    junit.write_text('<testsuite name="t" tests="1" failures="0" errors="0" skipped="0"><testcase name="ok"/></testsuite>', encoding="utf-8")
    bad.write_text("{}", encoding="utf-8")

    manifest_inputs = {
        "coverage_xml": str(coverage),
        "junit_xml": str(junit),
        "benchmark_metrics": str(bad),
    }

    produced = _run_capture(snapshot.parent, manifest_inputs)

    # Move referenced file outside snapshot to simulate escape
    shutil.rmtree(produced / "benchmarks", ignore_errors=True)

    result = _run_verify(produced)
    assert result.returncode != 0
