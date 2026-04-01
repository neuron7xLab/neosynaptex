"""Error budget tracking across pipeline stages.

Collects per-stage error contributions to identify bottlenecks
in the simulation→detection→forecast pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StageError:
    """Error contribution from a single pipeline stage."""

    stage: str
    metric: str
    value: float
    threshold: float
    fraction: float  # value / threshold — how much of the budget is consumed


@dataclass
class ErrorBudget:
    """Cumulative error budget across pipeline stages."""

    stages: list[StageError] = field(default_factory=list)
    total_fraction: float = 0.0
    budget_threshold: float = 1.0

    @property
    def within_budget(self) -> bool:
        return self.total_fraction <= self.budget_threshold

    @property
    def top_contributors(self) -> list[StageError]:
        return sorted(self.stages, key=lambda s: s.fraction, reverse=True)[:3]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_fraction": round(self.total_fraction, 4),
            "within_budget": self.within_budget,
            "budget_threshold": self.budget_threshold,
            "top_contributors": [
                {"stage": s.stage, "metric": s.metric, "fraction": round(s.fraction, 4)}
                for s in self.top_contributors
            ],
            "stages": [
                {
                    "stage": s.stage,
                    "metric": s.metric,
                    "value": round(s.value, 6),
                    "threshold": s.threshold,
                    "fraction": round(s.fraction, 4),
                }
                for s in self.stages
            ],
        }


def compute_error_budget(
    sequence: Any,
    descriptor: Any | None = None,
    forecast: Any | None = None,
) -> ErrorBudget:
    """Compute cumulative error budget from pipeline stage metrics.

    Parameters
    ----------
    sequence:
        FieldSequence with simulation metadata.
    descriptor:
        MorphologyDescriptor (optional).
    forecast:
        ForecastResult (optional).

    Returns
    -------
    ErrorBudget
        Per-stage error fractions and total.
    """
    stages: list[StageError] = []

    # Simulation: clamping events / total cells
    total_cells = sequence.field.size
    clamp_events = int(sequence.metadata.get("clamping_events", 0))
    steps = max(1, int(sequence.metadata.get("steps_computed", 1)))
    clamp_fraction = clamp_events / (total_cells * steps) if total_cells > 0 else 0.0
    stages.append(
        StageError(
            stage="simulate",
            metric="clamping_rate",
            value=clamp_fraction,
            threshold=0.05,
            fraction=clamp_fraction / 0.05,
        )
    )

    # Simulation: occupancy mass error
    occ_error = float(sequence.metadata.get("occupancy_mass_error_max", 0.0))
    stages.append(
        StageError(
            stage="simulate",
            metric="occupancy_mass_error",
            value=occ_error,
            threshold=1e-4,
            fraction=occ_error / 1e-4 if occ_error > 0 else 0.0,
        )
    )

    # Simulation: field range utilization
    field_range = float(np.max(sequence.field) - np.min(sequence.field))
    max_range = 0.135  # -95mV to +40mV = 135mV = 0.135V
    range_frac = field_range / max_range if max_range > 0 else 0.0
    stages.append(
        StageError(
            stage="simulate",
            metric="field_range_utilization",
            value=range_frac,
            threshold=1.0,
            fraction=range_frac,
        )
    )

    # Extraction: D_r2 quality (inverted — low R² = high error)
    if descriptor is not None:
        d_r2 = descriptor.features.get("D_r2", 1.0)
        r2_error = 1.0 - d_r2
        stages.append(
            StageError(
                stage="extract",
                metric="fractal_regression_error",
                value=r2_error,
                threshold=0.3,
                fraction=r2_error / 0.3 if r2_error > 0 else 0.0,
            )
        )

    # Forecast: structural error
    if forecast is not None:
        fd = forecast.to_dict()
        se = fd.get("benchmark_metrics", {}).get("forecast_structural_error", 0.0)
        stages.append(
            StageError(
                stage="forecast",
                metric="structural_error",
                value=se,
                threshold=0.2,
                fraction=se / 0.2 if se > 0 else 0.0,
            )
        )

    total = sum(s.fraction for s in stages) / max(1, len(stages))
    return ErrorBudget(stages=stages, total_fraction=total)
