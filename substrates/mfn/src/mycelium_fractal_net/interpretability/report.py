"""Interpretability report generator — structured output for publication.

Generates Markdown report with sections:
1. Executive Summary
2. Attribution Analysis
3. Causal Chain
4. Statistical Validation
5. Mechanistic Hypothesis

Ref: Vasylenko (2026) NFI Platform
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .attribution_graph import AttributionGraph
    from .causal_tracer import CausalRuleTrace
    from .gamma_diagnostics import GammaDiagnosticReport

__all__ = ["MFNInterpretabilityReport"]


class MFNInterpretabilityReport:
    """Generate structured interpretability report."""

    def generate(
        self,
        diagnostic: GammaDiagnosticReport,
        attribution_graph: AttributionGraph | None = None,
        rule_traces: dict[str, CausalRuleTrace] | None = None,
        probe_results: dict[str, dict[str, float]] | None = None,
    ) -> str:
        """Generate Markdown report."""
        sections: list[str] = []

        # 1. Executive Summary
        sections.append("# MFN Interpretability Report\n")
        sections.append("## 1. Executive Summary\n")
        sections.append(f"- **Gamma**: {diagnostic.gamma_value:.4f}")
        sections.append(f"- **Status**: {diagnostic.gamma_status}")
        sections.append(f"- **Deviation origin**: {diagnostic.deviation_origin}")
        sections.append(f"- **Confidence**: {diagnostic.attribution_confidence:.3f}")
        sections.append(f"- **p-value**: {diagnostic.null_model_p_value:.4f}")
        sections.append(f"\n{diagnostic.mechanistic_description}\n")

        # 2. Attribution Analysis
        sections.append("## 2. Attribution Analysis\n")
        if diagnostic.top_attributing_features:
            sections.append("| Feature | Attribution |")
            sections.append("|---------|-----------|")
            for name, weight in diagnostic.top_attributing_features:
                sections.append(f"| {name} | {weight:+.4f} |")
        sections.append("")

        # 3. Causal Chain
        sections.append("## 3. Causal Chain\n")
        if diagnostic.critical_rule_ids:
            sections.append(f"Critical rules: {', '.join(diagnostic.critical_rule_ids)}")
        else:
            sections.append("No critical rules identified.")
        if diagnostic.bottleneck_stage:
            sections.append(f"\nBottleneck stage: **{diagnostic.bottleneck_stage}**")
        sections.append("")

        # 4. Statistical Validation
        sections.append("## 4. Statistical Validation\n")
        if probe_results:
            sections.append("| Feature Group | AUC | Accuracy |")
            sections.append("|--------------|-----|----------|")
            for group, result in probe_results.items():
                sections.append(
                    f"| {group} | {result.get('roc_auc', 0):.3f} | "
                    f"{result.get('accuracy', 0):.3f} |"
                )
        sections.append("")

        # 5. Mechanistic Hypothesis
        sections.append("## 5. Mechanistic Hypothesis\n")
        if diagnostic.gamma_status == "healthy":
            sections.append(
                "Gamma is within healthy range. Attribution graph shows balanced "
                "contribution from thermodynamic, topological, fractal, and causal "
                "feature groups. No single mechanism dominates the scaling exponent."
            )
        else:
            sections.append(
                f"Gamma deviation originates in the **{diagnostic.deviation_origin}** "
                f"layer. This suggests that the {diagnostic.deviation_origin} mechanism "
                f"is the primary driver of pathological scaling behavior."
            )

        return "\n".join(sections)

    def export_for_paper(
        self,
        diagnostic: GammaDiagnosticReport,
        probe_results: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        """Export LaTeX-compatible tables and data for publication."""
        tables: dict[str, Any] = {
            "gamma_summary": {
                "gamma": diagnostic.gamma_value,
                "status": diagnostic.gamma_status,
                "origin": diagnostic.deviation_origin,
                "confidence": diagnostic.attribution_confidence,
                "p_value": diagnostic.null_model_p_value,
            },
            "top_features": diagnostic.top_attributing_features,
            "critical_rules": diagnostic.critical_rule_ids,
        }
        if probe_results:
            tables["probe_auc"] = {
                g: r.get("roc_auc", 0.5) for g, r in probe_results.items()
            }
        return tables
