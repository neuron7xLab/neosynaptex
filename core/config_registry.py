"""Unified Config Registry — schema validation for all substrates.

Enforces NFI invariants in configuration:
- gamma field → REJECT (derived only)
- modulation_bound > 0.05 → REJECT
- ssi_mode != "external" → REJECT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConfigValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


class ConfigRegistry:
    """Central configuration registry with schema + invariant validation."""

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        self._defaults: dict[str, dict[str, Any]] = {}

    def register_schema(
        self, substrate: str, schema: dict[str, Any], defaults: dict[str, Any] | None = None
    ) -> None:
        """Register validation schema for a substrate."""
        self._schemas[substrate] = schema
        if defaults:
            self._defaults[substrate] = defaults

    def validate(self, substrate: str, config: dict[str, Any]) -> ConfigValidationResult:
        """Validate config against schema + NFI invariants."""
        errors: list[str] = []
        warnings: list[str] = []

        # NFI invariant checks (apply to ALL configs)
        inv_errors = self.invariant_check(config)
        errors.extend(inv_errors)

        # Schema validation
        schema = self._schemas.get(substrate)
        if schema is None:
            warnings.append(f"No schema registered for '{substrate}'")
        else:
            schema_errors = self._validate_schema(config, schema, prefix=substrate)
            errors.extend(schema_errors)

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def get_defaults(self, substrate: str) -> dict[str, Any]:
        """Get default config for substrate."""
        return dict(self._defaults.get(substrate, {}))

    def merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Merge override into base, with invariant check on result."""
        result = {**base, **override}
        inv_errors = self.invariant_check(result)
        if inv_errors:
            raise ValueError(f"Merged config violates invariants: {'; '.join(inv_errors)}")
        return result

    @staticmethod
    def invariant_check(config: dict[str, Any]) -> list[str]:
        """Check NFI invariants in configuration."""
        errors: list[str] = []

        # INV: gamma must never be in config (derived only)
        if "gamma" in config:
            errors.append("INV-1: 'gamma' field in config (gamma is derived only, never assigned)")

        # INV: modulation_bound must be <= 0.05
        mod_bound = config.get("modulation_bound")
        if mod_bound is not None and float(mod_bound) > 0.05:
            errors.append(f"INV-3: modulation_bound={mod_bound} > 0.05 (max bounded modulation)")

        # INV: ssi_mode must be "external"
        ssi_mode = config.get("ssi_mode")
        if ssi_mode is not None and ssi_mode != "external":
            errors.append(f"INV-SSI: ssi_mode='{ssi_mode}' (must be 'external')")

        return errors

    @staticmethod
    def _validate_schema(
        config: dict[str, Any], schema: dict[str, Any], prefix: str = ""
    ) -> list[str]:
        """Validate config against schema definition."""
        errors: list[str] = []

        for field_name, field_spec in schema.items():
            required = field_spec.get("required", False)
            field_type = field_spec.get("type")
            min_val = field_spec.get("min")
            max_val = field_spec.get("max")

            if field_name not in config:
                if required:
                    errors.append(f"{prefix}.{field_name}: required field missing")
                continue

            value = config[field_name]

            # Type check
            if field_type == "int" and not isinstance(value, int):
                errors.append(f"{prefix}.{field_name}: expected int, got {type(value).__name__}")
            elif field_type == "float" and not isinstance(value, (int, float)):
                errors.append(f"{prefix}.{field_name}: expected float, got {type(value).__name__}")
            elif field_type == "str" and not isinstance(value, str):
                errors.append(f"{prefix}.{field_name}: expected str, got {type(value).__name__}")

            # Range check
            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    errors.append(f"{prefix}.{field_name}: {value} < min {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"{prefix}.{field_name}: {value} > max {max_val}")

        return errors

    @property
    def registered_substrates(self) -> list[str]:
        return sorted(self._schemas.keys())
