#!/usr/bin/env python3
"""OpenAPI contract compatibility check.

Checks for breaking changes between a baseline spec and a candidate spec.
Fails on removed paths/operations, removed response codes, removed schemas,
and removal of required properties.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _collect_operations(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    operations: dict[tuple[str, str], dict[str, Any]] = {}
    for path, methods in spec.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
                "trace",
            }:
                continue
            operations[(path, method.lower())] = details or {}
    return operations


def _collect_schemas(spec: dict[str, Any]) -> dict[str, Any]:
    return spec.get("components", {}).get("schemas", {}) or {}


def _collect_required_properties(schema: dict[str, Any]) -> set[str]:
    required = set(schema.get("required", []) or [])
    properties = schema.get("properties", {}) or {}
    for _prop_name, prop_schema in properties.items():
        if isinstance(prop_schema, dict):
            required |= _collect_required_properties(prop_schema)
    return required


def _check_required_properties(
    baseline_schema: dict[str, Any], candidate_schema: dict[str, Any]
) -> list[str]:
    failures: list[str] = []
    base_required = set(baseline_schema.get("required", []) or [])
    cand_required = set(candidate_schema.get("required", []) or [])
    removed_required = base_required - cand_required
    if removed_required:
        failures.append(f"removed required properties: {sorted(removed_required)}")

    base_props = baseline_schema.get("properties", {}) or {}
    cand_props = candidate_schema.get("properties", {}) or {}
    for prop_name, prop_schema in base_props.items():
        if prop_name not in cand_props:
            failures.append(f"removed property: {prop_name}")
            continue
        if isinstance(prop_schema, dict) and isinstance(cand_props.get(prop_name), dict):
            nested_failures = _check_required_properties(prop_schema, cand_props[prop_name])
            failures.extend([f"{prop_name}.{item}" for item in nested_failures])
    return failures


def check_breaking_changes(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> list[str]:
    failures: list[str] = []

    baseline_ops = _collect_operations(baseline)
    candidate_ops = _collect_operations(candidate)

    for op_key, op_details in baseline_ops.items():
        if op_key not in candidate_ops:
            failures.append(f"removed operation: {op_key[1].upper()} {op_key[0]}")
            continue

        base_responses = op_details.get("responses", {}) or {}
        cand_responses = candidate_ops[op_key].get("responses", {}) or {}
        for status_code in base_responses:
            if status_code not in cand_responses:
                failures.append(
                    f"removed response {status_code} for {op_key[1].upper()} {op_key[0]}"
                )

        base_request = op_details.get("requestBody")
        cand_request = candidate_ops[op_key].get("requestBody")
        if base_request and not cand_request:
            failures.append(f"removed requestBody for {op_key[1].upper()} {op_key[0]}")
        if base_request and cand_request:
            base_required = bool(base_request.get("required", False))
            cand_required = bool(cand_request.get("required", False))
            if base_required and not cand_required:
                failures.append(
                    f"requestBody required removed for {op_key[1].upper()} {op_key[0]}"
                )

    baseline_schemas = _collect_schemas(baseline)
    candidate_schemas = _collect_schemas(candidate)
    for schema_name, schema in baseline_schemas.items():
        if schema_name not in candidate_schemas:
            failures.append(f"removed schema: {schema_name}")
            continue
        if isinstance(schema, dict) and isinstance(candidate_schemas[schema_name], dict):
            prop_failures = _check_required_properties(schema, candidate_schemas[schema_name])
            for failure in prop_failures:
                failures.append(f"schema {schema_name}: {failure}")

    return failures


def _write_summary(path: Path | None, failures: list[str]) -> None:
    if not path:
        return
    lines = []
    if failures:
        lines.append("## ❌ OpenAPI contract check failed")
        lines.append("")
        lines.append("Breaking changes detected:")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("## ✅ OpenAPI contract check passed")
        lines.append("")
        lines.append("No breaking changes detected.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI contract check")
    parser.add_argument("--baseline", required=True, help="Path to baseline OpenAPI JSON")
    parser.add_argument("--candidate", required=True, help="Path to candidate OpenAPI JSON")
    parser.add_argument(
        "--summary-file", help="Optional path to write GitHub step summary markdown"
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)

    if not baseline_path.exists():
        print(f"Baseline not found: {baseline_path}", file=sys.stderr)
        return 2
    if not candidate_path.exists():
        print(f"Candidate not found: {candidate_path}", file=sys.stderr)
        return 2

    baseline = _load_spec(baseline_path)
    candidate = _load_spec(candidate_path)
    failures = check_breaking_changes(baseline, candidate)

    summary_path = Path(args.summary_file) if args.summary_file else None
    _write_summary(summary_path, failures)

    if failures:
        print("Breaking changes detected:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("OpenAPI contract check passed (no breaking changes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
