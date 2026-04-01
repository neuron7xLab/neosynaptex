#!/usr/bin/env python3
"""Validate deterministic dependency policy and hidden dependency discipline."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"
LOCK = ROOT / "governance/requirements-governance.lock.json"

GOVERNANCE_TOOL_FILES = [
    "tools/validate_governance.py",
    "tools/governance_contract.py",
    "tools/render_governance_checklist.py",
    "tools/run_local_governance_baseline.py",
    "tools/validate_pr_intake.py",
    "tools/check_governance_nondeterminism.py",
    "tools/check_cli_contracts.py",
    "tools/check_dependency_hermeticity.py",
    "tools/check_internal_links.py",
    "tools/check_external_links.py",
    "tools/validate_publication_surfaces.py",
    "tools/verify_ci_artifact_manifest.py",
    "tools/assert_fail_closed_semantics.py",
    "tools/assert_gate_benchmark_invariants.py",
    "tools/assert_worked_example_semantics.py",
    "tools/check_canonical_hash_stability.py",
    "tools/check_canonicalization_negative_cases.py",
    "tools/verify_manifest.py",
    "tools/validate_json.py",
    "tools/reference_runner.py",
]


THIRD_PARTY_IMPORT_TO_PACKAGE = {
    "yaml": "PyYAML",
    "jsonschema": "jsonschema",
}


def parse_requirements(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise SystemExit(f"NON_DETERMINISTIC_REQUIREMENT {line}")
        name, ver = [x.strip() for x in line.split("==", 1)]
        if not name or not ver:
            raise SystemExit(f"MALFORMED_REQUIREMENT {line}")
        out[name] = ver
    return out


def third_party_imports(pyfile: Path) -> set[str]:
    tree = ast.parse(pyfile.read_text(encoding="utf-8"), filename=str(pyfile))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return {m for m in imports if m in THIRD_PARTY_IMPORT_TO_PACKAGE}


def main() -> int:
    req = parse_requirements(REQ)
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    lock_pkgs: dict[str, str] = lock.get("packages", {})

    if set(req.keys()) != set(lock_pkgs.keys()):
        raise SystemExit(f"LOCK_DRIFT package-set requirements={sorted(req)} lock={sorted(lock_pkgs)}")
    for pkg, ver in req.items():
        if lock_pkgs.get(pkg) != ver:
            raise SystemExit(f"LOCK_DRIFT_VERSION {pkg} requirements={ver} lock={lock_pkgs.get(pkg)}")

    used_pkgs: set[str] = set()
    for rel in GOVERNANCE_TOOL_FILES:
        p = ROOT / rel
        if not p.exists():
            raise SystemExit(f"MISSING_GOVERNANCE_TOOL {rel}")
        for mod in third_party_imports(p):
            used_pkgs.add(THIRD_PARTY_IMPORT_TO_PACKAGE[mod])

    undeclared = sorted(used_pkgs - set(req.keys()))
    if undeclared:
        raise SystemExit(f"UNDECLARED_DEPENDENCIES {undeclared}")

    print("DEPENDENCY_HERMETICITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
