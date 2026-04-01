#!/usr/bin/env python3
"""Generate JSON Schemas for all artifact types.

Produces: docs/contracts/schemas/*.schema.json
"""

from __future__ import annotations

import json
from pathlib import Path


def _dataclass_to_schema(cls, title: str, version: str) -> dict:
    """Convert a dataclass to a JSON Schema (draft-07)."""
    properties = {}

    for name, field_obj in cls.__dataclass_fields__.items():
        field_type = field_obj.type
        type_str = str(field_type)

        # Map Python types to JSON Schema types
        if "float" in type_str:
            prop = {"type": "number"}
        elif "int" in type_str:
            prop = {"type": "integer"}
        elif "bool" in type_str:
            prop = {"type": "boolean"}
        elif "str" in type_str:
            prop = {"type": "string"}
        elif "dict" in type_str:
            prop = {"type": "object"}
        elif "list" in type_str or "tuple" in type_str:
            prop = {"type": "array"}
        elif "None" in type_str:
            prop = {"type": ["null", "object"]}
        else:
            prop = {"type": "object"}

        if "None" in type_str or "| None" in type_str:
            prop = {"oneOf": [prop, {"type": "null"}]}

        properties[name] = prop

        # Fields without defaults are required
        if field_obj.default is field_obj.default_factory is type(field_obj.default):
            pass  # has default

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": title,
        "version": version,
        "type": "object",
        "properties": properties,
        "additionalProperties": True,
    }


def main() -> None:
    from mycelium_fractal_net.types.causal import CausalValidationResult
    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.field import SimulationSpec
    from mycelium_fractal_net.types.forecast import ComparisonResult, ForecastResult
    from mycelium_fractal_net.types.report import AnalysisReport

    schemas = [
        (SimulationSpec, "SimulationSpec", "v1"),
        (MorphologyDescriptor, "MorphologyDescriptor", "v1"),
        (AnomalyEvent, "AnomalyEvent", "v1"),
        (ForecastResult, "ForecastResult", "v1"),
        (ComparisonResult, "ComparisonResult", "v1"),
        (CausalValidationResult, "CausalValidationResult", "v1"),
        (AnalysisReport, "AnalysisReport", "v1"),
    ]

    out_dir = Path("docs/contracts/schemas")
    out_dir.mkdir(parents=True, exist_ok=True)

    for cls, title, version in schemas:
        schema = _dataclass_to_schema(cls, title, version)
        filename = f"{title.lower()}.{version}.schema.json"
        path = out_dir / filename
        path.write_text(json.dumps(schema, indent=2))
        print(f"  {path} ({len(schema['properties'])} properties)")

    # Bundle manifest schema
    manifest = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "BundleManifest",
        "version": "v1",
        "type": "object",
        "properties": {
            "schema_version": {"type": "string"},
            "engine_version": {"type": "string"},
            "run_id": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "artifacts": {"type": "object"},
            "checksums": {"type": "object"},
            "signature": {"type": ["string", "null"]},
        },
        "required": ["schema_version", "engine_version", "run_id"],
    }
    (out_dir / "manifest.v1.schema.json").write_text(json.dumps(manifest, indent=2))
    print(f"  {out_dir / 'manifest.v1.schema.json'}")

    print(f"\nGenerated {len(schemas) + 1} schemas in {out_dir}")


if __name__ == "__main__":
    main()
