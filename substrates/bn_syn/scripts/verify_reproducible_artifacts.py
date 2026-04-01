from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Sequence


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_command(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, shell=True, capture_output=True, text=True, check=False)


def verify_artifact(command: str, artifact_path: Path, runs: int) -> dict[str, object]:
    hashes: list[str] = []
    outputs: list[dict[str, object]] = []
    for _ in range(runs):
        proc = _run_command(command)
        outputs.append({"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode != 0:
            return {
                "artifact": str(artifact_path),
                "command": command,
                "status": "failed_command",
                "outputs": outputs,
                "hashes": hashes,
            }
        if not artifact_path.exists():
            return {
                "artifact": str(artifact_path),
                "command": command,
                "status": "missing_artifact",
                "outputs": outputs,
                "hashes": hashes,
            }
        hashes.append(_sha256(artifact_path))

    stable = len(set(hashes)) == 1
    return {
        "artifact": str(artifact_path),
        "command": command,
        "status": "pass" if stable else "non_deterministic",
        "hashes": hashes,
        "outputs": outputs,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify generated artifacts are reproducible")
    parser.add_argument("--spec", required=True, help="Path to JSON list of {artifact, command}")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--report", default="evidence/reproducibility/report.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    import sys
    args = parse_args(argv if argv is not None else sys.argv[1:])
    spec_path = Path(args.spec)
    specs = json.loads(spec_path.read_text(encoding="utf-8"))

    results = []
    for item in specs:
        artifact_path = Path(item["artifact"])
        command = str(item["command"])
        results.append(verify_artifact(command=command, artifact_path=artifact_path, runs=args.runs))

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failed = [result for result in results if result["status"] != "pass"]
    if failed:
        for result in failed:
            print(f"FAIL {result['artifact']}: {result['status']}")
        return 1
    print("PASS reproducibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
