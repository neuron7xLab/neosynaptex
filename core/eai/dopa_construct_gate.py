from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable


class ContextContaminationError(ValueError):
    """Raised when construct context shape/signature is not trusted."""


CheckFn = Callable[[], bool]


@dataclass(frozen=True, slots=True)
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


_REQUIRED_FIELDS = (
    "dnca_substrate_check",
    "dopamine_mechanism_check",
    "sklearn_proxy_only_check",
    "closure_metric_accuracy_only_check",
    "trivial_baselines_check",
    "negative_controls_check",
)
_EXPECTED_SIGNATURE = sha256("|".join(_REQUIRED_FIELDS).encode("utf-8")).hexdigest()


def _resolve(flag_or_fn: bool | CheckFn) -> bool:
    return flag_or_fn() if callable(flag_or_fn) else bool(flag_or_fn)


def _assert_context_integrity(ctx: ConstructContext) -> None:
    slots = getattr(ctx, "__slots__", ())
    if tuple(slots) != _REQUIRED_FIELDS:
        raise ContextContaminationError("context_slots_mismatch")
    got = sha256("|".join(slots).encode("utf-8")).hexdigest()
    if got != _EXPECTED_SIGNATURE:
        raise ContextContaminationError("context_signature_mismatch")


def validate_construct_context(ctx: ConstructContext) -> ConstructVerdict:
    try:
        _assert_context_integrity(ctx)
    except ContextContaminationError as exc:
        return ConstructVerdict(False, "INSTRUMENT_INADMISSIBLE", [str(exc)])

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
