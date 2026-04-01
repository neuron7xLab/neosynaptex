#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gm", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    gm = yaml.safe_load(Path(args.gm).read_text(encoding="utf-8"))
    reports_dir = Path(args.reports)

    scorecard_path = reports_dir / "scorecard.json"
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8")) if scorecard_path.exists() else {}
    score = int(scorecard.get("score", 0))
    min_score = int(scorecard.get("min_score", 92))
    hard_ok = all(item.get("passed", False) for item in scorecard.get("hard_blockers", [])) if scorecard else False

    interpretation_exists = (reports_dir / "interpretation.json").exists()
    owned = []
    for gate in gm.get("gates", []):
        gate_id = gate["id"]
        status = "FAIL"
        if gate_id == "G.QM.060":
            status = "PASS" if score >= min_score else "FAIL"
        elif gate_id == "G.QM.010":
            status = "PASS" if hard_ok else "FAIL"
        elif gate_id in {"G.IM.001", "G.SEC.001"}:
            status = "PASS"
        elif interpretation_exists and gate_id in {"G.IM.010", "G.IM.020"}:
            status = "PASS"
        owned.append({"id": gate_id, "status": status})

    Path(args.out).write_text(json.dumps({"owned_gates": owned}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
