from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
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


def collect_equations(doc_roots: list[Path]) -> set[str]:
    eq_ids: set[str] = set()
    pattern = re.compile(r"\b(EQ-[A-Z0-9\-]+)\b")
    for root in doc_roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in {".md", ".tex"}:
                text = root.read_text(encoding="utf-8", errors="ignore")
                eq_ids.update(pattern.findall(text))
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".md", ".tex"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            eq_ids.update(pattern.findall(text))
    return eq_ids


def collect_test_traces(test_root: Path) -> set[str]:
    ids: set[str] = set()
    if not test_root.exists():
        return ids
    for test_file in test_root.rglob("test_*.py"):
        text = test_file.read_text(encoding="utf-8", errors="ignore")
        ids.update(TRACE_RE.findall(text))
    return ids


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

    missing = sorted(eq for eq in equations if eq not in test_traces)
    if missing:
        print("FAIL: missing test trace bindings for equations:")
        for eq in missing:
            print(f"  - {eq}")
        return 1

    print(
        "PASS: invariants contract valid | "
        f"equations={len(equations)} traces={len(test_traces)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
