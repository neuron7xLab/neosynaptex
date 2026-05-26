#!/usr/bin/env python3
"""Operational divergence/convergence compiler for machine-thinking reports.

Divergence: expand unresolved checklist signal into granular execution tasks.
Convergence: compress the expanded plan into a minimal prioritized action vector.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from substrates.bn_syn.scripts.mt_contract import SECTION_WEIGHTS

REQUIRED_REPORT_KEYS = {
    "verdict",
    "capital_index",
    "unresolved_by_section",
    "action_plan",
}


def _validate_report_contract(report: dict[str, Any]) -> None:
    missing = sorted(k for k in REQUIRED_REPORT_KEYS if k not in report)
    if missing:
        raise SystemExit(f"report-json missing required keys: {missing}")
    if not isinstance(report.get("unresolved_by_section"), dict):
        raise SystemExit("report-json key 'unresolved_by_section' must be object")
    if not isinstance(report.get("action_plan"), dict):
        raise SystemExit("report-json key 'action_plan' must be object")


def _diverge(report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    unresolved = report.get("unresolved_by_section", {}) or {}
    action_plan = report.get("action_plan", {}) or {}
    for section, count in unresolved.items():
        priority = round(SECTION_WEIGHTS.get(section, 1.0) * float(count), 3)
        actions = action_plan.get(section, [])
        if not actions:
            actions = [f"Resolve unresolved items in {section}"]
        for idx, action in enumerate(actions, start=1):
            tasks.append(
                {
                    "task_id": f"{section}-{idx}",
                    "section": section,
                    "priority": priority,
                    "unresolved_items": count,
                    "action": action,
                }
            )
    tasks.sort(key=lambda t: (-t["priority"], t["section"], t["task_id"]))
    return tasks


def _counterfactual_tests(tasks: list[dict[str, Any]], top_k: int) -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    for t in tasks[:top_k]:
        tests.append({
            "section": str(t["section"]),
            "hypothesis": f"If action is skipped in {t['section']}, quality degrades.",
            "falsifier": f"Execute without: {t['action']} and compare capital_index delta.",
        })
    return tests


def _converge(tasks: list[dict[str, Any]], top_k: int) -> dict[str, Any]:
    head = tasks[:top_k]
    status = "NO_ACTION_REQUIRED" if not head else "ACTION_REQUIRED"
    return {
        "status": status,
        "top_vector": [t["action"] for t in head],
        "sections": sorted({t["section"] for t in head}),
        "task_count": len(head),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    report = json.loads(args.report_json.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise SystemExit("report-json must contain a JSON object")
    _validate_report_contract(report)
    tasks = _diverge(report)
    converged = _converge(tasks, top_k=max(1, args.top_k))
    counterfactual_tests = _counterfactual_tests(tasks, top_k=max(1, args.top_k)) if tasks else []

    artifact = {
        "artifact_schema_version": "mt-operational-artifact/v1",
        "compiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_verdict": report.get("verdict"),
        "capital_index": report.get("capital_index"),
        "contract": {"required_keys": sorted(REQUIRED_REPORT_KEYS)},
        "divergence": tasks,
        "convergence": converged,
        "counterfactual_tests": counterfactual_tests,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out_json), "tasks": len(tasks), "top_k": converged["task_count"], "status": converged["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
