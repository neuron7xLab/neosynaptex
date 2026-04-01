"""Causal rule tracer — tracks activation of 46 rules across 7 stages.

Read-only: traces rule activations and their cascade effects
on gamma-scaling without modifying CausalGate state.

Ref: Vasylenko (2026), Granger (1969), Schreiber (2000) transfer entropy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.causal import CausalValidationResult

__all__ = ["CausalRuleTrace", "CausalTracer", "StageTransitionTrace"]

STAGES = (
    "simulate", "extract", "detect", "forecast",
    "compare", "cross-stage", "perturbation",
)


@dataclass
class CausalRuleTrace:
    """Trace of a single causal rule across simulation steps."""

    rule_id: str
    stage: str
    activations: list[bool]  # True = passed at each step
    trigger_features: list[str] = field(default_factory=list)
    downstream_effects: dict[str, float] = field(default_factory=dict)


@dataclass
class StageTransitionTrace:
    """Trace of pass rates across CausalGate stages."""

    stage_pass_rates: list[dict[str, float]]  # per-step: {stage: pass_rate}
    bottleneck_stage: str = ""
    entropy_profile: list[float] = field(default_factory=list)


class CausalTracer:
    """Trace 46 causal rule activations through 7 stages."""

    def trace_rules(
        self,
        causal_results: list[CausalValidationResult],
    ) -> dict[str, CausalRuleTrace]:
        """Trace each rule's activation across a sequence of validation results."""
        traces: dict[str, CausalRuleTrace] = {}

        for result in causal_results:
            for rule in result.rule_results:
                if rule.rule_id not in traces:
                    traces[rule.rule_id] = CausalRuleTrace(
                        rule_id=rule.rule_id,
                        stage=rule.stage,
                        activations=[],
                    )
                traces[rule.rule_id].activations.append(rule.passed)

        return traces

    def find_critical_rules(
        self,
        traces: dict[str, CausalRuleTrace],
        gamma_values: list[float],
        threshold: float = 0.1,
    ) -> list[str]:
        """Rules whose failure correlates with significant gamma changes.

        A rule is critical if |delta_gamma| > threshold when it fails.
        """
        if len(gamma_values) < 2:
            return []

        gamma_arr = np.array(gamma_values)
        d_gamma = np.abs(np.diff(gamma_arr))
        critical: list[str] = []

        for rule_id, trace in traces.items():
            acts = trace.activations
            n = min(len(acts) - 1, len(d_gamma))
            if n < 1:
                continue

            # Check if rule failures coincide with large gamma changes
            failure_dgamma = [
                d_gamma[i] for i in range(n) if not acts[i]
            ]
            if failure_dgamma and float(np.mean(failure_dgamma)) > threshold:
                critical.append(rule_id)

        return critical

    def trace_stage_transitions(
        self,
        causal_results: list[CausalValidationResult],
    ) -> StageTransitionTrace:
        """Analyze pass rates across 7 stages over time."""
        stage_rates: list[dict[str, float]] = []
        entropy_profile: list[float] = []

        for result in causal_results:
            rates: dict[str, float] = {}
            for stage in STAGES:
                stage_rules = [r for r in result.rule_results if r.stage == stage]
                if stage_rules:
                    rates[stage] = float(np.mean([r.passed for r in stage_rules]))
                else:
                    rates[stage] = 1.0
            stage_rates.append(rates)

            # Entropy of stage pass rates
            vals = np.array(list(rates.values()))
            vals_norm = vals / (np.sum(vals) + 1e-12)
            entropy = float(-np.sum(vals_norm * np.log(vals_norm + 1e-12)))
            entropy_profile.append(entropy)

        # Bottleneck: stage with lowest mean pass rate
        if stage_rates:
            mean_rates = {
                stage: float(np.mean([sr[stage] for sr in stage_rates]))
                for stage in STAGES
            }
            bottleneck = min(mean_rates, key=mean_rates.get)  # type: ignore[arg-type]
        else:
            bottleneck = ""

        return StageTransitionTrace(
            stage_pass_rates=stage_rates,
            bottleneck_stage=bottleneck,
            entropy_profile=entropy_profile,
        )

    def null_model_comparison(
        self,
        traces: dict[str, CausalRuleTrace],
        n_null: int = 1000,
        seed: int = 42,
    ) -> dict[str, float]:
        """p-value for each rule: is its activation pattern non-random?

        Permutation test: shuffle activations, compare failure rate.
        """
        rng = np.random.default_rng(seed)
        p_values: dict[str, float] = {}

        for rule_id, trace in traces.items():
            acts = np.array(trace.activations, dtype=float)
            if len(acts) < 5:
                p_values[rule_id] = 1.0
                continue

            observed_fail_rate = float(1.0 - np.mean(acts))

            null_fail_rates = []
            for _ in range(n_null):
                shuffled = rng.permutation(acts)
                null_fail_rates.append(float(1.0 - np.mean(shuffled)))

            p_values[rule_id] = max(
                float(np.mean(np.array(null_fail_rates) >= observed_fail_rate)),
                1.0 / n_null,
            )

        return p_values
