"""Explanation Trace — machine-readable decision audit trail.

Every detection, forecast, and causal decision is fully traceable
back to source features, thresholds, and decision paths.

Usage:
    trace = build_explanation_trace(seq, det, desc, fc, cmp, causal)
    trace.to_json("explanation_trace.json")
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DetectionTrace:
    """Trace of every decision in the detection pipeline."""

    source_features: dict[str, float] = field(default_factory=dict)
    normalized_values: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    decision_path: list[str] = field(default_factory=list)
    triggered_rules: list[str] = field(default_factory=list)
    final_score: float = 0.0
    final_label: str = "unknown"
    regime_label: str = "unknown"
    confidence: float = 0.0
    margin_to_flip: float = 0.0
    contributing_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForecastTrace:
    """Trace of forecast computation."""

    input_features: dict[str, float] = field(default_factory=dict)
    horizon: int = 0
    uncertainty_components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComparisonTrace:
    """Trace of comparison computation."""

    left_features: dict[str, float] = field(default_factory=dict)
    right_features: dict[str, float] = field(default_factory=dict)
    distance: float = 0.0
    cosine_similarity: float = 0.0
    label: str = "unknown"
    changed_dimensions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CausalTrace:
    """Trace of causal validation gate."""

    rules_evaluated: int = 0
    rules_passed: int = 0
    rules_failed: list[dict[str, Any]] = field(default_factory=list)
    rules_warned: list[dict[str, Any]] = field(default_factory=list)
    decision: str = "unknown"
    mode: str = "strict"
    provenance_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExplanationTrace:
    """Complete machine-readable trace of all pipeline decisions."""

    schema_version: str = "mfn-explanation-trace-v1"
    detection_trace: DetectionTrace | None = None
    forecast_trace: ForecastTrace | None = None
    comparison_trace: ComparisonTrace | None = None
    causal_trace: CausalTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "detection": self.detection_trace.to_dict() if self.detection_trace else None,
            "forecast": self.forecast_trace.to_dict() if self.forecast_trace else None,
            "comparison": self.comparison_trace.to_dict() if self.comparison_trace else None,
            "causal": self.causal_trace.to_dict() if self.causal_trace else None,
        }

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))


def build_explanation_trace(
    detection: Any = None,
    descriptor: Any = None,
    forecast: Any = None,
    comparison: Any = None,
    causal: Any = None,
) -> ExplanationTrace:
    """Build a complete explanation trace from pipeline outputs.

    All arguments are optional — the trace includes only available sections.
    """
    det_trace = None
    if detection is not None:
        # Extract detection decision path
        from mycelium_fractal_net.core.detection_config import (
            DYNAMIC_ANOMALY_BASELINE,
            STABLE_CEILING,
            THRESHOLD_CEILING,
            THRESHOLD_FLOOR,
            WATCH_THRESHOLD_FLOOR,
        )

        thresholds = {
            "anomaly_baseline": DYNAMIC_ANOMALY_BASELINE,
            "stable_ceiling": STABLE_CEILING,
            "threshold_floor": THRESHOLD_FLOOR,
            "threshold_ceiling": THRESHOLD_CEILING,
            "watch_floor": WATCH_THRESHOLD_FLOOR,
        }

        decision_path = []
        score = detection.score
        label = detection.label

        if score < THRESHOLD_FLOOR:
            decision_path.append(f"score {score:.4f} < threshold_floor {THRESHOLD_FLOOR} → nominal")
        elif score < WATCH_THRESHOLD_FLOOR:
            decision_path.append(
                f"score {score:.4f} < watch_floor {WATCH_THRESHOLD_FLOOR} → nominal/watch boundary"
            )
        elif score >= THRESHOLD_CEILING:
            decision_path.append(
                f"score {score:.4f} >= threshold_ceiling {THRESHOLD_CEILING} → anomalous"
            )
        else:
            decision_path.append(f"score {score:.4f} in middle range → {label}")

        regime_label = detection.regime.label if detection.regime else "none"
        decision_path.append(f"regime={regime_label}")

        # Margin to flip
        if label == "nominal":
            margin = THRESHOLD_FLOOR - score
        elif label == "anomalous":
            margin = score - THRESHOLD_CEILING
        else:
            margin = min(abs(score - THRESHOLD_FLOOR), abs(score - THRESHOLD_CEILING))

        det_trace = DetectionTrace(
            source_features=dict(detection.evidence) if hasattr(detection, "evidence") else {},
            thresholds=thresholds,
            decision_path=decision_path,
            triggered_rules=[],
            final_score=score,
            final_label=label,
            regime_label=regime_label,
            confidence=detection.confidence,
            margin_to_flip=abs(margin),
            contributing_features=list(detection.contributing_features)
            if hasattr(detection, "contributing_features")
            else [],
        )

    fc_trace = None
    if forecast is not None:
        fc_trace = ForecastTrace(
            input_features={},
            horizon=forecast.horizon,
            uncertainty_components=forecast.uncertainty.to_dict()
            if hasattr(forecast, "uncertainty") and forecast.uncertainty
            else {},
        )

    cmp_trace = None
    if comparison is not None:
        cmp_trace = ComparisonTrace(
            distance=comparison.distance,
            cosine_similarity=comparison.cosine_similarity,
            label=comparison.label,
        )

    causal_trace = None
    if causal is not None:
        failed = [
            {
                "rule_id": r.rule_id,
                "severity": r.severity.value,
                "observed": str(r.observed),
                "expected": str(r.expected),
            }
            for r in causal.rule_results
            if not r.passed and r.severity.value in ("error", "fatal")
        ]
        warned = [
            {"rule_id": r.rule_id, "observed": str(r.observed)}
            for r in causal.rule_results
            if not r.passed and r.severity.value == "warn"
        ]
        causal_trace = CausalTrace(
            rules_evaluated=len(causal.rule_results),
            rules_passed=sum(1 for r in causal.rule_results if r.passed),
            rules_failed=failed,
            rules_warned=warned,
            decision=causal.decision.value,
            provenance_hash=causal.provenance_hash if hasattr(causal, "provenance_hash") else "",
        )

    return ExplanationTrace(
        detection_trace=det_trace,
        forecast_trace=fc_trace,
        comparison_trace=cmp_trace,
        causal_trace=causal_trace,
    )
