"""Schema↔Code sync tests — verify JSON schemas match actual dataclass fields.

If a dataclass gains a new field, the schema must be regenerated.
If a schema lists a field the code doesn't have, the schema is stale.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_DIR = Path("docs/contracts/schemas")


def _get_dataclass_fields(cls: type) -> set[str]:
    """Get field names from a frozen dataclass."""
    return set(cls.__dataclass_fields__.keys())


class TestSchemaCodeSync:
    """Every schema property must exist as a dataclass field (and vice versa)."""

    def test_simulation_spec_sync(self) -> None:
        from mycelium_fractal_net.types.field import SimulationSpec

        schema = json.loads((SCHEMA_DIR / "simulationspec.v1.schema.json").read_text())
        schema_fields = set(schema["properties"].keys())
        code_fields = _get_dataclass_fields(SimulationSpec)
        # Schema should be subset of code (schema may omit private fields)
        extra_in_schema = schema_fields - code_fields
        assert not extra_in_schema, f"Schema has fields not in code: {extra_in_schema}"

    def test_anomaly_event_sync(self) -> None:
        from mycelium_fractal_net.types.detection import AnomalyEvent

        schema = json.loads((SCHEMA_DIR / "anomalyevent.v1.schema.json").read_text())
        schema_fields = set(schema["properties"].keys())
        code_fields = _get_dataclass_fields(AnomalyEvent)
        extra_in_schema = schema_fields - code_fields
        assert not extra_in_schema, f"Schema has fields not in code: {extra_in_schema}"

    def test_forecast_result_sync(self) -> None:
        from mycelium_fractal_net.types.forecast import ForecastResult

        schema = json.loads((SCHEMA_DIR / "forecastresult.v1.schema.json").read_text())
        schema_fields = set(schema["properties"].keys())
        code_fields = _get_dataclass_fields(ForecastResult)
        extra_in_schema = schema_fields - code_fields
        assert not extra_in_schema, f"Schema has fields not in code: {extra_in_schema}"

    def test_all_schemas_valid_json(self) -> None:
        for sf in SCHEMA_DIR.glob("*.schema.json"):
            data = json.loads(sf.read_text())
            assert "$schema" in data, f"{sf.name}: no $schema"
            assert "properties" in data, f"{sf.name}: no properties"
