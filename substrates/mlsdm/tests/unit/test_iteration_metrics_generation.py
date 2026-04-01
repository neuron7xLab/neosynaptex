from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eval" / "generate_iteration_metrics.py"
MAX_JSONL_BYTES = 100_000  # ensures deterministic artifact stays well under evidence size guardrails


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


def _run_generator(out_path: Path, *, seed: int = 7, steps: int = 16) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    repo_root = _repo_root()
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}".rstrip(":")
    subprocess.check_call(
        [
            sys.executable,
            str(SCRIPT),
            "--seed",
            str(seed),
            "--steps",
            str(steps),
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        env=env,
    )
    return out_path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_finite(values: list[float]) -> None:
    for value in values:
        assert math.isfinite(value), f"non-finite value: {value}"


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first = _run_generator(tmp_path / "iter_a.jsonl", seed=11, steps=24)
    second = _run_generator(tmp_path / "iter_b.jsonl", seed=11, steps=24)

    assert first.read_bytes() == second.read_bytes()
    assert _hash(first) == _hash(second)


def test_jsonl_schema_and_bounds(tmp_path: Path) -> None:
    steps = 20
    out = _run_generator(tmp_path / "schema.jsonl", seed=5, steps=steps)
    records = _load_lines(out)

    assert len(records) == steps
    assert out.stat().st_size < MAX_JSONL_BYTES  # bounded artifact size

    required_keys = {
        "timestamp",
        "dt",
        "seed",
        "threat",
        "risk",
        "regime",
        "prediction_error",
        "action",
        "dynamics",
        "safety",
    }
    for rec in records:
        assert required_keys.issubset(rec.keys())
        _assert_finite([rec["timestamp"], rec["dt"], rec["seed"], rec["threat"], rec["risk"]])

        pe = rec["prediction_error"]
        assert {"delta", "abs_delta", "clipped_delta"}.issubset(pe.keys())
        _assert_finite([pe["abs_delta"], *pe["delta"], *pe["clipped_delta"]])
        assert isinstance(rec["action"], dict)
        assert isinstance(rec["dynamics"], dict)
        assert isinstance(rec["safety"], dict)


def test_capture_evidence_packs_iteration_metrics(tmp_path: Path) -> None:
    coverage = tmp_path / "coverage.xml"
    junit = tmp_path / "junit.xml"
    coverage.write_text('<coverage line-rate="0.5"></coverage>', encoding="utf-8")
    junit.write_text('<testsuite name="t" tests="1" failures="0" errors="0" skipped="0"><testcase name="ok"/></testsuite>', encoding="utf-8")

    metrics = _run_generator(tmp_path / "iteration-metrics.jsonl", seed=2, steps=8)
    inputs_path = tmp_path / "inputs.json"
    inputs_path.write_text(
        json.dumps(
            {
                "coverage_xml": str(coverage),
                "junit_xml": str(junit),
                "iteration_metrics": str(metrics),
            }
        ),
        encoding="utf-8",
    )

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
        env={
            **os.environ,
            "PYTHONPATH": f"{_repo_root() / 'src'}:{os.environ.get('PYTHONPATH', '')}".rstrip(":"),
        },
    )

    evidence_root = _repo_root() / "artifacts" / "evidence"
    snapshots = sorted(evidence_root.glob("*/*"))
    assert snapshots, "capture_evidence did not produce a snapshot"
    snapshot = snapshots[-1]
    packed = snapshot / "iteration" / "iteration-metrics.jsonl"
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))

    assert packed.exists()
    assert manifest["outputs"].get("iteration_metrics") == "iteration/iteration-metrics.jsonl"
