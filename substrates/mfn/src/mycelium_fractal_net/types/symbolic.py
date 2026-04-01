from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SymbolicContext:
    run_id: str
    simulation_spec: dict[str, Any] | None
    key_metrics: dict[str, float] = field(default_factory=dict)
    regime_labels: dict[str, str] = field(default_factory=dict)
    forecast_summary: dict[str, float | str] = field(default_factory=dict)
    compare_summary: dict[str, float | str] = field(default_factory=dict)
    manifest_hashes: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-symbolic-context-v1",
            "run_id": self.run_id,
            "simulation_spec": self.simulation_spec,
            "key_metrics": {str(k): float(v) for k, v in self.key_metrics.items()},
            "regime_labels": {str(k): str(v) for k, v in self.regime_labels.items()},
            "forecast_summary": {
                str(k): (float(v) if isinstance(v, (int, float)) else str(v))
                for k, v in self.forecast_summary.items()
            },
            "compare_summary": {
                str(k): (float(v) if isinstance(v, (int, float)) else str(v))
                for k, v in self.compare_summary.items()
            },
            "manifest_hashes": {str(k): str(v) for k, v in self.manifest_hashes.items()},
            "metadata": dict(self.metadata),
        }
