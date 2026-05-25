"""Deterministic runtime deliberation with self-validation trace."""

from __future__ import annotations

from dataclasses import dataclass

from core.dre import DREDecision
from core.truth_guard import TruthGuardDecision
from core.value_gate import ValueGateDecision

__all__ = [
    "DeliberationConfig",
    "DeliberationStep",
    "DeliberationTrace",
    "build_deliberation_trace",
]


@dataclass(frozen=True)
class DeliberationConfig:
    max_steps: int = 3


@dataclass(frozen=True)
class DeliberationStep:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class DeliberationTrace:
    accepted: bool
    steps: tuple[DeliberationStep, ...]


def build_deliberation_trace(
    *,
    truth_guard: TruthGuardDecision,
    value_gate: ValueGateDecision,
    dre_decisions: tuple[DREDecision, ...],
    config: DeliberationConfig | None = None,
) -> DeliberationTrace:
    """Build deterministic decision trace from gate outcomes.

    The trace is bounded by ``max_steps`` and contains only validator outcomes.
    """
    cfg = config or DeliberationConfig()
    if cfg.max_steps < 1:
        raise ValueError("max_steps must be >= 1")

    steps: list[DeliberationStep] = []

    tg_pass = not truth_guard.activated
    steps.append(DeliberationStep("truth_guard", tg_pass, truth_guard.reason))

    vg_pass = value_gate.accepted
    steps.append(DeliberationStep("value_gate", vg_pass, value_gate.reason))

    dre_pass = bool(dre_decisions) and all(d.accepted for d in dre_decisions)
    dre_reason = "accepted" if dre_pass else "blocked:dre_gate"
    steps.append(DeliberationStep("dre", dre_pass, dre_reason))

    bounded = tuple(steps[: cfg.max_steps])
    accepted = all(step.passed for step in bounded)
    return DeliberationTrace(accepted=accepted, steps=bounded)
