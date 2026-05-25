"""Operational integration layer for DRE + TruthGuard.

Single-call API for production loops.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from core.deliberation import DeliberationTrace, build_deliberation_trace
from core.dre import ConstitutionInvariant, DREConfig, DREDecision, DREInput, DREState, run_dre_loop
from core.event_bus import EventBus
from core.truth_guard import TruthGuardConfig, TruthGuardDecision, evaluate_truth_guard
from core.value_gate import ValueGateConfig, ValueGateDecision, ValueGateInput, evaluate_value_gate

__all__ = ["IntegratedCycleResult", "run_integrated_cycle"]


@dataclass(frozen=True)
class IntegratedCycleResult:
    truth_guard: TruthGuardDecision
    value_gate: ValueGateDecision
    dre_decisions: tuple[DREDecision, ...]
    dre_state: DREState
    deliberation: DeliberationTrace


def run_integrated_cycle(
    *,
    baseline: float,
    observed: float,
    confidence: float,
    dre_events: tuple[DREInput, ...],
    dre_config: DREConfig,
    invariant: ConstitutionInvariant,
    truth_guard_config: TruthGuardConfig | None = None,
    event_bus: EventBus | None = None,
    start_day_index: int = 0,
    value_gate_input: ValueGateInput | None = None,
    value_gate_config: ValueGateConfig | None = None,
) -> IntegratedCycleResult:
    """Run truth pre-gate + DRE in a deterministic integrated cycle.

    If truth guard activates, all DRE events are skipped (fail-closed pause).
    """
    truth_guard_config = truth_guard_config or TruthGuardConfig()
    value_gate_config = value_gate_config or ValueGateConfig()

    tg = evaluate_truth_guard(
        baseline=baseline,
        observed=observed,
        confidence=confidence,
        config=truth_guard_config,
        event_bus=event_bus,
    )
    if tg.activated:
        vg_block = ValueGateDecision(False, float("-inf"), "blocked:truth_guard")
        return IntegratedCycleResult(
            truth_guard=tg,
            value_gate=vg_block,
            dre_decisions=(),
            dre_state=DREState(
                day_index=start_day_index,
                ktb=(),
                phase_transition_triggered=False,
            ),
            deliberation=build_deliberation_trace(
                truth_guard=tg,
                value_gate=vg_block,
                dre_decisions=(),
            ),
        )

    vg_inp = value_gate_input or ValueGateInput(
        utility=1.0,
        risk=0.0,
        uncertainty=0.0,
        kl_drift=0.0,
        counterfactual_score=-1.0,
    )
    vg = evaluate_value_gate(vg_inp, value_gate_config)
    if not vg.accepted:
        return IntegratedCycleResult(
            truth_guard=tg,
            value_gate=vg,
            dre_decisions=(),
            dre_state=DREState(day_index=start_day_index, ktb=(), phase_transition_triggered=False),
            deliberation=build_deliberation_trace(
                truth_guard=tg,
                value_gate=vg,
                dre_decisions=(),
            ),
        )

    decisions, state = asyncio.run(
        run_dre_loop(
            dre_events,
            config=dre_config,
            invariant=invariant,
            start_day_index=start_day_index,
        )
    )
    dre_tuple = tuple(decisions)
    return IntegratedCycleResult(
        truth_guard=tg,
        value_gate=vg,
        dre_decisions=dre_tuple,
        dre_state=state,
        deliberation=build_deliberation_trace(
            truth_guard=tg,
            value_gate=vg,
            dre_decisions=dre_tuple,
        ),
    )
