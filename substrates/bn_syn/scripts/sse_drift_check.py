from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/sse_sdo/04_ci")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    workflow = ROOT / ".github" / "workflows" / "sse-sdo-fhe-gate.yml"
    required_checks = ["python scripts/sse_gate_runner.py", "python scripts/sse_proof_index.py", "artifacts/sse_sdo/**"]
    content = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    missing = [item for item in required_checks if item not in content]

    (out / "REQUIRED_CHECKS_MANIFEST.json").write_text(
        json.dumps({"required_checks": ["sse-sdo-fhe-gate"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "WORKFLOW_GRAPH.json").write_text(
        json.dumps({"workflows": [workflow.name] if workflow.exists() else []}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "DRIFT_REPORT.json").write_text(
        json.dumps({"status": "ok" if not missing else "drift_detected", "drift": missing}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("OK" if not missing else "DRIFT")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
