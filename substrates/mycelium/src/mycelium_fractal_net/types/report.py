"""Canonical analysis report type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mycelium_fractal_net.types.symbolic import SymbolicContext

if TYPE_CHECKING:
    from mycelium_fractal_net.types.detection import AnomalyEvent
    from mycelium_fractal_net.types.features import MorphologyDescriptor
    from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec
    from mycelium_fractal_net.types.forecast import ComparisonResult, ForecastResult


@dataclass(frozen=True)
class AnalysisReport:
    run_id: str
    spec: SimulationSpec | None
    sequence: FieldSequence
    descriptor: MorphologyDescriptor
    detection: AnomalyEvent
    forecast: ForecastResult | None = None
    comparison: ComparisonResult | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "mfn-analysis-report-v1",
            "engine_version": "0.1.0",
            "run_id": self.run_id,
            "spec": None if self.spec is None else self.spec.to_dict(),
            "sequence": self.sequence.to_dict(include_arrays=False),
            "descriptor": self.descriptor.to_dict(),
            "detection": self.detection.to_dict(),
            "forecast": None if self.forecast is None else self.forecast.to_dict(),
            "comparison": (None if self.comparison is None else self.comparison.to_dict()),
            "artifacts": dict(self.artifacts),
            "metadata": dict(self.metadata),
        }

    def to_symbolic_context(self, manifest_hashes: dict[str, str] | None = None) -> SymbolicContext:
        summary = dict(self.metadata.get("summary", {}))
        forecast_summary = {}
        if self.forecast is not None:
            forecast_summary = {
                "method": self.forecast.method,
                "horizon": float(self.forecast.horizon),
                "forecast_structural_error": float(
                    self.forecast.benchmark_metrics.get("forecast_structural_error", 0.0)
                ),
                "adaptive_damping": float(
                    self.forecast.benchmark_metrics.get("adaptive_damping", 0.0)
                ),
            }
        compare_summary = {}
        if self.comparison is not None:
            compare_summary = {
                "label": self.comparison.label,
                "distance": float(self.comparison.distance),
                "cosine_similarity": float(self.comparison.cosine_similarity),
                "topology_label": self.comparison.topology_label,
            }
        return SymbolicContext(
            run_id=f"symbolic-{self.sequence.runtime_hash}",
            simulation_spec=None if self.spec is None else self.spec.to_dict(),
            key_metrics={
                "anomaly_score": float(self.detection.score),
                "field_mean_mV": float(
                    summary.get(
                        "field_mean_mV",
                        self.sequence.to_dict().get("field_mean_mV", 0.0),
                    )
                ),
                "field_std_mV": float(
                    summary.get("field_std_mV", self.sequence.to_dict().get("field_std_mV", 0.0))
                ),
            },
            regime_labels={
                "anomaly_label": self.detection.label,
                "regime_label": (self.detection.regime.label if self.detection.regime else "n/a"),
                "comparison_label": (
                    self.comparison.label if self.comparison is not None else "n/a"
                ),
            },
            forecast_summary=forecast_summary,  # type: ignore[arg-type]
            compare_summary=compare_summary,  # type: ignore[arg-type]
            manifest_hashes=dict(manifest_hashes or {}),
            metadata={
                "runtime_hash": self.sequence.runtime_hash,
                "history_included": False,
                "artifact_keys": sorted(self.artifacts),
            },
        )
