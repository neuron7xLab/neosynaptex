"""Check openapi contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "evidence" / "wave_4"
CURRENT = OUT / "openapi.v2.json"
BASELINE = ROOT / "docs" / "contracts" / "openapi.v2.json"
REPORT = OUT / "openapi_contract_report.json"
REQUIRED_PATHS = [
    "/v1/simulate",
    "/v1/detect",
    "/v1/forecast",
    "/v1/compare",
    "/v1/report",
]


def _resolve_ref(schema: dict[str, Any], ref: str) -> Any:
    node: Any = schema
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def _contains_neuromodulation(node: object, schema: dict[str, Any]) -> bool:
    if isinstance(node, dict):
        if "$ref" in node:
            return _contains_neuromodulation(_resolve_ref(schema, str(node["$ref"])), schema)
        return any(
            k == "neuromodulation" or _contains_neuromodulation(v, schema) for k, v in node.items()
        )
    if isinstance(node, list):
        return any(_contains_neuromodulation(v, schema) for v in node)
    return False


def main() -> int:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    current_paths = set(current.get("paths", {}))
    baseline_paths = set(baseline.get("paths", {}))
    removed = sorted(baseline_paths - current_paths)
    added = sorted(current_paths - baseline_paths)
    path_failures = [path for path in REQUIRED_PATHS if path not in current_paths]
    neuromod_failures = [
        path
        for path in REQUIRED_PATHS
        if path in current.get("paths", {})
        and not _contains_neuromodulation(current["paths"][path], current)
    ]
    payload = {
        "ok": not removed and not path_failures and not neuromod_failures,
        "removed_paths": removed,
        "added_paths": added,
        "missing_required_paths": path_failures,
        "neuromodulation_coverage_failures": neuromod_failures,
        "current_version": current.get("info", {}).get("version"),
        "baseline_version": baseline.get("info", {}).get("version"),
        "contract_version": "openapi-v2",
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(REPORT)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
