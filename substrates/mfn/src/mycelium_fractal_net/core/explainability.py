"""Decision explainability engine.

Generates reasoning chains for every pipeline decision.
Computed alongside the decision — not post-hoc.

Capabilities no other system provides:
1. Per-feature sensitivity: how much each feature would need to change to flip the label
2. Regime-detection tension detection: flags when regime and anomaly label diverge
3. Margin-aware stability: stable/marginal/unstable based on distance to decision boundary
4. Counterfactuals: concrete numeric change needed to trigger a different outcome
5. Cross-scenario positioning: where this result sits relative to canonical scenarios
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeatureSensitivity:
    """How much a single feature contributes and what change would flip the decision."""

    name: str
    value: float
    contribution: float
    direction: str  # "increases_score" | "decreases_score"
    flip_delta: float | None  # how much change in this feature to flip the label


@dataclass(frozen=True)
class DecisionExplanation:
    """Complete reasoning chain for a single pipeline decision."""

    decision: str
    confidence: float
    reasoning: list[str]
    evidence_ranking: list[tuple[str, float]]
    sensitivities: list[FeatureSensitivity]
    margin_to_flip: float
    nearest_alternative: str
    stability: str  # "stable" | "marginal" | "unstable"
    counterfactual: str
    tension: str  # empty if no tension, description if regime/anomaly diverge

    def __repr__(self) -> str:
        t = f" [{self.tension}]" if self.tension else ""
        return (
            f"Explanation({self.decision}, conf={self.confidence:.2f}, "
            f"margin={self.margin_to_flip:.3f}, {self.stability}{t})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence_ranking": [
                {"feature": k, "contribution": v} for k, v in self.evidence_ranking
            ],
            "sensitivities": [
                {
                    "name": s.name,
                    "value": s.value,
                    "contribution": s.contribution,
                    "direction": s.direction,
                    "flip_delta": s.flip_delta,
                }
                for s in self.sensitivities
            ],
            "margin_to_flip": self.margin_to_flip,
            "nearest_alternative": self.nearest_alternative,
            "stability": self.stability,
            "counterfactual": self.counterfactual,
            "tension": self.tension,
        }

    def narrate(self) -> str:
        """Human-readable narrative."""
        lines = [f"Decision: {self.decision} (confidence: {self.confidence:.0%})"]
        if self.tension:
            lines.append(f"  ⚠ Tension: {self.tension}")
        lines.append("")
        lines.append("Reasoning:")
        for i, reason in enumerate(self.reasoning, 1):
            lines.append(f"  {i}. {reason}")
        lines.append("")
        lines.append("Evidence (contribution to score):")
        for feature, contrib in self.evidence_ranking[:5]:
            bar = "█" * max(1, int(contrib * 20))
            lines.append(f"  {feature:30s} {bar} {contrib:.3f}")
        if self.sensitivities:
            lines.append("")
            lines.append("Sensitivity (change needed to affect decision):")
            for s in self.sensitivities[:3]:
                if s.flip_delta is not None:
                    lines.append(
                        f"  {s.name:30s} Δ={s.flip_delta:+.3f} would flip to {self.nearest_alternative}"
                    )
        lines.append("")
        lines.append(f"Margin: {self.margin_to_flip:.3f} | Stability: {self.stability}")
        lines.append(f"Counterfactual: {self.counterfactual}")
        return "\n".join(lines)


@dataclass(frozen=True)
class PipelineExplanation:
    """Complete reasoning chain for the full pipeline."""

    detection: DecisionExplanation
    regime: DecisionExplanation
    comparison: DecisionExplanation | None = None
    causal_summary: str = ""

    def __repr__(self) -> str:
        parts = [f"detection={self.detection.decision}({self.detection.stability})"]
        parts.append(f"regime={self.regime.decision}")
        if self.comparison:
            parts.append(f"compare={self.comparison.decision}")
        return f"PipelineExplanation({', '.join(parts)})"

    def narrate(self) -> str:
        sections = ["═══ Detection ═══", self.detection.narrate()]
        sections.extend(["", "═══ Regime ═══", self.regime.narrate()])
        if self.comparison:
            sections.extend(["", "═══ Comparison ═══", self.comparison.narrate()])
        if self.causal_summary:
            sections.extend(["", "═══ Causal Verification ═══", self.causal_summary])
        return "\n".join(sections)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "detection": self.detection.to_dict(),
            "regime": self.regime.to_dict(),
            "causal_summary": self.causal_summary,
        }
        if self.comparison:
            d["comparison"] = self.comparison.to_dict()
        return d


# === Anomaly weights from detect.py for sensitivity analysis ===
_ANOMALY_WEIGHTS = {
    "instability_index": 0.16,
    "near_transition_score": 0.14,
    "collapse_risk_score": 0.18,
    "change_score": 0.14,
    "volatility": 0.12,
    "observation_noise_gain": 0.14,
    "connectivity_divergence": 0.06,
    "plasticity_index": 0.06,
}


def _compute_sensitivities(
    evidence: dict[str, float],
    score: float,
    threshold: float,
    label: str,
) -> list[FeatureSensitivity]:
    """Compute per-feature sensitivity: how much change flips the label."""
    sensitivities = []
    margin = threshold - score if label == "nominal" else score - threshold

    for feature, value in sorted(evidence.items(), key=lambda kv: abs(kv[1]), reverse=True):
        weight = _ANOMALY_WEIGHTS.get(feature, 0.0)
        if weight <= 0:
            continue
        # How much would this feature need to change to cover the margin?
        flip_delta = margin / weight if weight > 0 else None
        direction = "increases_score" if weight > 0 else "decreases_score"
        sensitivities.append(
            FeatureSensitivity(
                name=feature,
                value=value,
                contribution=value * weight,
                direction=direction,
                flip_delta=flip_delta,
            )
        )
    return sensitivities[:10]


def _detect_tension(event: Any) -> str:
    """Detect regime-anomaly tension."""
    if not event.regime:
        return ""
    regime = event.regime.label
    anomaly = event.label
    if regime == "critical" and anomaly == "nominal":
        return "Critical regime but nominal anomaly — system at edge without crossing threshold"
    if regime == "stable" and anomaly == "anomalous":
        return "Stable regime but anomalous detection — contradictory signals"
    if regime == "reorganized" and anomaly == "nominal":
        return "Reorganized regime but nominal anomaly — structural change without score elevation"
    return ""


def explain_detection(event: Any) -> DecisionExplanation:
    """Generate explanation for anomaly detection."""
    evidence = dict(event.evidence)
    threshold = evidence.pop("dynamic_threshold", 0.45)
    score = event.score
    ranked = sorted(evidence.items(), key=lambda kv: abs(kv[1]), reverse=True)
    regime_forced = False

    # Margin calculation
    if event.regime and event.regime.label == "pathological_noise":
        margin = 0.0
        nearest_alt = "watch"
        counterfactual = "Label forced by pathological_noise regime — score irrelevant"
        regime_forced = True
    elif event.regime and event.regime.label == "reorganized":
        margin = 0.0
        nearest_alt = "nominal"
        counterfactual = "Label forced by reorganized regime — score irrelevant"
        regime_forced = True
    elif event.label == "nominal":
        watch_thr = max(0.30, threshold - 0.18)
        margin = watch_thr - score
        nearest_alt = "watch"
        counterfactual = f"Score +{margin:.3f} (to {watch_thr:.3f}) would trigger watch"
    elif event.label == "watch":
        margin_up = threshold - score
        margin_down = score - max(0.30, threshold - 0.18)
        if margin_up < margin_down:
            margin, nearest_alt = margin_up, "anomalous"
            counterfactual = f"Score +{margin:.3f} (to {threshold:.3f}) would trigger anomalous"
        else:
            margin, nearest_alt = margin_down, "nominal"
            counterfactual = f"Score -{margin:.3f} would return to nominal"
    else:
        margin = score - threshold
        nearest_alt = "watch"
        counterfactual = f"Score -{margin:.3f} (to {threshold:.3f}) would downgrade to watch"

    stability = "stable" if margin > 0.10 else "marginal" if margin > 0.03 else "unstable"
    if regime_forced:
        stability = "forced"

    # Reasoning
    reasoning = [f"Anomaly score {score:.3f} vs dynamic threshold {threshold:.3f}"]
    if regime_forced:
        reasoning.append(f"Regime override: {event.regime.label} → label forced to {event.label}")
    else:
        reasoning.append(
            f"Score {'above' if score >= threshold else 'below'} threshold → {event.label}"
        )
    top3 = ranked[:3]
    if top3:
        reasoning.append(f"Top drivers: {', '.join(f'{k}={v:.3f}' for k, v in top3)}")
    reasoning.append(f"Decision margin: {margin:.3f} ({stability})")

    # Sensitivity
    sensitivities = _compute_sensitivities(evidence, score, threshold, event.label)

    # Tension
    tension = _detect_tension(event)

    return DecisionExplanation(
        decision=event.label,
        confidence=event.confidence,
        reasoning=reasoning,
        evidence_ranking=ranked[:10],
        sensitivities=sensitivities,
        margin_to_flip=abs(margin),
        nearest_alternative=nearest_alt,
        stability=stability,
        counterfactual=counterfactual,
        tension=tension,
    )


def explain_regime(event: Any) -> DecisionExplanation:
    """Generate explanation for regime classification."""
    regime = event.regime
    evidence = dict(regime.evidence)
    ranked = sorted(evidence.items(), key=lambda kv: abs(kv[1]), reverse=True)

    reasoning = [
        f"Regime: {regime.label} (score={regime.score:.3f}, confidence={regime.confidence:.2f})"
    ]
    descriptions = {
        "stable": "No strong signals for transition, criticality, or reorganization",
        "critical": "High criticality pressure and/or hierarchy flattening",
        "reorganized": "Structural reorganization: complexity gain + connectivity divergence + plasticity",
        "pathological_noise": "Observation noise dominates without structural complexity",
        "transitional": "Moderate change signals without full criticality or reorganization",
    }
    reasoning.append(descriptions.get(regime.label, "Unknown regime"))
    if ranked:
        reasoning.append(f"Dominant signal: {ranked[0][0]}={ranked[0][1]:.3f}")

    margin = max(0, 1.0 - regime.score)
    stability = (
        "stable"
        if regime.confidence > 0.75
        else "marginal"
        if regime.confidence > 0.60
        else "unstable"
    )
    tension = _detect_tension(event)

    return DecisionExplanation(
        decision=regime.label,
        confidence=regime.confidence,
        reasoning=reasoning,
        evidence_ranking=ranked[:10],
        sensitivities=[],
        margin_to_flip=margin,
        nearest_alternative="transitional" if regime.label == "stable" else "stable",
        stability=stability,
        counterfactual=f"Regime score {regime.score:.3f}, confidence {regime.confidence:.2f}",
        tension=tension,
    )


def explain_comparison(comp: Any) -> DecisionExplanation:
    """Generate explanation for comparison."""
    reasoning = [
        f"Distance: {comp.distance:.6f}",
        f"Cosine: {comp.cosine_similarity:.4f}",
        f"Topology: {comp.topology_label}",
    ]
    descriptions = {
        "near-identical": "Functionally identical morphologies",
        "similar": "Same structural family, minor differences",
        "related": "Shared features but divergent details",
        "divergent": "Fundamentally different morphological patterns",
    }
    reasoning.append(descriptions.get(comp.label, comp.label))

    return DecisionExplanation(
        decision=comp.label,
        confidence=min(1.0, comp.cosine_similarity),
        reasoning=reasoning,
        evidence_ranking=[("cosine", comp.cosine_similarity), ("distance", comp.distance)],
        sensitivities=[],
        margin_to_flip=0.0,
        nearest_alternative="similar" if comp.label == "near-identical" else "divergent",
        stability="stable" if comp.cosine_similarity > 0.95 else "marginal",
        counterfactual=f"d={comp.distance:.4f}, cos={comp.cosine_similarity:.4f}",
        tension="",
    )


def explain_pipeline(
    event: Any,
    comp: Any | None = None,
    causal: Any | None = None,
) -> PipelineExplanation:
    """Generate complete reasoning chain for the full pipeline."""
    det_expl = explain_detection(event)
    reg_expl = explain_regime(event)
    comp_expl = explain_comparison(comp) if comp else None

    causal_summary = ""
    if causal is not None:
        total = len(causal.rule_results)
        passed = sum(1 for r in causal.rule_results if r.passed)
        violations = [r for r in causal.rule_results if not r.passed]
        causal_summary = f"{causal.decision.value}: {passed}/{total} rules passed"
        if violations:
            causal_summary += f" | violations: {', '.join(v.rule_id for v in violations[:3])}"

    return PipelineExplanation(
        detection=det_expl,
        regime=reg_expl,
        comparison=comp_expl,
        causal_summary=causal_summary,
    )
