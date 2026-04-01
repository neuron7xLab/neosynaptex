from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from tools.manifest.generate import build_computed

ROOT = Path(__file__).resolve().parents[2]
SSOT_PATH = ROOT / "manifest/repo_manifest.yml"
SCHEMA_PATH = ROOT / "manifest/repo_manifest.schema.json"
COMPUTED_PATH = ROOT / "manifest/repo_manifest.computed.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_manifest() -> None:
    ssot = _load_yaml(SSOT_PATH)
    schema = _load_json(SCHEMA_PATH)
    Draft202012Validator(schema).validate(ssot)

    if not COMPUTED_PATH.exists():
        raise SystemExit("manifest/repo_manifest.computed.json missing; run generate first")

    computed = _load_json(COMPUTED_PATH)
    recomputed = build_computed()

    if computed != recomputed:
        raise SystemExit("Computed manifest drift detected; run python -m tools.manifest generate")

    gates_source = ROOT / ssot["required_pr_gates"]["source"]
    gates_hash = hashlib.sha256(gates_source.read_bytes()).hexdigest()
    if gates_hash != ssot["required_pr_gates"]["sha256"]:
        raise SystemExit("required_pr_gates.sha256 does not match current .github/PR_GATES.yml")

    for gate in _load_yaml(gates_source).get("required_pr_gates", []):
        workflow_file = ROOT / ".github/workflows" / gate["workflow_file"]
        if not workflow_file.exists():
            raise SystemExit(f"Missing required gate workflow: {workflow_file}")

    if (ROOT / "ci_manifest.json").exists():
        raise SystemExit("ci_manifest.json must be absent (dead control artifact)")
    if computed["metrics"]["ci_manifest_reference_count"] != 0:
        raise SystemExit("ci_manifest.json references detected in automation/docs")

    for generated_file in ssot["policies"]["generated_files"]:
        if not (ROOT / generated_file).exists():
            raise SystemExit(f"Generated file missing: {generated_file}")

    print("Manifest validation passed.")


if __name__ == "__main__":
    validate_manifest()
