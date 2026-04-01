#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path, default: object) -> object:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--oh", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reports = Path(args.reports)
    gate = _load(
        reports / "gate-decisions.after.json",
        _load(reports / "gate-decisions.json", {"owned_gates": []}),
    )
    score = _load(
        reports / "scorecard.after.json",
        _load(reports / "scorecard.json", {"score": 0, "min_score": 92, "dimensions": [], "hard_blockers": []}),
    )
    interp = _load(reports / "interpretation.json", {"status": "FAIL", "items": [], "contradictions": [], "alternatives": []})
    delta = _load(
        reports / "delta.json",
        {
            "baseline_sha": "na",
            "after_sha": "na",
            "score_delta": 0,
            "dimension_deltas": {},
            "metric_deltas": {},
            "measurement_contract_equal": False,
        },
    )

    output = {
        "header": {
            "name": "Codex Interpreted Mechanized Quality Agent",
            "version": "2026.3.0",
            "mode": "strict",
            "work_id": "manual",
            "utc": "",
            "repo": "",
            "base_branch": "",
            "git_sha_before": "",
            "git_sha_after": "",
        },
        "inputs": {"missing_required": [], "assumptions": [], "constraints": []},
        "scope": {"allowlist": [], "exclusions": [], "budgets": {}},
        "modalities": {
            "present": interp.get("modalities_present", []),
            "missing": [],
            "instrumentation_required": interp.get("instrumentation_required", []),
        },
        "interpretation": {
            "status": interp.get("status", "FAIL"),
            "items": interp.get("items", []),
            "contradictions": interp.get("contradictions", []),
            "alternatives": interp.get("alternatives", []),
            "trace_path": "REPORTS/trace.jsonl",
        },
        "scorecard": score,
        "delta": delta,
        "gate_decisions": gate,
        "pr": {"pr_url": "", "pr_number": "", "head_branch": "", "head_sha": "", "state": ""},
        "ci": {"run_urls": [], "checks_summary": {}},
        "actions": {
            "act_performed": False,
            "diff_summary": {},
            "commit_list": [],
            "deficits_closed": [],
            "ordered_plan": [],
        },
        "evidence": {
            "evidence_root": "",
            "manifest_path": "",
            "reports_index": "REPORTS",
            "artifacts_sha256_count": 0,
            "redaction_policy_path": "scpe/codex-interpreted-mechanized-quality-agent/SECURITY.redaction.yml",
        },
        "rollback": {"revert_strategy": "git revert", "revert_command_or_steps": "git revert <sha>"},
        "next_steps": {"blocking_items": [], "instrumentation_plan": [], "handoff": ""},
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
