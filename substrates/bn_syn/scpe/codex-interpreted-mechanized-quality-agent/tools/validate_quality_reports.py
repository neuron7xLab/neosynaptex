#!/usr/bin/env python3
import json
import os
import sys

import yaml

qm = yaml.safe_load(open(sys.argv[1], "r", encoding="utf-8"))
missing = []
for dim in qm["quality_dimensions"]:
    for m in dim["metrics"]:
        src = m["source"]
        if not os.path.exists(src):
            missing.append(src)

out = {"missing_reports": sorted(set(missing)), "ok": len(missing) == 0}
os.makedirs("REPORTS", exist_ok=True)
json.dump(out, open("REPORTS/quality-reports.check.json","w",encoding="utf-8"), indent=2, sort_keys=True)
print("ok" if out["ok"] else "fail")
sys.exit(0 if out["ok"] else 2)
