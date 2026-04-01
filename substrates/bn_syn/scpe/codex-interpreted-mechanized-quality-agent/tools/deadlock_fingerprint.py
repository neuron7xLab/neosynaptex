#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def deficit_severity(interpretation: dict) -> str:
    items = interpretation.get("items", []) or []
    if any(item.get("severity") == "S0" for item in items):
        return "S0"
    return "S1+"


def primary_category(interpretation: dict) -> str:
    items = interpretation.get("items", []) or []
    s0_items = [item for item in items if item.get("severity") == "S0"]
    if s0_items:
        return s0_items[0].get("category", "none")
    if items:
        return items[0].get("category", "none")
    return "none"


def owned_fail_gates(gate_decisions: dict) -> list[str]:
    owned = gate_decisions.get("owned_gates", gate_decisions.get("owned", gate_decisions))
    fails: list[str] = []
    if isinstance(owned, dict):
        for gate_id, gate_payload in owned.items():
            if isinstance(gate_payload, dict) and gate_payload.get("status") in ("FAIL", "UNKNOWN"):
                fails.append(gate_id)
    elif isinstance(owned, list):
        for item in owned:
            if item.get("status") in ("FAIL", "UNKNOWN") and item.get("id"):
                fails.append(item["id"])
    return sorted(set(fails))


def missing_reports(interpretation: dict) -> list[str]:
    items = interpretation.get("items", []) or []
    for item in items:
        if item.get("metric") == "missing_reports":
            value = item.get("value", [])
            if isinstance(value, list):
                return sorted(str(x) for x in value)
    return []


def compute_dfp(payload: dict) -> str:
    if payload["missing_reports_count"] > 0 and payload["deficit_severity"] == "S0":
        return "DFP:missing_reports"
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"DFP:{digest}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-decisions", default="REPORTS/gate-decisions.json")
    ap.add_argument("--interpretation", default="REPORTS/interpretation.json")
    ap.add_argument("--out", default="REPORTS/deadlock.json")
    ap.add_argument("--consecutive-fails", default="0")
    args = ap.parse_args()

    root = Path(".").resolve()
    gd = load_json(root / args.gate_decisions, default={})
    it = load_json(root / args.interpretation, default={"items": []})

    m_reports = missing_reports(it)
    normalized = {
        "deficit_severity": deficit_severity(it),
        "primary_category": primary_category(it),
        "owned_fail_gates": owned_fail_gates(gd),
        "missing_reports": m_reports,
        "missing_reports_count": len(m_reports),
        "consecutive_fails": int(args.consecutive_fails),
    }
    dfp = compute_dfp(normalized)
    result = {
        "deadlock_fingerprint": dfp,
        "normalized": normalized,
    }

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(dfp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
