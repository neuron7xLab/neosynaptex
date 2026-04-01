"""Gamma diagnostics — mechanistic explanation of gamma deviation from +1.0.

Central component of the interpretability engine. Localizes gamma
deviations in the causal chain: thermodynamic -> topological -> fractal -> causal.

Scientific hypothesis:
  Healthy tissue: gamma ~ +1.0, attribution graph balanced.
  Pathological: gamma != 1.0, single feature group dominates.

Falsified if: gamma deviates but attribution balanced, OR
              gamma ~ 1.0 but attribution unbalanced.

Ref: Vasylenko (2026) gamma-scaling hypothesis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from .attribution_graph import AttributionGraph, AttributionGraphBuilder
from .causal_tracer import CausalTracer
from .feature_extractor import FeatureVector, MFNFeatureExtractor

if TYPE_CHECKING:
    from mycelium_fractal_net.types.causal import CausalValidationResult
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.thermodynamics import ThermodynamicStabilityReport

__all__ = ["GammaDiagnosticReport", "GammaDiagnostics"]

GammaStatus = Literal["healthy", "pathological_low", "pathological_high", "critical"]
DeviationOrigin = Literal[
    "thermodynamic", "topological", "fractal",
    "causal_rule", "stage_transition", "emergent",
]


@dataclass
class GammaDiagnosticReport:
    gamma_value: float
    gamma_status: GammaStatus
    deviation_origin: DeviationOrigin

    top_attributing_features: list[tuple[str, float]]
    critical_rule_ids: list[str]
    bottleneck_stage: str

    attribution_confidence: float  # [0, 1]
    null_model_p_value: float

    mechanistic_description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gamma_value": self.gamma_value,
            "gamma_status": self.gamma_status,
            "deviation_origin": self.deviation_origin,
            "top_features": self.top_attributing_features,
            "critical_rules": self.critical_rule_ids,
            "bottleneck_stage": self.bottleneck_stage,
            "confidence": self.attribution_confidence,
            "p_value": self.null_model_p_value,
            "description": self.mechanistic_description,
        }


class GammaDiagnostics:
    """Full diagnostic cycle for gamma-scaling hypothesis."""

    def __init__(
        self,
        extractor: MFNFeatureExtractor | None = None,
        graph_builder: AttributionGraphBuilder | None = None,
        tracer: CausalTracer | None = None,
    ) -> None:
        self.extractor = extractor or MFNFeatureExtractor()
        self.graph_builder = graph_builder or AttributionGraphBuilder()
        self.tracer = tracer or CausalTracer()

    def diagnose(
        self,
        sequences: list[FieldSequence],
        gamma_values: list[float],
        thermo_reports: list[ThermodynamicStabilityReport] | None = None,
        causal_results: list[CausalValidationResult] | None = None,
    ) -> GammaDiagnosticReport:
        """Full diagnostic cycle.

        1. Extract features for each snapshot
        2. Build attribution graph
        3. Trace causal rules
        4. Localize gamma deviation
        5. Generate mechanistic description
        """
        # 1. Extract features
        feature_vectors: list[FeatureVector] = []
        for i, seq in enumerate(sequences):
            fv = self.extractor.extract_all(
                seq,
                thermo_report=thermo_reports[i] if thermo_reports and i < len(thermo_reports) else None,
                causal_result=causal_results[i] if causal_results and i < len(causal_results) else None,
                step=i,
            )
            feature_vectors.append(fv)

        # 2. Build attribution graph
        graph = self.graph_builder.build(feature_vectors, gamma_values)

        # 3. Trace causal rules
        critical_rules: list[str] = []
        bottleneck = ""
        null_p = 1.0
        if causal_results:
            traces = self.tracer.trace_rules(causal_results)
            critical_rules = self.tracer.find_critical_rules(traces, gamma_values)
            stage_trace = self.tracer.trace_stage_transitions(causal_results)
            bottleneck = stage_trace.bottleneck_stage

            p_values = self.tracer.null_model_comparison(traces, n_null=200)
            [r for r, p in p_values.items() if p < 0.05]
            null_p = float(np.min(list(p_values.values()))) if p_values else 1.0

        # 4. Classify gamma status
        mean_gamma = float(np.mean(gamma_values)) if gamma_values else 0.0
        gamma_status = self._classify_gamma(mean_gamma)

        # 5. Localize deviation origin
        deviation_origin = self._localize_deviation(graph)

        # 6. Attribution confidence
        top = graph.top_contributors(5)
        top_weights = [abs(w) for _, w in top]
        confidence = float(np.mean(top_weights)) if top_weights else 0.0

        # 7. Mechanistic description
        description = self._generate_description(
            gamma_status, deviation_origin, top, critical_rules, bottleneck,
        )

        return GammaDiagnosticReport(
            gamma_value=mean_gamma,
            gamma_status=gamma_status,
            deviation_origin=deviation_origin,
            top_attributing_features=top,
            critical_rule_ids=critical_rules,
            bottleneck_stage=bottleneck,
            attribution_confidence=min(confidence, 1.0),
            null_model_p_value=null_p,
            mechanistic_description=description,
        )

    def _classify_gamma(self, gamma: float) -> GammaStatus:
        if 0.7 <= gamma <= 1.5:
            return "healthy"
        if gamma < 0:
            return "pathological_low"
        if gamma > 2.0:
            return "pathological_high"
        return "critical"

    def _localize_deviation(self, graph: AttributionGraph) -> DeviationOrigin:
        """Determine which feature group dominates the attribution."""
        group_scores: dict[str, float] = {}
        for name, weight in graph.gamma_attribution.items():
            group = name.split(".")[0] if "." in name else "unknown"
            group_scores[group] = group_scores.get(group, 0.0) + abs(weight)

        if not group_scores:
            return "emergent"

        dominant = max(group_scores, key=group_scores.get)  # type: ignore[arg-type]
        total = sum(group_scores.values())
        dominance = group_scores[dominant] / (total + 1e-12)

        if dominance < 0.35:
            return "emergent"

        mapping: dict[str, DeviationOrigin] = {
            "thermo": "thermodynamic",
            "topo": "topological",
            "fractal": "fractal",
            "causal": "causal_rule",
        }
        return mapping.get(dominant, "emergent")

    def _generate_description(
        self,
        status: str,
        origin: str,
        top_features: list[tuple[str, float]],
        critical_rules: list[str],
        bottleneck: str,
    ) -> str:
        parts: list[str] = []

        if status == "healthy":
            parts.append("Gamma is in the healthy range [0.7, 1.5].")
            parts.append("Attribution graph is balanced — no single mechanism dominates.")
        else:
            parts.append(f"Gamma deviation detected: status={status}.")
            parts.append(f"Primary deviation origin: {origin}.")

        if top_features:
            top_str = ", ".join(f"{n} ({w:+.3f})" for n, w in top_features[:3])
            parts.append(f"Top contributing features: {top_str}.")

        if critical_rules:
            parts.append(f"Critical causal rules: {', '.join(critical_rules[:3])}.")

        if bottleneck:
            parts.append(f"Bottleneck stage: {bottleneck}.")

        return " ".join(parts)
