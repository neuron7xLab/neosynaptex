#!/usr/bin/env python3
"""Generate Causal Conformance Matrix.

Maps every causal rule to its test coverage and falsification scenario.
Produces: artifacts/causal_conformance_matrix.json
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from mycelium_fractal_net.core.rule_registry import get_registry

    registry = get_registry()

    # Scan test files for rule references
    test_dir = Path("tests")
    test_coverage: dict[str, list[str]] = {}
    for test_file in test_dir.rglob("*.py"):
        if "__pycache__" in str(test_file):
            continue
        content = test_file.read_text(encoding="utf-8", errors="ignore")
        for rule_id in registry:
            if rule_id in content:
                test_coverage.setdefault(rule_id, []).append(str(test_file))

    # Scan validation for scenario coverage
    val_dir = Path("validation")
    scenario_coverage: dict[str, list[str]] = {}
    for val_file in val_dir.rglob("*.py"):
        if "__pycache__" in str(val_file):
            continue
        content = val_file.read_text(encoding="utf-8", errors="ignore")
        for rule_id in registry:
            if rule_id in content:
                scenario_coverage.setdefault(rule_id, []).append(str(val_file))

    rules = []
    for rule_id, rule_obj in sorted(registry.items()):
        rules.append(
            {
                "rule_id": rule_id,
                "stage": rule_obj.stage,
                "severity": rule_obj.severity.value,
                "category": rule_obj.category.value,
                "scientific_claim": rule_obj.spec.claim,
                "math": rule_obj.spec.math,
                "reference": rule_obj.spec.reference,
                "falsifiable_by": rule_obj.spec.falsifiable_by,
                "rationale": rule_obj.spec.rationale,
                "expected_failure_mode": rule_obj.spec.falsifiable_by,
                "test_coverage": test_coverage.get(rule_id, []),
                "scenario_coverage": scenario_coverage.get(rule_id, []),
                "has_test": len(test_coverage.get(rule_id, [])) > 0,
                "has_falsification": bool(rule_obj.spec.falsifiable_by),
            }
        )

    matrix = {
        "schema_version": "mfn-causal-conformance-v1",
        "total_rules": len(rules),
        "rules_with_tests": sum(1 for r in rules if r["has_test"]),
        "rules_with_falsification": sum(1 for r in rules if r["has_falsification"]),
        "rules": rules,
    }

    out = Path("artifacts/causal_conformance_matrix.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=2))
    print(f"Conformance matrix: {out}")
    print(f"  Rules: {matrix['total_rules']}")
    print(f"  With tests: {matrix['rules_with_tests']}")
    print(f"  With falsification: {matrix['rules_with_falsification']}")


if __name__ == "__main__":
    main()
