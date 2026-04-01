from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / ".github" / "sse_sdo_fhe.yml"

SCHEMA: dict[str, Any] = {
    "protocol": str,
    "toolchain": {"python": str, "pip": str},
    "determinism": {
        "stable_ordering_required": bool,
        "seed_required": bool,
        "nondeterminism_whitelist": list,
    },
    "evidence": {"required_ratio_P0": (int, float)},
    "policy": {"law_without_police_forbidden": bool},
    "ci": {
        "required_checks_contract": bool,
        "pinned_actions": bool,
        "least_privilege": bool,
    },
    "tests": {"required_suites": list},
    "perf": {"baseline_required": bool, "regression_threshold_pct": (int, float)},
    "flags": {"required_for": list},
}


def _validate_strict(payload: Any, schema: Any, path: str = "root") -> None:
    if isinstance(schema, dict):
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected object")
        extra = set(payload) - set(schema)
        missing = set(schema) - set(payload)
        if extra:
            raise ValueError(f"{path}: unknown keys {sorted(extra)}")
        if missing:
            raise ValueError(f"{path}: missing keys {sorted(missing)}")
        for key, sub in schema.items():
            _validate_strict(payload[key], sub, f"{path}.{key}")
        return
    if isinstance(schema, tuple):
        if not isinstance(payload, schema):
            raise ValueError(f"{path}: expected {schema}, got {type(payload)}")
        return
    if not isinstance(payload, schema):
        raise ValueError(f"{path}: expected {schema}, got {type(payload)}")


def load_and_validate(path: Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    _validate_strict(payload, SCHEMA)
    if payload["protocol"] != "SSE-SDO-FHE-2026.06":
        raise ValueError("root.protocol: unexpected value")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", nargs="?", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    payload = load_and_validate(Path(args.policy))
    print(json.dumps(payload, indent=2, sort_keys=True) if args.as_json else "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
