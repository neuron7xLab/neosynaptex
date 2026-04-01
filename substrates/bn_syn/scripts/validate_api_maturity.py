"""Validate package maturity status mapping for public BN-Syn modules."""

from __future__ import annotations

import argparse
from pathlib import Path

import json

VALID_STATUSES = {"stable", "experimental", "deprecated"}
REQUIRED_STABLE_MODULES = {
    "bnsyn.config",
    "bnsyn.rng",
    "bnsyn.cli",
    "bnsyn.neurons",
    "bnsyn.synapses",
    "bnsyn.control",
    "bnsyn.simulation",
    "bnsyn.sim.network",
    "bnsyn.neuron.adex",
    "bnsyn.synapse.conductance",
    "bnsyn.plasticity.three_factor",
    "bnsyn.criticality.branching",
    "bnsyn.temperature.schedule",
    "bnsyn.connectivity.sparse",
}


def validate_maturity_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Missing maturity file: {path}"]

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ["Maturity file root must be a mapping"]

    modules = data.get("modules")
    if not isinstance(modules, dict):
        return ["Field 'modules' must be a mapping"]

    for module_name, status in modules.items():
        if not isinstance(module_name, str) or not module_name:
            errors.append("Module names must be non-empty strings")
            continue
        if status not in VALID_STATUSES:
            errors.append(
                f"Module {module_name!r} has invalid status {status!r}; "
                f"expected one of {sorted(VALID_STATUSES)}"
            )

    missing_stable = sorted(REQUIRED_STABLE_MODULES - set(modules))
    for module_name in missing_stable:
        errors.append(f"Missing required stable module tag: {module_name}")

    for module_name in REQUIRED_STABLE_MODULES & set(modules):
        if modules[module_name] != "stable":
            errors.append(f"Module {module_name} must be tagged as stable")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs/api_maturity.json")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs/api_maturity.json"),
        help="Path to api maturity JSON file",
    )
    args = parser.parse_args()

    errors = validate_maturity_file(args.path)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("api_maturity validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
