#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _load_metric(path: Path, key: str) -> int:
    return int(json.loads(path.read_text(encoding="utf-8"))[key])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--im", required=True)
    ap.add_argument("--qm", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trace", required=True)
    args = ap.parse_args()

    lint = _load_metric(Path("REPORTS/quality/lint.json"), "lint.error_count")
    tests = _load_metric(Path("REPORTS/quality/tests.json"), "tests.fail_count")
    sec = _load_metric(Path("REPORTS/quality/security.json"), "security.high_count")

    items: list[dict[str, object]] = []
    if tests > 0:
        items.append(
            {
                "status": "FAIL",
                "category": "tests",
                "severity": "S0",
                "metric": "tests.fail_count",
                "value": tests,
                "threshold": 0,
                "gate_ids": ["G.QM.010"],
                "recommended_actions": ["A.FIX.TESTS.MINIMAL"],
                "priority": 900,
            }
        )
    if sec > 0:
        items.append(
            {
                "status": "FAIL",
                "category": "security",
                "severity": "S0",
                "metric": "security.high_count",
                "value": sec,
                "threshold": 0,
                "gate_ids": ["G.QM.010"],
                "recommended_actions": ["A.FIX.SEC.MINIMAL"],
                "priority": 850,
            }
        )
    if lint > 0:
        items.append(
            {
                "status": "FAIL",
                "category": "lint",
                "severity": "S1",
                "metric": "lint.error_count",
                "value": lint,
                "threshold": 0,
                "gate_ids": ["G.QM.010"],
                "recommended_actions": ["A.FIX.LINT.MINIMAL"],
                "priority": 800,
            }
        )

    status = "PASS" if not items else "FAIL"
    interpretation = {
        "status": status,
        "items": items,
        "instrumentation_required": [],
        "modalities_present": ["M.CODE", "M.TEST", "M.SEC", "M.DOC", "M.PERF", "M.CI"],
        "contradictions": [],
        "alternatives": [],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(interpretation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    digest = hashlib.sha256(json.dumps(interpretation, sort_keys=True).encode("utf-8")).hexdigest()
    Path(args.trace).write_text(
        json.dumps(
            {
                "step": 1,
                "rule_id": "R.IM.EVAL",
                "decision": status,
                "facts_snapshot_sha256": digest,
                "outputs": [args.out],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
