#!/usr/bin/env python3
"""Run fail-closed semantic mutation and assert strict output behavior."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json")
    parser.add_argument("--runner", default="tools/reference_runner.py")
    parser.add_argument("--verifier", default="tools/verify_execution_chain.py")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    src = Path(args.input)
    payload = json.loads(src.read_text(encoding="utf-8"))
    for task in payload["tasks"]:
        task["evidence_artifact_ids"] = []

    tmp_dir = Path(tempfile.gettempdir())
    tmp_in = tmp_dir / "SE_WORKED_EXAMPLE_INPUT.no_evidence.semantic.json"
    tmp_out = Path(args.output) if args.output else tmp_dir / "SE_WORKED_EXAMPLE_OUTPUT.no_evidence.semantic.json"
    tmp_in.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    proc = subprocess.run(
        ["python", args.runner, str(tmp_in), "--allow-non-authoritative-git", "--output", str(tmp_out)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, ((proc.stdout or ""), (proc.stderr or ""))
    assert tmp_out.exists(), tmp_out

    verify = subprocess.run(
        ["python", args.verifier, "--input", str(tmp_in), "--result", str(tmp_out), "--allow-non-authoritative-git"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, ((verify.stdout or ""), (verify.stderr or ""))

    out = json.loads(tmp_out.read_text(encoding="utf-8"))
    final = out["final_classification"]
    assert final["status"] == "FAIL", final
    assert float(final["composite_score"]) == 0.0, final

    gates = {g["gate_id"]: g["status"] for g in out["gate_results"]}
    assert gates["G0_INTEGRITY"] == "PASS", gates
    assert gates["G2_EVIDENCE_SUFFICIENCY"] == "FAIL", gates

    for task in out["task_scores"]:
        assert float(task["final_score"]) == 0.0, task
        assert (
            "NO_ADMISSIBLE_EVIDENCE" in task.get("reason_codes", [])
            or "NO_ADMISSIBLE_EVIDENCE" in task.get("penalties_applied", [])
        ), task

    print("FAIL_CLOSED_SEMANTIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
