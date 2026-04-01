#!/usr/bin/env python3
"""Run worked example semantic checks including repeat-run consistency."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run_once(input_path: Path, output_path: Path, runner: Path, expected_tasks: int) -> dict:
    proc = subprocess.run(
        ["python", str(runner), str(input_path), "--output", str(output_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert output_path.exists(), output_path
    doc = json.loads(output_path.read_text(encoding="utf-8"))
    final = doc["final_classification"]
    assert final["status"] in {"PASS", "FAIL"}, final
    assert 0.0 <= float(final["composite_score"]) <= 5.0, final
    gates = [g["gate_id"] for g in doc["gate_results"]]
    assert gates == ["G0_INTEGRITY", "G1_MINIMUM_READINESS", "G2_EVIDENCE_SUFFICIENCY"], gates
    assert len(doc.get("task_scores", [])) == expected_tasks, "task cardinality drift"
    return doc


def stable_signature(doc: dict) -> dict:
    final = doc["final_classification"]
    gates = {g["gate_id"]: g["status"] for g in doc["gate_results"]}
    task_scores = sorted((t["task_id"], float(t["final_score"])) for t in doc["task_scores"])
    return {
        "final_status": final["status"],
        "composite": float(final["composite_score"]),
        "gates": gates,
        "task_scores": task_scores,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json")
    parser.add_argument("--runner", default="tools/reference_runner.py")
    parser.add_argument("--out-dir", default=".ci-artifacts")
    args = parser.parse_args()

    input_path = Path(args.input)
    runner = Path(args.runner)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    expected_tasks = len(json.loads(input_path.read_text(encoding="utf-8")).get("tasks", []))
    doc1 = run_once(input_path, out_dir / "worked-example.output.run1.json", runner, expected_tasks)
    doc2 = run_once(input_path, out_dir / "worked-example.output.run2.json", runner, expected_tasks)

    sig1 = stable_signature(doc1)
    sig2 = stable_signature(doc2)
    assert sig1 == sig2, (sig1, sig2)

    (out_dir / "worked-example.output.json").write_text(json.dumps(doc1, indent=2, ensure_ascii=False), encoding="utf-8")
    print("WORKED_EXAMPLE_SEMANTICS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
