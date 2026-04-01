#!/usr/bin/env python3
import argparse
import json
import os
import sys

import yaml

def jload(p):
    return json.load(open(p, "r", encoding="utf-8"))

def get_metric(metrics_json, key):
    if key in metrics_json:
        return metrics_json[key]
    return None

def eval_pass(expr, ctx):
    expr = expr.strip()
    if expr == "==0":
        return ctx["value"] == 0
    if expr == "==false":
        return ctx["value"] is False
    raise SystemExit(f"unsupported pass expr: {expr}")

def eval_hard_blocker(expr, observed):
    if "==" not in expr:
        raise SystemExit(f"unsupported hard blocker expr: {expr}")
    key, raw_expected = expr.split("==", 1)
    key = key.strip()
    expected_token = raw_expected.strip().lower()
    if expected_token == "false":
        expected = False
    elif expected_token == "true":
        expected = True
    else:
        try:
            expected = int(expected_token)
        except ValueError as exc:
            raise SystemExit(f"unsupported hard blocker value: {raw_expected}") from exc
    if key not in observed:
        return False
    return observed[key] == expected

ap = argparse.ArgumentParser()
ap.add_argument("qm")
ap.add_argument("--out", required=True)
args = ap.parse_args()

qm = yaml.safe_load(open(args.qm, "r", encoding="utf-8"))
thresholds = qm.get("thresholds", {})
dims_out = []
hard_blockers = []
score_num = 0.0
score_den = 0.0
observed_metrics = {}

for dim in qm["quality_dimensions"]:
    w = float(dim["weight"])
    dim_pass = True
    dim_metrics = []
    for m in dim["metrics"]:
        src = m["source"]
        data = jload(src)
        val = get_metric(data, m["key"])
        if val is None:
            raise SystemExit(f"missing metric {m['key']} in {src}")
        observed_metrics[m["key"]] = val
        thr = None
        passed = None
        if "pass" in m:
            passed = eval_pass(m["pass"], {"value": val})
        else:
            thr = thresholds[m["threshold_key"]]
            passed = val <= thr
        dim_metrics.append({"key": m["key"], "value": val, "threshold": thr, "passed": passed, "source": src})
        if not passed:
            dim_pass = False
    dims_out.append({"id": dim["id"], "weight": w, "passed": dim_pass, "metrics": dim_metrics})
    score_den += w
    score_num += w * (1.0 if dim_pass else 0.0)

min_score = qm["score"]["pass_requirement"]["min_score"]
score = int(round(100.0 * (score_num / score_den))) if score_den > 0 else 0

hb_refs = qm["score"]["pass_requirement"]["hard_blockers"]
hb_map = {h.get("id"): h.get("expr") for h in qm.get("hard_blockers", [])}
for ref in hb_refs:
    expr = hb_map.get(ref, ref)
    hard_blockers.append({"id": ref, "expr": expr, "passed": eval_hard_blocker(expr, observed_metrics)})

out = {
  "score": score,
  "min_score": min_score,
  "dimensions": dims_out,
  "hard_blockers": hard_blockers
}
os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2, sort_keys=True)
print(score)
sys.exit(0)
