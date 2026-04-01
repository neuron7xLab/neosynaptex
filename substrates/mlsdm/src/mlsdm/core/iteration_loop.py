from __future__ import annotations

import json
from collections import deque
from collections.abc import (  # noqa: TC003 - needed at runtime for type guard in _to_vector
    Iterable,
    Sequence,
)
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from mlsdm.protocols.neuro_signals import (
    ActionGatingSignal,
    RewardPredictionErrorSignal,
    RiskSignal,
    StabilityMetrics,
)

if TYPE_CHECKING:
    import pathlib


class Regime(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    DEFENSIVE = "defensive"


GUARD_WINDOW = 10
MAX_ABS_DELTA = 1.5
MAX_SIGN_FLIP_RATE = 0.6
MAX_REGIME_FLIP_RATE = 0.5
COOLDOWN_STEPS = 2


@dataclass
class IterationContext:
    dt: float
    timestamp: float
    seed: int
    threat: float = 0.0
    risk: float = 0.0
    regime: Regime = Regime.NORMAL
    mode: str | None = None


@dataclass
class PredictionBundle:
    predicted_outcome: list[float]
    predicted_value: float | None = None
    predicted_uncertainty: float | None = None


@dataclass
class ObservationBundle:
    observed_outcome: list[float]
    reward: float | None = None
    terminal: bool = False


@dataclass
class PredictionError:
    delta: list[float]
    abs_delta: float
    clipped_delta: list[float]
    components: list[float] = field(default_factory=list)


@dataclass
class ActionProposal:
    action_id: str
    action_payload: Any
    scores: list[float] | None = None
    confidence: float | None = None


@dataclass
class UpdateResult:
    parameter_deltas: dict[str, float]
    bounded: bool
    applied: bool


@dataclass
class SafetyDecision:
    allow_next: bool
    reason: str
    stability_metrics: dict[str, Any]
    risk_metrics: dict[str, float]
    regime: Regime


@dataclass
class IterationState:
    parameter: float = 0.0
    regime: Regime = Regime.NORMAL
    learning_rate: float = 0.1
    last_effective_lr: float = 0.0
    inhibition_gain: float = 1.0
    tau: float = 1.0
    cooldown_steps: int = 0
    kill_switch_active: bool = field(default=False, init=False)
    cooldown_remaining: int = field(default=0, init=False)
    instability_events_count: int = field(default=0, init=False)
    time_to_kill_switch: int | None = field(default=None, init=False)
    recovered: bool = field(default=False, init=False)
    last_delta: float = 0.0
    steps: int = 0
    frozen: bool = False
    delta_signs: deque[int] = field(default_factory=lambda: deque(maxlen=GUARD_WINDOW))
    regime_flips_window: deque[int] = field(default_factory=lambda: deque(maxlen=GUARD_WINDOW))
    recent_abs_deltas: deque[float] = field(default_factory=lambda: deque(maxlen=GUARD_WINDOW))
    max_abs_delta: float = 0.0
    last_envelope_metrics: dict[str, float] = field(default_factory=dict)


class EnvironmentAdapter(Protocol):
    def reset(self, seed: int | None = None) -> ObservationBundle: ...

    def step(self, action_payload: Any) -> ObservationBundle: ...


def _to_vector(value: float | Sequence[float]) -> list[float]:
    if not isinstance(value, (int, float)):
        return [float(v) for v in value]
    return [float(value)]


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _sign_flip_rate(signs: Iterable[int]) -> float:
    signs_list = signs if isinstance(signs, list) else list(signs)
    if len(signs_list) < 2:
        return 0.0
    flips = 0
    comparisons = 0
    for prev, current in zip(signs_list, signs_list[1:], strict=False):
        if prev == 0 or current == 0:
            continue
        comparisons += 1
        if prev != current:
            flips += 1
    return flips / max(1, comparisons)


class RegimeController:
    def __init__(self, caution: float = 0.4, defensive: float = 0.7, cooldown: int = 2) -> None:
        self.caution = caution
        self.defensive = defensive
        self.cooldown = cooldown

    def update(self, state: IterationState, ctx: IterationContext) -> tuple[Regime, float, float, float, int]:
        cooldown = state.cooldown_steps
        regime = state.regime
        if ctx.threat >= self.defensive or ctx.risk >= self.defensive:
            regime = Regime.DEFENSIVE
            cooldown = self.cooldown
        elif ctx.threat >= self.caution or ctx.risk >= self.caution:
            if regime == Regime.NORMAL:
                regime = Regime.CAUTION
                cooldown = self.cooldown
            elif regime == Regime.DEFENSIVE and cooldown > 0:
                cooldown -= 1
            else:
                regime = Regime.CAUTION
        else:
            if cooldown > 0:
                cooldown -= 1
                regime = state.regime
            else:
                regime = Regime.NORMAL

        if regime == Regime.NORMAL:
            return regime, 1.0, 1.0, 1.0, cooldown
        if regime == Regime.CAUTION:
            return regime, 0.7, 1.1, 1.2, cooldown
        return regime, 0.4, 1.3, 1.4, cooldown


class IterationLoop:
    def __init__(
        self,
        *,
        enabled: bool = False,
        delta_max: float = 1.0,
        alpha_min: float = 0.01,
        alpha_max: float = 0.5,
        clamp_bounds: tuple[float, float] = (-1.0, 1.0),
        regime_controller: RegimeController | None = None,
        risk_scale: float = 0.5,
        safety_multiplier: float = 1.5,
        tau_decay: float = 0.9,
        tau_max: float = 5.0,
        max_regime_flip_rate: float = 0.5,
        max_oscillation_index: float = 0.6,
        convergence_tol: float = 0.2,
        metrics_emitter: IterationMetricsEmitter | None = None,
    ) -> None:
        self.enabled = enabled
        self.delta_max = delta_max
        self.alpha_min = alpha_min
        self.alpha_max = alpha_max
        self.clamp_bounds = clamp_bounds
        self.regime_controller = regime_controller or RegimeController()
        self.risk_scale = risk_scale
        self.safety_multiplier = safety_multiplier
        self.tau_decay = tau_decay
        self.tau_max = tau_max
        self.max_regime_flip_rate = max_regime_flip_rate
        self.max_oscillation_index = max_oscillation_index
        self.convergence_tol = convergence_tol
        self.metrics_emitter = metrics_emitter

    def propose_action(self, state: IterationState, ctx: IterationContext) -> tuple[ActionProposal, PredictionBundle]:
        predicted = _to_vector(state.parameter)
        proposal = ActionProposal(
            action_id="predict",
            action_payload=state.parameter,
            scores=[state.parameter],
            confidence=1.0,
        )
        bundle = PredictionBundle(predicted_outcome=predicted, predicted_value=state.parameter)
        return proposal, bundle

    def execute_action(self, env: EnvironmentAdapter, proposal: ActionProposal, ctx: IterationContext) -> ObservationBundle:
        _ = ctx  # ctx reserved for future environment modulation
        return env.step(proposal.action_payload)

    def compute_prediction_error(
        self, prediction: PredictionBundle, observation: ObservationBundle, ctx: IterationContext
    ) -> PredictionError:
        _ = ctx
        predicted = prediction.predicted_outcome
        observed = observation.observed_outcome
        if len(predicted) != len(observed):
            raise ValueError("Prediction and observation dimensions must match")
        delta = [p - o for p, o in zip(predicted, observed, strict=True)]
        abs_delta = sum(abs(d) for d in delta) / len(delta) if delta else 0.0
        clipped = [max(-self.delta_max, min(self.delta_max, d)) for d in delta]
        components = [abs(d) for d in delta]
        return PredictionError(delta=delta, abs_delta=abs_delta, clipped_delta=clipped, components=components)

    def apply_updates(
        self,
        state: IterationState,
        pe: PredictionError,
        ctx: IterationContext,
    ) -> tuple[IterationState, UpdateResult, dict[str, float]]:
        delta_mean = sum(pe.clipped_delta) / len(pe.clipped_delta) if pe.clipped_delta else 0.0
        abs_max = max((abs(d) for d in pe.delta), default=0.0)

        def _apply_kill_switch_fields(target: IterationState, **updates: Any) -> IterationState:
            for key, value in updates.items():
                setattr(target, key, value)
            return target

        def _update_guard_window(target: IterationState, abs_delta_max: float) -> tuple[deque[float], float]:
            recent_abs_deltas = deque(target.recent_abs_deltas, maxlen=GUARD_WINDOW)
            recent_abs_deltas.append(abs_delta_max)
            window_max = max(recent_abs_deltas) if recent_abs_deltas else abs_delta_max
            return recent_abs_deltas, window_max

        def _calculate_envelope(
            *,
            regime: Regime,
            steps: int,
            delta_signs: deque[int],
            regime_flips_window: deque[int],
            windowed_abs_delta_max: float,
        ) -> tuple[dict[str, float], float, float, bool]:
            max_delta = max((abs(d) for d in pe.delta), default=0.0)
            clipped_max_delta = max((abs(d) for d in pe.clipped_delta), default=0.0)
            convergence_time = float(steps) if abs(delta_mean) <= self.delta_max * self.convergence_tol else -1.0
            sign_flip_rate = _sign_flip_rate(delta_signs)
            regime_flip_rate = sum(regime_flips_window) / max(1, len(regime_flips_window))
            envelope_metrics = {
                "max_delta": max_delta,
                "oscillation_index": sign_flip_rate,
                "regime_flip_rate": regime_flip_rate,
                "convergence_time": convergence_time,
                "sign_flip_rate": sign_flip_rate,
                "windowed_max_abs_delta": windowed_abs_delta_max,
                "windowed_sign_flip_rate": sign_flip_rate,
                "windowed_regime_flip_rate": regime_flip_rate,
                "guard_window": GUARD_WINDOW,
                "guard_max_abs_delta": MAX_ABS_DELTA,
                "guard_max_sign_flip_rate": MAX_SIGN_FLIP_RATE,
                "guard_max_regime_flip_rate": MAX_REGIME_FLIP_RATE,
            }
            delta_breach = clipped_max_delta > MAX_ABS_DELTA
            regime_flip_breach = len(regime_flips_window) > 1 and regime_flip_rate > MAX_REGIME_FLIP_RATE
            oscillation_breach = len(delta_signs) > 1 and sign_flip_rate > MAX_SIGN_FLIP_RATE
            envelope_breach = delta_breach or regime_flip_breach or oscillation_breach
            return envelope_metrics, sign_flip_rate, regime_flip_rate, envelope_breach

        def _guard_metrics_stable(metrics: dict[str, float]) -> bool:
            return (
                metrics.get("windowed_max_abs_delta", 0.0) <= MAX_ABS_DELTA
                and metrics.get("windowed_sign_flip_rate", 0.0) <= MAX_SIGN_FLIP_RATE
                and metrics.get("windowed_regime_flip_rate", 0.0) <= MAX_REGIME_FLIP_RATE
            )

        if not self.enabled:
            recent_abs_deltas, max_abs_delta = _update_guard_window(state, abs_max)
            sign_flip_rate = _sign_flip_rate(state.delta_signs)
            regime_flip_rate = sum(state.regime_flips_window) / max(1, len(state.regime_flips_window))
            frozen_state = replace(
                state,
                regime=Regime.DEFENSIVE if state.frozen else state.regime,
                last_effective_lr=0.0,
                frozen=state.frozen,
                recent_abs_deltas=recent_abs_deltas,
                max_abs_delta=max_abs_delta,
                last_envelope_metrics={
                    "max_delta": abs_max,
                    "oscillation_index": sign_flip_rate,
                    "regime_flip_rate": regime_flip_rate,
                    "convergence_time": float(state.steps) if abs(state.last_delta) <= self.delta_max else -1.0,
                    "sign_flip_rate": sign_flip_rate,
                    "windowed_max_abs_delta": max_abs_delta,
                    "windowed_sign_flip_rate": sign_flip_rate,
                    "windowed_regime_flip_rate": regime_flip_rate,
                    "guard_window": GUARD_WINDOW,
                    "guard_max_abs_delta": MAX_ABS_DELTA,
                    "guard_max_sign_flip_rate": MAX_SIGN_FLIP_RATE,
                    "guard_max_regime_flip_rate": MAX_REGIME_FLIP_RATE,
                },
            )
            return frozen_state, UpdateResult(parameter_deltas={}, bounded=state.frozen, applied=False), {
                "effective_lr": 0.0,
                "inhibition_scale": 1.0,
                "tau_scale": 1.0,
            }

        if state.kill_switch_active or state.frozen or state.cooldown_remaining > 0:
            delta_sign = _sign(delta_mean)
            regime = Regime.DEFENSIVE
            delta_signs = deque(state.delta_signs, maxlen=GUARD_WINDOW)
            regime_flips_window = deque(state.regime_flips_window, maxlen=GUARD_WINDOW)
            recent_abs_deltas, max_abs_delta = _update_guard_window(state, abs_max)
            regime_flip = regime != state.regime
            delta_signs.append(delta_sign)
            regime_flips_window.append(1 if regime_flip else 0)
            envelope_metrics, _, _, envelope_breach = _calculate_envelope(
                regime=regime,
                steps=state.steps + 1,
                delta_signs=delta_signs,
                regime_flips_window=regime_flips_window,
                windowed_abs_delta_max=max_abs_delta,
            )
            guard_stable = _guard_metrics_stable(envelope_metrics)
            if envelope_breach:
                cooldown_remaining = COOLDOWN_STEPS
            else:
                base_cooldown = state.cooldown_remaining
                cooldown_remaining = max(0, base_cooldown - 1)
            if cooldown_remaining > 0 or envelope_breach or not guard_stable:
                steps = state.steps + 1
                time_to_kill_switch = state.time_to_kill_switch if state.time_to_kill_switch is not None else steps
                frozen_state = replace(
                    state,
                    regime=Regime.DEFENSIVE,
                    last_effective_lr=0.0,
                    last_delta=delta_mean,
                    steps=steps,
                    delta_signs=delta_signs,
                    regime_flips_window=regime_flips_window,
                    recent_abs_deltas=recent_abs_deltas,
                    max_abs_delta=max_abs_delta,
                    last_envelope_metrics=envelope_metrics,
                )
                frozen_state = _apply_kill_switch_fields(
                    frozen_state,
                    cooldown_remaining=cooldown_remaining,
                    kill_switch_active=True,
                    instability_events_count=state.instability_events_count
                    + (1 if state.frozen and not state.kill_switch_active else 0),
                    recovered=False,
                    frozen=True,
                    time_to_kill_switch=time_to_kill_switch,
                )
                return frozen_state, UpdateResult(parameter_deltas={}, bounded=True, applied=False), {
                    "effective_lr": 0.0,
                    "inhibition_scale": 1.0,
                    "tau_scale": 1.0,
                    **envelope_metrics,
                }
            state = replace(
                state,
                recent_abs_deltas=recent_abs_deltas,
                max_abs_delta=max_abs_delta,
                last_envelope_metrics=envelope_metrics,
            )
            state = _apply_kill_switch_fields(
                state,
                kill_switch_active=False,
                cooldown_remaining=cooldown_remaining,
                recovered=True,
                frozen=False,
            )

        regime, lr_scale, inhibition_scale, tau_scale, cooldown = self.regime_controller.update(state, ctx)
        risk_adjusted_lr = state.learning_rate * lr_scale * (1 - ctx.risk * self.risk_scale)
        base_lr = max(self.alpha_min, min(self.alpha_max, risk_adjusted_lr))
        new_param = state.parameter - base_lr * delta_mean
        bounded = any(abs(d) > self.delta_max for d in pe.delta)

        low, high = self.clamp_bounds
        if new_param < low:
            new_param = low
            bounded = True
        if new_param > high:
            new_param = high
            bounded = True

        smoothed_tau = state.tau * self.tau_decay + ctx.dt * tau_scale * (1 - self.tau_decay)
        bounded_tau = min(self.tau_max, smoothed_tau)

        regime_flip = regime != state.regime
        # Detect oscillations via sign changes between consecutive delta means.
        delta_sign = _sign(delta_mean)
        steps = state.steps + 1
        delta_signs = deque(state.delta_signs, maxlen=GUARD_WINDOW)
        regime_flips_window = deque(state.regime_flips_window, maxlen=GUARD_WINDOW)
        recent_abs_deltas, max_abs_delta = _update_guard_window(state, abs_max)
        delta_signs.append(delta_sign)
        regime_flips_window.append(1 if regime_flip else 0)
        envelope_metrics, sign_flip_rate, regime_flip_rate, envelope_breach = _calculate_envelope(
            regime=regime,
            steps=steps,
            delta_signs=delta_signs,
            regime_flips_window=regime_flips_window,
            windowed_abs_delta_max=max_abs_delta,
        )

        new_state = replace(
            state,
            parameter=new_param,
            regime=regime,
            learning_rate=state.learning_rate,
            last_effective_lr=base_lr,
            inhibition_gain=state.inhibition_gain * inhibition_scale,
            tau=bounded_tau,
            last_delta=delta_mean,
            cooldown_steps=cooldown,
            steps=steps,
            frozen=envelope_breach,
            delta_signs=delta_signs,
            regime_flips_window=regime_flips_window,
            recent_abs_deltas=recent_abs_deltas,
            max_abs_delta=max_abs_delta,
            last_envelope_metrics=envelope_metrics,
        )
        new_state = _apply_kill_switch_fields(
            new_state,
            kill_switch_active=state.kill_switch_active,
            cooldown_remaining=state.cooldown_remaining,
            instability_events_count=state.instability_events_count,
            time_to_kill_switch=state.time_to_kill_switch,
            recovered=state.recovered,
        )
        if envelope_breach:
            time_to_kill_switch = state.time_to_kill_switch if state.time_to_kill_switch is not None else steps
            new_state = replace(
                state,
                regime=Regime.DEFENSIVE,
                last_effective_lr=0.0,
                last_delta=delta_mean,
                steps=steps,
                delta_signs=delta_signs,
                regime_flips_window=regime_flips_window,
                recent_abs_deltas=recent_abs_deltas,
                max_abs_delta=max_abs_delta,
                last_envelope_metrics=envelope_metrics,
            )
            new_state = _apply_kill_switch_fields(
                new_state,
                kill_switch_active=True,
                cooldown_remaining=COOLDOWN_STEPS,
                instability_events_count=state.instability_events_count + 1,
                time_to_kill_switch=time_to_kill_switch,
                recovered=False,
                frozen=True,
            )
            return new_state, UpdateResult(parameter_deltas={}, bounded=True, applied=False), {
                "effective_lr": 0.0,
                "inhibition_scale": inhibition_scale,
                "tau_scale": tau_scale,
                **envelope_metrics,
            }

        return new_state, UpdateResult(parameter_deltas={"parameter": new_param - state.parameter}, bounded=bounded, applied=True), {
            "effective_lr": base_lr,
            "inhibition_scale": inhibition_scale,
            "tau_scale": tau_scale,
            **envelope_metrics,
        }

    def evaluate_safety(self, state: IterationState, pe: PredictionError, ctx: IterationContext) -> SafetyDecision:
        abs_max = max((abs(d) for d in pe.delta), default=0.0)
        allow = abs_max <= self.delta_max * self.safety_multiplier
        reason = "stable"
        if state.regime == Regime.DEFENSIVE and abs_max > self.delta_max:
            allow = False
            reason = "defensive_clamp"
        if state.frozen:
            allow = False
            reason = "stability_envelope_breach"
        if not allow and reason == "stable":
            reason = "delta_exceeds_bounds"

        envelope_metrics = state.last_envelope_metrics or {}
        stability = {
            "abs_delta": pe.abs_delta,
            "abs_delta_max": abs_max,
            "max_delta": envelope_metrics.get("max_delta", abs_max),
            "windowed_max_abs_delta": envelope_metrics.get("windowed_max_abs_delta", abs_max),
            "max_abs_delta": state.max_abs_delta,
            "tau": state.tau,
            "inhibition_gain": state.inhibition_gain,
            "oscillation_index": envelope_metrics.get("oscillation_index", 0.0),
            "sign_flip_rate": envelope_metrics.get("sign_flip_rate", 0.0),
            "regime_flip_rate": envelope_metrics.get("regime_flip_rate", 0.0),
            "windowed_sign_flip_rate": envelope_metrics.get("windowed_sign_flip_rate", 0.0),
            "windowed_regime_flip_rate": envelope_metrics.get("windowed_regime_flip_rate", 0.0),
            "convergence_time": envelope_metrics.get("convergence_time", -1.0),
            "instability_events_count": state.instability_events_count,
            "time_to_kill_switch": state.time_to_kill_switch,
            "recovered": state.recovered,
        }
        risks = {"threat": ctx.threat, "risk": ctx.risk}
        return SafetyDecision(
            allow_next=allow,
            reason=reason,
            stability_metrics=stability,
            risk_metrics=risks,
            regime=state.regime,
        )

    def step(
        self,
        state: IterationState,
        env: EnvironmentAdapter,
        ctx: IterationContext,
    ) -> tuple[IterationState, dict[str, Any], SafetyDecision]:
        proposal, prediction = self.propose_action(state, ctx)
        observation = self.execute_action(env, proposal, ctx)
        pe = self.compute_prediction_error(prediction, observation, ctx)
        new_state, update_result, dynamics = self.apply_updates(state, pe, ctx)
        safety = self.evaluate_safety(new_state, pe, ctx)

        stability_guard = {
            "instability_events_count": new_state.instability_events_count,
            "max_abs_delta": new_state.max_abs_delta,
            "windowed_max_abs_delta": new_state.max_abs_delta,
            "time_to_kill_switch": new_state.time_to_kill_switch,
            "recovered": new_state.recovered,
            "windowed_sign_flip_rate": new_state.last_envelope_metrics.get("windowed_sign_flip_rate", 0.0),
            "windowed_regime_flip_rate": new_state.last_envelope_metrics.get("windowed_regime_flip_rate", 0.0),
        }

        trace = {
            "action": {
                "id": proposal.action_id,
                "payload": proposal.action_payload,
                "scores": proposal.scores,
                "confidence": proposal.confidence,
            },
            "prediction": prediction.predicted_outcome,
            "observation": observation.observed_outcome,
            "prediction_error": {
                "delta": pe.delta,
                "abs_delta": pe.abs_delta,
                "clipped_delta": pe.clipped_delta,
            },
            "regime": new_state.regime.value,
            "dynamics": {
                "learning_rate": new_state.learning_rate,
                "effective_learning_rate": new_state.last_effective_lr,
                "inhibition_gain": new_state.inhibition_gain,
                "tau": new_state.tau,
                **dynamics,
            },
            "update": {
                "parameter_deltas": update_result.parameter_deltas,
                "bounded": update_result.bounded,
                "applied": update_result.applied,
            },
            "safety": {
                "allow_next": safety.allow_next,
                "reason": safety.reason,
                "stability_metrics": safety.stability_metrics,
                "risk_metrics": safety.risk_metrics,
                "regime": safety.regime.value,
                "stability_guard": stability_guard,
            },
        }
        if self.metrics_emitter and self.metrics_emitter._should_emit():
            self.metrics_emitter.emit(ctx, trace)
        return new_state, trace, safety


@dataclass(frozen=True)
class IterationLoopContractAdapter:
    """Adapter for exposing IterationLoop signals via contract models."""

    @staticmethod
    def risk_signal(ctx: IterationContext, *, source: str | None = None) -> RiskSignal:
        return RiskSignal(threat=ctx.threat, risk=ctx.risk, source=source or "iteration_loop")

    @staticmethod
    def reward_prediction_error_signal(
        pe: PredictionError,
        *,
        reward: float | None = None,
    ) -> RewardPredictionErrorSignal:
        return RewardPredictionErrorSignal(
            delta=[float(value) for value in pe.delta],
            abs_delta=float(pe.abs_delta),
            clipped_delta=[float(value) for value in pe.clipped_delta],
            components=[float(value) for value in pe.components],
            reward=reward,
        )

    @staticmethod
    def stability_metrics(safety: SafetyDecision) -> StabilityMetrics:
        metrics = safety.stability_metrics
        return StabilityMetrics(
            max_abs_delta=float(metrics.get("max_abs_delta", metrics.get("abs_delta_max", 0.0))),
            windowed_max_abs_delta=float(metrics.get("windowed_max_abs_delta", 0.0)),
            oscillation_index=float(metrics.get("oscillation_index", 0.0)),
            sign_flip_rate=float(metrics.get("sign_flip_rate", 0.0)),
            regime_flip_rate=float(metrics.get("regime_flip_rate", 0.0)),
            convergence_time=float(metrics.get("convergence_time", -1.0)),
            instability_events_count=int(metrics.get("instability_events_count", 0)),
            time_to_kill_switch=metrics.get("time_to_kill_switch"),
            recovered=bool(metrics.get("recovered", False)),
        )

    @staticmethod
    def action_gating_signal(safety: SafetyDecision) -> ActionGatingSignal:
        return ActionGatingSignal(
            allow=safety.allow_next,
            reason=safety.reason,
            mode=safety.regime.value,
            metadata={
                "risk": float(safety.risk_metrics.get("risk", 0.0)),
                "threat": float(safety.risk_metrics.get("threat", 0.0)),
            },
        )


@dataclass
class IterationMetricsEmitter:
    enabled: bool = False
    output_path: pathlib.Path | None = None
    _prepared: bool = False

    def emit(self, ctx: IterationContext, trace: dict[str, Any]) -> None:
        if not self._should_emit():
            return
        if self.output_path is None:
            return
        if not self._prepared:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._prepared = True
        record = {
            "timestamp": ctx.timestamp,
            "dt": ctx.dt,
            "seed": ctx.seed,
            "threat": ctx.threat,
            "risk": ctx.risk,
            **trace,
        }
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _should_emit(self) -> bool:
        return self.enabled and self.output_path is not None
