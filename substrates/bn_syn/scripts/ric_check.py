from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


EXPECTED_DOCS = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/REPRODUCIBILITY.md",
    "docs/RUNBOOK.md",
    "docs/SSOT.md",
]
EXPECTED_WORKFLOWS = [
    ".github/workflows/ci-pr-atomic.yml",
    ".github/workflows/perfection-gate.yml",
    ".github/workflows/launch-gate.yml",
    ".github/workflows/release-pipeline.yml",
]
EXPECTED_PATHS = [
    "Makefile",
    "pyproject.toml",
    "src/bnsyn",
    "scripts/launch_gate.py",
    "scripts/perfection_gate.py",
]


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def build_truth_map() -> dict[str, Any]:
    return {
        "command_truth": {
            "make_targets": ["install", "lint", "mypy", "test", "build", "docs", "security", "perfection-gate", "launch-gate"],
            "cli_entrypoint": "bnsyn",
        },
        "policy_truth": {
            "docs": EXPECTED_DOCS,
            "workflows": EXPECTED_WORKFLOWS,
        },
        "code_truth": {
            "package_root": "src/bnsyn",
            "main": "src/bnsyn/__main__.py",
            "cli": "src/bnsyn/cli.py",
            "schema": "src/bnsyn/schemas/experiment.py",
        },
    }


def collect_contradictions() -> list[dict[str, str]]:
    contradictions: list[dict[str, str]] = []
    for rel in EXPECTED_DOCS + EXPECTED_WORKFLOWS + EXPECTED_PATHS:
        if not _exists(rel):
            contradictions.append({"id": f"missing:{rel}", "evidence": f"file:{rel}:L1-L1"})
    return sorted(contradictions, key=lambda item: item["id"])


def write_report(path: Path, contradictions: list[dict[str, str]]) -> None:
    lines = ["# RIC_REPORT", "", f"contradictions={len(contradictions)}", ""]
    if contradictions:
        lines.extend(f"- {item['id']} [{item['evidence']}]" for item in contradictions)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run recursive integrity check and emit truth map/report")
    parser.add_argument("--truth-map", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    truth_map_path = Path(args.truth_map)
    report_path = Path(args.report)
    truth_map_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    truth_map = build_truth_map()
    contradictions = collect_contradictions()

    truth_map_path.write_text(json.dumps(truth_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, contradictions)
    return 0 if not contradictions else 1


if __name__ == "__main__":
    raise SystemExit(main())
