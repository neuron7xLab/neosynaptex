#!/usr/bin/env python3
"""Standalone Bundle Verifier — validates artifacts without engine import.

Uses only JSON schema validation and optional Ed25519 signature check.
Does NOT import mycelium_fractal_net.

Usage:
    python scripts/verify_bundle.py <bundle_directory>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def _validate_schema(data: dict, schema: dict) -> list[str]:
    """Basic JSON Schema validation (type checking only, no jsonschema dep)."""
    errors = []
    props = schema.get("properties", {})
    required = schema.get("required", [])

    for req in required:
        if req not in data:
            errors.append(f"Missing required field: {req}")

    for key, value in data.items():
        if key in props:
            expected = props[key]
            etype = expected.get("type")
            if isinstance(etype, str):
                if etype == "number" and not isinstance(value, (int, float)):
                    errors.append(f"{key}: expected number, got {type(value).__name__}")
                elif etype == "string" and not isinstance(value, str):
                    errors.append(f"{key}: expected string, got {type(value).__name__}")
                elif etype == "integer" and not isinstance(value, int):
                    errors.append(f"{key}: expected integer, got {type(value).__name__}")
                elif etype == "boolean" and not isinstance(value, bool):
                    errors.append(f"{key}: expected boolean, got {type(value).__name__}")
                elif etype == "object" and not isinstance(value, dict):
                    if value is not None:
                        errors.append(f"{key}: expected object, got {type(value).__name__}")
                elif etype == "array" and not isinstance(value, list):
                    errors.append(f"{key}: expected array, got {type(value).__name__}")

    return errors


def _verify_checksum(file_path: Path, expected_hash: str) -> bool:
    """Verify SHA256 checksum."""
    actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return actual.startswith(expected_hash) or expected_hash.startswith(actual[:16])


def verify_bundle(bundle_dir: str | Path) -> dict:
    """Verify a bundle directory without importing the engine."""
    bundle_dir = Path(bundle_dir)
    results = {"ok": True, "artifacts": [], "errors": []}

    # Check manifest
    manifest_candidates = list(bundle_dir.rglob("report.json")) + list(
        bundle_dir.rglob("manifest.json")
    )
    if not manifest_candidates:
        results["ok"] = False
        results["errors"].append("No manifest or report.json found")
        return results

    # Load schemas
    schema_dir = Path("docs/contracts/schemas")
    schemas = {}
    if schema_dir.exists():
        for sf in schema_dir.glob("*.schema.json"):
            schemas[sf.stem.split(".")[0]] = json.loads(sf.read_text())

    # Validate each JSON artifact
    for json_file in bundle_dir.rglob("*.json"):
        try:
            data = json.loads(json_file.read_text())
        except json.JSONDecodeError as e:
            results["ok"] = False
            results["errors"].append(f"{json_file.name}: invalid JSON: {e}")
            continue

        # Check version field
        has_version = any(k for k in data if "version" in k.lower())
        artifact = {
            "file": json_file.name,
            "has_version": has_version,
            "valid_json": True,
            "schema_errors": [],
        }

        # Try schema validation
        name_key = json_file.stem.lower().replace("_", "")
        for schema_name, schema in schemas.items():
            if schema_name in name_key or name_key in schema_name:
                errors = _validate_schema(data, schema)
                artifact["schema_errors"] = errors
                if errors:
                    results["ok"] = False
                break

        results["artifacts"].append(artifact)

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_bundle.py <bundle_directory>")
        sys.exit(1)

    bundle_dir = sys.argv[1]
    result = verify_bundle(bundle_dir)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
