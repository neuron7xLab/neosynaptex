"""Validate codebase readiness audit JSON structure and scoring invariants."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

CATEGORY_WEIGHTS: dict[str, float] = {
    "A Build & Reproducibility": 0.12,
    "B Test Quality & Reliability": 0.16,
    "C Coverage & Mutation/Quality Signals": 0.08,
    "D Static Analysis & Linting": 0.08,
    "E Type Safety / Contracts": 0.08,
    "F Dependency Hygiene": 0.08,
    "G Security (SAST/Secrets/Vuln)": 0.12,
    "H Documentation & Onboarding": 0.08,
    "I Observability & Ops Readiness": 0.10,
    "J Release Engineering (versioning, changelog, artifacts, rollback)": 0.10,
}

ALLOWED_CONFIDENCE = {"high", "medium", "low"}
EVIDENCE_PATTERN = re.compile(r"^(file:[^#\s]+#L\d+-L\d+: .+|cmd:[^:]+: .+)$")


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_audit_report(path: Path) -> list[str]:
    errors: list[str] = []

    if not path.exists():
        return [f"Missing audit report: {path}"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    if not isinstance(payload, dict):
        return ["Audit report root must be a JSON object"]

    readiness_percent = payload.get("readiness_percent")
    if not isinstance(readiness_percent, int) or not 0 <= readiness_percent <= 100:
        errors.append("readiness_percent must be an integer in [0, 100]")

    confidence = payload.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE:
        errors.append(f"confidence must be one of {sorted(ALLOWED_CONFIDENCE)}")

    scorecard = payload.get("scorecard")
    if not isinstance(scorecard, list):
        errors.append("scorecard must be a list")
        return errors

    if len(scorecard) != len(CATEGORY_WEIGHTS):
        errors.append(f"scorecard must contain exactly {len(CATEGORY_WEIGHTS)} categories")

    seen_categories: set[str] = set()
    weighted_sum = 0.0

    for index, row in enumerate(scorecard, start=1):
        if not isinstance(row, dict):
            errors.append(f"scorecard[{index}] must be an object")
            continue

        category = row.get("category")
        if category not in CATEGORY_WEIGHTS:
            errors.append(f"scorecard[{index}] has unknown category {category!r}")
            continue

        if category in seen_categories:
            errors.append(f"scorecard has duplicated category {category!r}")
            continue
        seen_categories.add(category)

        score = row.get("score_0_to_5")
        if not isinstance(score, int) or not 0 <= score <= 5:
            errors.append(f"scorecard[{index}] score_0_to_5 must be integer in [0, 5]")
            continue

        weight = row.get("weight")
        expected_weight = CATEGORY_WEIGHTS[category]
        if not isinstance(weight, (float, int)) or abs(float(weight) - expected_weight) > 1e-9:
            errors.append(
                f"scorecard[{index}] weight must be {expected_weight:.2f} for category {category!r}"
            )
            continue

        weighted_sum += (score / 5.0) * expected_weight

        for field in ("evidence", "unknowns", "key_gaps"):
            field_value = row.get(field)
            if not isinstance(field_value, list) or not field_value:
                errors.append(f"scorecard[{index}] field {field!r} must be a non-empty list")
                continue
            for evidence_idx, entry in enumerate(field_value, start=1):
                if not _is_non_empty_string(entry):
                    errors.append(
                        f"scorecard[{index}] field {field!r} entry #{evidence_idx} must be a non-empty string"
                    )
                    continue
                if field == "evidence" and not EVIDENCE_PATTERN.match(entry):
                    errors.append(
                        f"scorecard[{index}] evidence entry #{evidence_idx} has invalid format: {entry!r}"
                    )

    if seen_categories != set(CATEGORY_WEIGHTS):
        missing = sorted(set(CATEGORY_WEIGHTS) - seen_categories)
        if missing:
            errors.append(f"scorecard is missing categories: {missing}")

    expected_readiness = round(weighted_sum * 100)
    if isinstance(readiness_percent, int) and readiness_percent != expected_readiness:
        errors.append(
            f"readiness_percent mismatch: declared={readiness_percent}, expected={expected_readiness}"
        )

    blockers = payload.get("top_blockers")
    if not isinstance(blockers, list) or len(blockers) < 3:
        errors.append("top_blockers must be a list with at least 3 items")
    else:
        for expected_rank, blocker in enumerate(blockers, start=1):
            if not isinstance(blocker, dict):
                errors.append(f"top_blockers[{expected_rank}] must be an object")
                continue
            if blocker.get("rank") != expected_rank:
                errors.append(
                    f"top_blockers[{expected_rank}] rank must be {expected_rank}, got {blocker.get('rank')!r}"
                )
            for field in ("blocker", "impact"):
                if not _is_non_empty_string(blocker.get(field)):
                    errors.append(f"top_blockers[{expected_rank}] field {field!r} must be non-empty string")
            for list_field in ("fix_plan", "evidence"):
                entries = blocker.get(list_field)
                if not isinstance(entries, list) or not entries:
                    errors.append(
                        f"top_blockers[{expected_rank}] field {list_field!r} must be non-empty list"
                    )
                    continue
                for entry_idx, entry in enumerate(entries, start=1):
                    if not _is_non_empty_string(entry):
                        errors.append(
                            f"top_blockers[{expected_rank}] field {list_field!r} entry #{entry_idx} must be non-empty string"
                        )
                    elif list_field == "evidence" and not EVIDENCE_PATTERN.match(entry):
                        errors.append(
                            "top_blockers["
                            f"{expected_rank}] evidence entry #{entry_idx} has invalid format: {entry!r}"
                        )

    exec_summary = payload.get("exec_summary")
    if not _is_non_empty_string(exec_summary):
        errors.append("exec_summary must be a non-empty string")
    else:
        words = len(exec_summary.split())
        if words > 120:
            errors.append(f"exec_summary exceeds 120 words ({words})")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate codebase readiness audit JSON shape and score invariants"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs/appendix/codebase_readiness_audit_2026-02-15.json"),
        help="Path to audit report JSON file",
    )
    args = parser.parse_args()

    violations = validate_audit_report(args.path)
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}")
        return 1

    print("codebase_readiness_audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
