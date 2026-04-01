#!/usr/bin/env python3
"""Contract Validator — single source of truth for all system contracts.

Validates that types, API surface, schemas, and documentation are consistent.
Any drift = CI blocker.

Produces: artifacts/contract_validation_report.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _check_api_surface() -> list[str]:
    """Verify all V1_SURFACE symbols are importable."""
    errors = []
    import mycelium_fractal_net as mfn

    for name in mfn.V1_SURFACE:
        if not hasattr(mfn, name):
            errors.append(f"V1_SURFACE: {name!r} not importable")
    return errors


def _check_schemas() -> list[str]:
    """Verify all artifact schemas exist and are valid JSON Schema."""
    errors = []
    schema_dir = Path("docs/contracts/schemas")
    if not schema_dir.exists():
        errors.append("Schema directory docs/contracts/schemas/ missing")
        return errors

    required = [
        "simulationspec",
        "morphologydescriptor",
        "anomalyevent",
        "forecastresult",
        "comparisonresult",
        "causalvalidationresult",
        "analysisreport",
        "manifest",
    ]
    existing = {f.stem.split(".")[0] for f in schema_dir.glob("*.schema.json")}
    for name in required:
        if name not in existing:
            errors.append(f"Missing schema: {name}")

    for sf in schema_dir.glob("*.schema.json"):
        try:
            data = json.loads(sf.read_text())
            if "$schema" not in data:
                errors.append(f"{sf.name}: missing $schema")
            if "version" not in data:
                errors.append(f"{sf.name}: missing version")
        except json.JSONDecodeError as e:
            errors.append(f"{sf.name}: invalid JSON: {e}")

    return errors


def _check_type_roundtrips() -> list[str]:
    """Verify key types survive JSON roundtrip."""
    errors = []
    import mycelium_fractal_net as mfn

    spec = mfn.SimulationSpec(grid_size=16, steps=8, seed=42)
    seq = mfn.simulate(spec)
    desc = mfn.extract(seq)
    det = mfn.detect(seq)

    # SimulationSpec roundtrip
    try:
        d = spec.to_dict()
        restored = mfn.SimulationSpec.from_dict(d)
        if restored.grid_size != spec.grid_size:
            errors.append("SimulationSpec roundtrip: grid_size mismatch")
    except Exception as e:
        errors.append(f"SimulationSpec roundtrip failed: {e}")

    # MorphologyDescriptor roundtrip
    try:
        d = desc.to_dict()
        from mycelium_fractal_net.types.features import MorphologyDescriptor

        restored = MorphologyDescriptor.from_dict(d)
        if restored.features != desc.features:
            errors.append("MorphologyDescriptor roundtrip: features mismatch")
    except Exception as e:
        errors.append(f"MorphologyDescriptor roundtrip failed: {e}")

    # AnomalyEvent serializable
    try:
        d = det.to_dict()
        json.dumps(d, default=str)
    except Exception as e:
        errors.append(f"AnomalyEvent serialization failed: {e}")

    return errors


def _check_docs_exist() -> list[str]:
    """Verify critical documentation files exist."""
    errors = []
    required_docs = [
        "docs/PUBLIC_API_CONTRACT.md",
        "docs/BUNDLE_SPEC.md",
        "docs/INTEROP_CONTRACT.md",
        "docs/REPRODUCIBILITY.md",
        "docs/INTERVENTION_PLANNER.md",
        "docs/QUALITY_GATE.md",
        "KNOWN_LIMITATIONS.md",
        "CHANGELOG.md",
    ]
    for doc in required_docs:
        if not Path(doc).exists():
            errors.append(f"Missing doc: {doc}")
    return errors


def main() -> None:
    all_errors: list[str] = []

    print("Validating API surface...")
    all_errors.extend(_check_api_surface())

    print("Validating schemas...")
    all_errors.extend(_check_schemas())

    print("Validating type roundtrips...")
    all_errors.extend(_check_type_roundtrips())

    print("Validating docs...")
    all_errors.extend(_check_docs_exist())

    report = {
        "ok": len(all_errors) == 0,
        "errors": all_errors,
        "checks_passed": 4 - bool(all_errors),
    }

    out = Path("artifacts/contract_validation_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    if all_errors:
        print(f"\nFAILED: {len(all_errors)} contract violations:")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nPASS: All contracts valid")


if __name__ == "__main__":
    main()
