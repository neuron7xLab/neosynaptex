from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConstructContext:
    dnca_substrate_declared: bool
    dopamine_mechanism_implemented: bool
    sklearn_proxy_only: bool
    closure_metric_accuracy_only: bool
    trivial_baselines_available: bool
    negative_controls_executable: bool


@dataclass(frozen=True)
class ConstructVerdict:
    admissible: bool
    verdict: str
    reasons: list[str]


def validate_construct_context(ctx: ConstructContext) -> ConstructVerdict:
    reasons: list[str] = []
    if not ctx.dnca_substrate_declared:
        reasons.append("dnca_substrate_missing")
    if not ctx.dopamine_mechanism_implemented:
        reasons.append("dopamine_mechanism_not_implemented")
    if ctx.sklearn_proxy_only:
        reasons.append("sklearn_proxy_forbidden")
    if ctx.closure_metric_accuracy_only:
        reasons.append("accuracy_only_metric_forbidden")
    if not ctx.trivial_baselines_available:
        reasons.append("trivial_baselines_missing")
    if not ctx.negative_controls_executable:
        reasons.append("negative_controls_not_executable")

    if reasons:
        return ConstructVerdict(False, "INSTRUMENT_INADMISSIBLE", reasons)
    return ConstructVerdict(True, "ADMISSIBLE", ["construct_gate_passed"])
