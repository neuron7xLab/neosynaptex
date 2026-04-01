#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

def load_json(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def overall_status(interpretation: dict) -> str:
    # deterministic: FAIL if any item FAIL; UNKNOWN if any item UNKNOWN; else PASS (not used for ERM gating)
    items = interpretation.get("items", []) or []
    st = [x.get("status") for x in items]
    if "FAIL" in st:
        return "FAIL"
    if "UNKNOWN" in st:
        return "UNKNOWN"
    return "PASS"

def deficit_severity(interpretation: dict) -> str:
    items = interpretation.get("items", []) or []
    if any(x.get("severity") == "S0" for x in items):
        return "S0"
    return "S1+"

def primary_category(interpretation: dict) -> str:
    items = interpretation.get("items", []) or []
    s0 = [x for x in items if x.get("severity") == "S0"]
    if s0:
        return s0[0].get("category", "none")
    if items:
        return items[0].get("category", "none")
    return "none"

def deadlock_key(gd: dict, it: dict) -> str:
    # stable key used for "same_deadlock_fingerprint"
    # (this is NOT the final DFP; it's the stable comparison input)
    owned = gd.get("owned_gates", gd.get("owned", gd))
    owned_fail = []
    if isinstance(owned, dict):
        for k, v in owned.items():
            if isinstance(v, dict) and v.get("status") == "FAIL":
                owned_fail.append(k)
    elif isinstance(owned, list):
        for x in owned:
            if x.get("status") == "FAIL":
                owned_fail.append(x.get("id"))
    items = it.get("items", []) or []
    missing_reports = []
    for x in items:
        if x.get("metric") == "missing_reports":
            v = x.get("value", [])
            if isinstance(v, list):
                missing_reports = sorted(v)
    key_obj = {
        "deficit_severity": deficit_severity(it),
        "category": primary_category(it),
        "owned_fail_gates": sorted([x for x in owned_fail if x]),
        "missing_reports": missing_reports
    }
    return json.dumps(key_obj, sort_keys=True, separators=(",",":"))

ap = argparse.ArgumentParser()
ap.add_argument("--gate-decisions", default="REPORTS/gate-decisions.json")
ap.add_argument("--interpretation", default="REPORTS/interpretation.json")
ap.add_argument("--out", default="REPORTS/meta-state.json")
ap.add_argument("--deadlock-out", default="REPORTS/deadlock.json")
ap.add_argument("--consecutive-fails-file", default="REPORTS/meta-state.json")  # previous run location
args = ap.parse_args()

root = Path(".").resolve()
gd = load_json(root / args.gate_decisions, default={})
it = load_json(root / args.interpretation, default={"items": []})

prev = load_json(root / args.consecutive_fails_file, default={}) or {}
prev_key = prev.get("deadlock_key", "")
prev_consecutive = int(prev.get("consecutive_fails", 0) or 0)
prev_overall = prev.get("overall_status", "UNKNOWN")

curr_key = deadlock_key(gd, it)
curr_overall = overall_status(it)

# consecutive_fails increments only when we remain in FAIL/UNKNOWN and the deadlock_key matches
same_key = (prev_key == curr_key) and (curr_key != "")
curr_bad = (curr_overall in ("FAIL","UNKNOWN"))
prev_bad = (prev_overall in ("FAIL","UNKNOWN"))

if same_key and curr_bad and prev_bad:
    consecutive = prev_consecutive + 1
elif curr_bad:
    consecutive = 1
else:
    consecutive = 0

meta = {
  "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "overall_status": curr_overall,
  "consecutive_fails": consecutive,
  "deficit_severity": deficit_severity(it),
  "category": primary_category(it),
  "deadlock_key": curr_key,
  "same_deadlock_fingerprint": bool(same_key),
  "erm_trigger_true": False
}

# ERM trigger predicate is computed here but still must be enforced by PA invariants.
if meta["consecutive_fails"] >= 3 and meta["deficit_severity"] == "S0" and meta["same_deadlock_fingerprint"]:
    meta["erm_trigger_true"] = True

os.makedirs((root / "REPORTS").as_posix(), exist_ok=True)
(Path(args.out)).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# Produce deadlock.json via deterministic DFP computation (delegated to deadlock_fingerprint.py)
# The caller of this script must pass the same consecutive value into deadlock_fingerprint.py for consistency.
rc, so, se = run([
    "python3","tools/deadlock_fingerprint.py",
    "--gate-decisions", args.gate_decisions,
    "--interpretation", args.interpretation,
    "--out", args.deadlock_out,
    "--consecutive-fails", str(meta["consecutive_fails"])
])
if rc != 0:
    raise SystemExit(rc)
print("ok")
