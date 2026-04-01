#!/usr/bin/env python3
"""Validate safety artifacts for schema and cross-file integrity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SAFETY_DIR = ROOT / "docs" / "safety"
STPA_PATH = SAFETY_DIR / "stpa.md"
HAZARD_LOG_PATH = SAFETY_DIR / "hazard_log.yml"
TRACEABILITY_PATH = SAFETY_DIR / "traceability.yml"


HAZARD_LOG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["hazards"],
    "properties": {
        "hazards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "title",
                    "loss_refs",
                    "unsafe_control_actions",
                    "safety_constraints",
                    "severity",
                    "likelihood",
                    "detectability",
                    "status",
                    "status_reason",
                    "enforcement",
                    "tests",
                    "verification",
                    "gates",
                    "owner",
                    "last_reviewed",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "loss_refs": {"type": "array", "items": {"type": "string"}},
                    "unsafe_control_actions": {"type": "array", "items": {"type": "string"}},
                    "safety_constraints": {"type": "array", "items": {"type": "string"}},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
                    "detectability": {"type": "string", "enum": ["low", "medium", "high"]},
                    "status": {
                        "type": "string",
                        "enum": ["enforced", "partially_mitigated", "unmitigated"],
                    },
                    "status_reason": {"type": "string"},
                    "enforcement": {"type": "array"},
                    "tests": {"type": "array"},
                    "verification": {"type": "array", "items": {"type": "string"}},
                    "gates": {"type": "array"},
                    "follow_up": {"type": "string"},
                    "owner": {"type": "string"},
                    "last_reviewed": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


TRACEABILITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["requirements"],
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "description",
                    "hazards",
                    "safety_constraints",
                    "status",
                    "status_reason",
                    "enforcement",
                    "tests",
                    "verification",
                    "gates",
                    "owner",
                    "last_reviewed",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "hazards": {"type": "array", "items": {"type": "string"}},
                    "safety_constraints": {"type": "array", "items": {"type": "string"}},
                    "status": {
                        "type": "string",
                        "enum": ["enforced", "partially_mitigated", "unmitigated"],
                    },
                    "status_reason": {"type": "string"},
                    "enforcement": {"type": "array"},
                    "tests": {"type": "array"},
                    "verification": {"type": "array", "items": {"type": "string"}},
                    "gates": {"type": "array"},
                    "follow_up": {"type": "string"},
                    "owner": {"type": "string"},
                    "last_reviewed": {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}


@dataclass(frozen=True)
class StpaIds:
    losses: set[str]
    hazards: set[str]
    ucas: set[str]
    constraints: set[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"{path} did not parse into a mapping")
    return data


def _parse_stpa_ids(text: str) -> StpaIds:
    return StpaIds(
        losses=set(re.findall(r"\bL\d+\b", text)),
        hazards=set(re.findall(r"\bH\d+\b", text)),
        ucas=set(re.findall(r"\bUCA\d+\b", text)),
        constraints=set(re.findall(r"\bSC-\d+\b", text)),
    )


def _strip_line_suffix(path: str) -> str:
    if ":L" in path:
        return path.split(":L", 1)[0]
    return path


def _extract_paths(items: Iterable[Any], key: str) -> list[str]:
    paths: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get(key)
            if isinstance(value, str):
                paths.append(value)
        elif isinstance(item, str):
            paths.append(item)
    return paths


def _validate_paths(paths: Iterable[str], context: str) -> list[str]:
    errors: list[str] = []
    for path_entry in paths:
        path = _strip_line_suffix(path_entry)
        if path and not (ROOT / path).exists():
            errors.append(f"{context}: missing path {path}")
    return errors


def _validate_schema(data: dict[str, Any], schema: dict[str, Any], name: str) -> list[str]:
    errors: list[str] = []
    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(data), key=str):
        errors.append(f"{name}: {error.message} at {list(error.path)}")
    return errors


def _validate_iso_date(value: str, context: str) -> list[str]:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return [f"{context}: last_reviewed must be YYYY-MM-DD"]
    return []


def _validate_enforced_fields(
    status: str,
    enforcement: list[Any],
    tests: list[Any],
    gates: list[Any],
    verification: list[Any],
    context: str,
) -> list[str]:
    errors: list[str] = []
    if status in {"enforced", "partially_mitigated"}:
        if not enforcement:
            errors.append(f"{context}: enforcement required for status {status}")
        if not tests:
            errors.append(f"{context}: tests required for status {status}")
        if not gates:
            errors.append(f"{context}: gates required for status {status}")
        if not verification:
            errors.append(f"{context}: verification required for status {status}")
    return errors


def main() -> int:
    errors: list[str] = []

    stpa_text = STPA_PATH.read_text(encoding="utf-8")
    stpa_ids = _parse_stpa_ids(stpa_text)

    hazard_log = _load_yaml(HAZARD_LOG_PATH)
    traceability = _load_yaml(TRACEABILITY_PATH)

    errors.extend(_validate_schema(hazard_log, HAZARD_LOG_SCHEMA, "hazard_log"))
    errors.extend(_validate_schema(traceability, TRACEABILITY_SCHEMA, "traceability"))

    hazard_items = hazard_log.get("hazards", [])
    requirement_items = traceability.get("requirements", [])

    hazard_ids = {hazard.get("id") for hazard in hazard_items if isinstance(hazard, dict)}
    if len(hazard_ids) != len(hazard_items):
        errors.append("hazard_log: duplicate or missing hazard ids")

    requirement_ids = {
        requirement.get("id") for requirement in requirement_items if isinstance(requirement, dict)
    }
    if len(requirement_ids) != len(requirement_items):
        errors.append("traceability: duplicate or missing requirement ids")

    for hazard in hazard_items:
        if not isinstance(hazard, dict):
            continue
        hid = hazard.get("id")
        if isinstance(hid, str) and hid not in stpa_ids.hazards:
            errors.append(f"hazard_log: hazard {hid} not found in stpa.md")
        for loss in hazard.get("loss_refs", []):
            if isinstance(loss, str) and loss not in stpa_ids.losses:
                errors.append(f"hazard_log: loss {loss} not found in stpa.md")
        for uca in hazard.get("unsafe_control_actions", []):
            if isinstance(uca, str) and uca not in stpa_ids.ucas:
                errors.append(f"hazard_log: UCA {uca} not found in stpa.md")
        for sc in hazard.get("safety_constraints", []):
            if isinstance(sc, str) and sc not in stpa_ids.constraints:
                errors.append(f"hazard_log: SC {sc} not found in stpa.md")

        if isinstance(hazard.get("last_reviewed"), str):
            errors.extend(
                _validate_iso_date(hazard["last_reviewed"], f"hazard_log:{hid}:last_reviewed")
            )

        errors.extend(
            _validate_enforced_fields(
                hazard.get("status", ""),
                hazard.get("enforcement", []),
                hazard.get("tests", []),
                hazard.get("gates", []),
                hazard.get("verification", []),
                f"hazard_log:{hid}",
            )
        )

        errors.extend(
            _validate_paths(
                _extract_paths(hazard.get("enforcement", []), "code"),
                f"hazard_log:{hid}:enforcement",
            )
        )
        errors.extend(
            _validate_paths(
                _extract_paths(hazard.get("tests", []), "path"),
                f"hazard_log:{hid}:tests",
            )
        )
        for gate in hazard.get("gates", []):
            if isinstance(gate, dict):
                workflow = gate.get("workflow")
                if isinstance(workflow, str) and not (ROOT / workflow).exists():
                    errors.append(f"hazard_log:{hid}:gate missing workflow {workflow}")

    for requirement in requirement_items:
        if not isinstance(requirement, dict):
            continue
        rid = requirement.get("id")
        for hazard_id in requirement.get("hazards", []):
            if isinstance(hazard_id, str) and hazard_id not in hazard_ids:
                errors.append(f"traceability:{rid}: hazard {hazard_id} not in hazard_log")
        for sc in requirement.get("safety_constraints", []):
            if isinstance(sc, str) and sc not in stpa_ids.constraints:
                errors.append(f"traceability:{rid}: SC {sc} not found in stpa.md")

        if isinstance(requirement.get("last_reviewed"), str):
            errors.extend(
                _validate_iso_date(
                    requirement["last_reviewed"], f"traceability:{rid}:last_reviewed"
                )
            )

        errors.extend(
            _validate_enforced_fields(
                requirement.get("status", ""),
                requirement.get("enforcement", []),
                requirement.get("tests", []),
                requirement.get("gates", []),
                requirement.get("verification", []),
                f"traceability:{rid}",
            )
        )

        errors.extend(
            _validate_paths(
                _extract_paths(requirement.get("enforcement", []), "code"),
                f"traceability:{rid}:enforcement",
            )
        )
        errors.extend(
            _validate_paths(
                _extract_paths(requirement.get("tests", []), "path"),
                f"traceability:{rid}:tests",
            )
        )
        for gate in requirement.get("gates", []):
            if isinstance(gate, dict):
                workflow = gate.get("workflow")
                if isinstance(workflow, str) and not (ROOT / workflow).exists():
                    errors.append(f"traceability:{rid}:gate missing workflow {workflow}")

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Safety artifacts validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
