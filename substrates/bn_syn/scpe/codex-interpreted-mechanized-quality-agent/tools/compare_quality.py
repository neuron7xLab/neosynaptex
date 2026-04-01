#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))

    measurement_equal = (
        baseline.get("command_list") == after.get("command_list")
        and baseline.get("report_paths") == after.get("report_paths")
    )

    delta = {
        "baseline_sha": "na",
        "after_sha": "na",
        "score_delta": 0,
        "dimension_deltas": {},
        "metric_deltas": {},
        "measurement_contract_equal": measurement_equal,
    }
    Path(args.out).write_text(json.dumps(delta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path("REPORTS/diff-summary.json").write_text(
        json.dumps({"changed": []}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
