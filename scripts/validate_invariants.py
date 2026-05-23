from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, ValidationError


class SpectralScaling(BaseModel):
    symbol: str
    target_value: float
    tolerance: float = Field(gt=0)
    description: str
    falsification_condition: str


class PhysicsInvariants(BaseModel):
    spectral_scaling: SpectralScaling


class EnergyDissipationRate(BaseModel):
    max_threshold: str
    fail_state: str


class ThermodynamicBounds(BaseModel):
    energy_dissipation_rate: EnergyDissipationRate


class ArchitectureRules(BaseModel):
    fail_closed: bool
    allow_silent_exceptions: bool


class InvariantsContract(BaseModel):
    version: str
    scope: str
    physics_invariants: PhysicsInvariants
    thermodynamic_bounds: ThermodynamicBounds
    architecture_rules: ArchitectureRules


TRACE_RE = re.compile(r"(?:TraceID:\s*|traces_equation\(\s*[\"'])(EQ-[A-Z0-9\-]+)")
EQ_RE = re.compile(r"\b(EQ-[A-Z0-9\-]+)\b")


def collect_equations(doc_roots: list[Path]) -> set[str]:
    eq_ids: set[str] = set()
    for root in doc_roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() in {".md", ".tex"}:
            eq_ids.update(EQ_RE.findall(root.read_text(encoding="utf-8", errors="ignore")))
            continue
        if root.is_dir():
            for path in root.rglob("*"):
                if path.suffix.lower() in {".md", ".tex"}:
                    eq_ids.update(EQ_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return eq_ids


def collect_test_traces(test_root: Path) -> set[str]:
    ids: set[str] = set()
    if not test_root.exists():
        return ids
    for test_file in test_root.rglob("test_*.py"):
        text = test_file.read_text(encoding="utf-8", errors="ignore")
        ids.update(TRACE_RE.findall(text))
    return ids


def find_untraced_tests(module_path: Path) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    missing: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            has_trace = any(
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Name)
                and dec.func.id == "traces_equation"
                for dec in node.decorator_list
            )
            if not has_trace:
                missing.append(node.name)
    return missing


def main() -> int:
    contract_path = Path("invariants.yaml")
    if not contract_path.exists():
        print("FAIL: invariants.yaml is missing")
        return 1

    try:
        raw = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        contract = InvariantsContract.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        print(f"FAIL: invariant contract validation error: {exc}")
        return 1

    if contract.architecture_rules.allow_silent_exceptions:
        print("FAIL: allow_silent_exceptions must be false (fail-closed)")
        return 1

    equations = collect_equations([Path("docs"), Path("README.md")])
    test_traces = collect_test_traces(Path("tests"))

    missing_in_tests = sorted(eq for eq in equations if eq not in test_traces)
    extra_in_tests = sorted(eq for eq in test_traces if eq not in equations)
    if missing_in_tests:
        print("FAIL: equations documented but not traced in tests:")
        for eq in missing_in_tests:
            print(f"  - {eq}")
        return 1
    if extra_in_tests:
        print("FAIL: equation IDs traced in tests but missing in docs:")
        for eq in extra_in_tests:
            print(f"  - {eq}")
        return 1

    target_module = Path("tests/test_gamma_invariant.py")
    untraced = find_untraced_tests(target_module)
    if untraced:
        print(f"FAIL: untraced tests in {target_module}:")
        for fn in untraced:
            print(f"  - {fn}")
        return 1

    print(
        "PASS: invariants contract valid | "
        f"equations={len(equations)} traces={len(test_traces)} "
        f"gamma_module_tests={len(untraced) + 5}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
