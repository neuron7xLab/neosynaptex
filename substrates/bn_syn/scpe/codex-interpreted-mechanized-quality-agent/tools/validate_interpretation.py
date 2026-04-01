#!/usr/bin/env python3
import json
import sys

REQ = ["status","items","instrumentation_required"]
ITEM_REQ = ["category","priority","metric","value","threshold","gate_ids","recommended_actions"]

p = sys.argv[1]
data = json.load(open(p, "r", encoding="utf-8"))
ok = True
errs = []

for k in REQ:
    if k not in data:
        ok = False
        errs.append(f"missing:{k}")

items = data.get("items", [])
if not isinstance(items, list):
    ok = False
    errs.append("items:not_list")
else:
    for i, it in enumerate(items):
        for k in ITEM_REQ:
            if k not in it:
                ok = False
                errs.append(f"items[{i}].missing:{k}")

out = {"schema_valid": ok, "errors": errs}
json.dump(out, open("REPORTS/interpretation.schema-check.json","w",encoding="utf-8"), indent=2, sort_keys=True)
print("ok" if ok else "fail")
sys.exit(0 if ok else 2)
