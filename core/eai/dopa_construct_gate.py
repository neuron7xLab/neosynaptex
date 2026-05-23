from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


CheckFn = Callable[[], bool]


@dataclass(frozen=True)
class ConstructContext:
    dnca_substrate_check: bool | CheckFn
    dopamine_mechanism_check: bool | CheckFn
    sklearn_proxy_only_check: bool | CheckFn
    closure_metric_accuracy_only_check: bool | CheckFn
    trivial_baselines_check: bool | CheckFn
    negative_controls_check: bool | CheckFn


@dataclass(frozen=True)
class ConstructVerdict:
    admissible: bool
    verdict: str
    reasons: list[str]


def _resolve(flag_or_fn: bool | CheckFn) -> bool:
    return flag_or_fn() if callable(flag_or_fn) else bool(flag_or_fn)


def validate_construct_context(ctx: ConstructContext) -> ConstructVerdict:
    dnca = _resolve(ctx.dnca_substrate_check)
    dopamine = _resolve(ctx.dopamine_mechanism_check)
    sklearn_proxy_only = _resolve(ctx.sklearn_proxy_only_check)
    accuracy_only = _resolve(ctx.closure_metric_accuracy_only_check)
    trivial_ok = _resolve(ctx.trivial_baselines_check)
    controls_ok = _resolve(ctx.negative_controls_check)

    reasons: list[str] = []
    if not dnca:
        reasons.append("dnca_substrate_missing")
    if not dopamine:
        reasons.append("dopamine_mechanism_not_implemented")
    if sklearn_proxy_only:
        reasons.append("sklearn_proxy_forbidden")
    if accuracy_only:
        reasons.append("accuracy_only_metric_forbidden")
    if not trivial_ok:
        reasons.append("trivial_baselines_missing")
    if not controls_ok:
        reasons.append("negative_controls_not_executable")
    if reasons:
        return ConstructVerdict(False, "INSTRUMENT_INADMISSIBLE", reasons)
    return ConstructVerdict(True, "ADMISSIBLE", ["construct_gate_passed"])
