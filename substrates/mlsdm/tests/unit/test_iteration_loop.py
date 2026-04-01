from __future__ import annotations

import importlib.util
import json
import sys
from collections import deque
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


def _load_iteration_loop_module():
    module_path = Path(__file__).resolve().parents[2] / "src" / "mlsdm" / "core" / "iteration_loop.py"
    spec = importlib.util.spec_from_file_location("iteration_loop", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load iteration_loop module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["iteration_loop"] = module
    spec.loader.exec_module(module)
    return module


iteration_loop = _load_iteration_loop_module()

ActionProposal = iteration_loop.ActionProposal
EnvironmentAdapter = iteration_loop.EnvironmentAdapter
IterationContext = iteration_loop.IterationContext
IterationLoop = iteration_loop.IterationLoop
IterationState = iteration_loop.IterationState
ObservationBundle = iteration_loop.ObservationBundle
PredictionBundle = iteration_loop.PredictionBundle
Regime = iteration_loop.Regime
RegimeController = iteration_loop.RegimeController
PredictionError = iteration_loop.PredictionError
SafetyDecision = iteration_loop.SafetyDecision


class ToyEnvironment(EnvironmentAdapter):
    def __init__(self, target: float = 1.0, outcomes: list[float] | None = None) -> None:
        self.target = target
        self.outcomes = outcomes or []
        self.index = 0

    def reset(self, seed: int | None = None) -> ObservationBundle:
        self.index = 0
        return ObservationBundle(observed_outcome=[self.target], reward=0.0, terminal=False)

    def step(self, action_payload: Any) -> ObservationBundle:
        _ = action_payload
        if self.outcomes:
            value = self.outcomes[min(self.index, len(self.outcomes) - 1)]
        else:
            value = self.target
        self.index += 1
        return ObservationBundle(observed_outcome=[float(value)], reward=None, terminal=False)


def _ctx(step: int, threat: float = 0.0, risk: float = 0.0) -> IterationContext:
    return IterationContext(dt=1.0, timestamp=float(step), seed=42, threat=threat, risk=risk)


def test_disabled_loop_does_not_apply_updates() -> None:
    loop = IterationLoop(enabled=False)
    state = IterationState(parameter=0.0)
    env = ToyEnvironment(target=1.0)
    new_state, trace, safety = loop.step(state, env, _ctx(0))

    assert new_state.parameter == pytest.approx(state.parameter)
    assert trace["prediction"] == [state.parameter]
    assert trace["observation"] == [env.target]
    assert trace["update"]["applied"] is False
    assert trace["update"]["parameter_deltas"] == {}
    assert trace["safety"]["stability_guard"]["windowed_sign_flip_rate"] == 0.0
    assert trace["safety"]["stability_guard"]["windowed_regime_flip_rate"] == 0.0
    assert safety.allow_next is True


def test_delta_learning_reduces_error() -> None:
    loop = IterationLoop(enabled=True, delta_max=1.0)
    env = ToyEnvironment(target=1.0)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    errors: list[float] = []
    for i in range(6):
        state, trace, _ = loop.step(state, env, _ctx(i))
        errors.append(abs(trace["prediction_error"]["delta"][0]))

    assert errors[0] > errors[-1]
    assert sum(errors[-3:]) / 3 < sum(errors[:3]) / 3


def test_threat_switches_regime_and_scales_dynamics() -> None:
    loop = IterationLoop(enabled=True)
    env = ToyEnvironment(target=0.5)
    base_state = IterationState(parameter=0.0, learning_rate=0.2, inhibition_gain=1.0, tau=0.5)

    new_state, trace, _ = loop.step(base_state, env, _ctx(0, threat=0.9, risk=0.8))

    assert new_state.regime == Regime.DEFENSIVE
    assert new_state.last_effective_lr < base_state.learning_rate
    assert new_state.learning_rate == base_state.learning_rate
    assert new_state.inhibition_gain > base_state.inhibition_gain
    assert new_state.tau > base_state.tau
    assert trace["regime"] == Regime.DEFENSIVE.value


def test_regime_controller_cooldown_transitions() -> None:
    controller = RegimeController(caution=0.4, defensive=0.7, cooldown=2)
    state = IterationState(regime=Regime.NORMAL, cooldown_steps=0)
    ctx = IterationContext(dt=1.0, timestamp=0.0, seed=0, threat=0.8, risk=0.0)

    regime, _, _, _, cooldown = controller.update(state, ctx)
    assert regime == Regime.DEFENSIVE
    assert cooldown == 2

    # Drop to caution; remain defensive while cooldown counts down
    ctx_caution = IterationContext(dt=1.0, timestamp=1.0, seed=0, threat=0.5, risk=0.0)
    state = replace(state, regime=regime, cooldown_steps=cooldown)
    regime, _, _, _, cooldown = controller.update(state, ctx_caution)
    assert regime == Regime.DEFENSIVE
    assert cooldown == 1

    # Back to normal threat; cooldown reaches zero then NORMAL
    ctx_normal = IterationContext(dt=1.0, timestamp=2.0, seed=0, threat=0.0, risk=0.0)
    state = replace(state, regime=regime, cooldown_steps=cooldown)
    regime, _, _, _, cooldown = controller.update(state, ctx_normal)
    assert regime == Regime.DEFENSIVE
    state = replace(state, regime=regime, cooldown_steps=cooldown)
    regime, _, _, _, cooldown = controller.update(state, ctx_normal)
    assert regime == Regime.NORMAL


def test_safety_gate_blocks_runaway_deltas() -> None:
    loop = IterationLoop(enabled=True, delta_max=1.0)
    env = ToyEnvironment(target=0.0, outcomes=[5.0, -5.0])
    state = IterationState(parameter=0.0, learning_rate=0.3)

    new_state, trace, safety = loop.step(state, env, _ctx(0, threat=0.2, risk=0.2))

    assert safety.allow_next is False
    assert trace["update"]["bounded"] is True
    assert abs(new_state.parameter) <= 1.0


def test_compute_prediction_error_mismatch_raises() -> None:
    loop = IterationLoop(enabled=True)
    prediction = PredictionBundle(predicted_outcome=[1.0], predicted_value=None)
    observation = ObservationBundle(observed_outcome=[1.0, 0.0])

    with pytest.raises(ValueError):
        loop.compute_prediction_error(prediction, observation, _ctx(0))


def test_apply_updates_clamps_parameter_bounds() -> None:
    loop = IterationLoop(enabled=True, clamp_bounds=(-0.2, 0.2), delta_max=1.0, alpha_max=0.5)
    state = IterationState(parameter=0.0, learning_rate=0.5, inhibition_gain=1.0, tau=1.0)
    ctx = _ctx(0)

    # Force upward clamp
    pe_high = PredictionError(delta=[-10.0], abs_delta=10.0, clipped_delta=[-1.0])
    new_state, update_result, _ = loop.apply_updates(state, pe_high, ctx)
    assert update_result.bounded
    assert new_state.parameter == 0.2

    # Force downward clamp
    pe_low = PredictionError(delta=[10.0], abs_delta=10.0, clipped_delta=[1.0])
    new_state, update_result, _ = loop.apply_updates(state, pe_low, ctx)
    assert update_result.bounded
    assert new_state.parameter == -0.2


def test_stability_envelope_triggers_fail_safe_on_oscillation() -> None:
    loop = IterationLoop(
        enabled=True,
        delta_max=0.5,
        max_regime_flip_rate=0.3,
        max_oscillation_index=0.4,
    )
    env = ToyEnvironment(outcomes=[1.0, -1.0] * 6)
    state = IterationState(parameter=0.0, learning_rate=0.3)

    frozen_seen = False
    safety: SafetyDecision | None = None
    for i in range(12):
        state, trace, safety = loop.step(state, env, _ctx(i, threat=0.9 if i % 2 == 0 else 0.1, risk=0.6))
        if state.frozen:
            frozen_seen = True
            assert trace["regime"] == Regime.DEFENSIVE.value
            assert trace["update"]["applied"] is False
            assert safety.allow_next is False
            assert safety.reason == "stability_envelope_breach"
            assert "oscillation_index" in safety.stability_metrics
            break

    assert frozen_seen
    assert safety is not None


def test_long_sequence_converges_or_halts_safely() -> None:
    loop = IterationLoop(
        enabled=True,
        delta_max=1.0,
        max_regime_flip_rate=0.6,
        max_oscillation_index=0.7,
        convergence_tol=0.3,
    )
    outcomes = []
    for i in range(20):
        oscillation = 0.05 * ((-1) ** i)
        outcomes.append(0.8 + oscillation)
    env = ToyEnvironment(outcomes=outcomes)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    final_safety: SafetyDecision | None = None
    for i in range(20):
        state, _, final_safety = loop.step(state, env, _ctx(i, threat=0.3, risk=0.2))
        if state.frozen:
            break

    assert final_safety is not None
    assert (
        not state.frozen and abs(state.last_delta) <= loop.delta_max * loop.convergence_tol
    ) or state.frozen
    assert "convergence_time" in final_safety.stability_metrics


def test_to_vector_handles_sequences() -> None:
    _to_vector = iteration_loop._to_vector

    assert _to_vector(5.0) == [5.0]
    assert _to_vector(0) == [0.0]
    assert _to_vector([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]
    assert _to_vector((4.0, 5.0)) == [4.0, 5.0]


def test_sign_function_edge_cases() -> None:
    _sign = iteration_loop._sign

    assert _sign(10.0) == 1
    assert _sign(-10.0) == -1
    assert _sign(0.0) == 0
    assert _sign(0.0001) == 1
    assert _sign(-0.0001) == -1


def test_regime_controller_normal_to_caution_transition() -> None:
    controller = RegimeController(caution=0.4, defensive=0.7, cooldown=2)
    state = IterationState(regime=Regime.NORMAL, cooldown_steps=0)
    ctx = IterationContext(dt=1.0, timestamp=0.0, seed=0, threat=0.5, risk=0.3)

    regime, lr_scale, inh_scale, tau_scale, cooldown = controller.update(state, ctx)

    assert regime == Regime.CAUTION
    assert cooldown == 2
    assert lr_scale == 0.7
    assert inh_scale == 1.1
    assert tau_scale == 1.2


def test_regime_controller_defensive_cooldown_expires() -> None:
    controller = RegimeController(caution=0.4, defensive=0.7, cooldown=2)
    state = IterationState(regime=Regime.DEFENSIVE, cooldown_steps=1)
    ctx = IterationContext(dt=1.0, timestamp=0.0, seed=0, threat=0.5, risk=0.0)

    regime, _, _, _, cooldown = controller.update(state, ctx)

    assert regime == Regime.DEFENSIVE
    assert cooldown == 0

    state = replace(state, regime=regime, cooldown_steps=cooldown)
    regime, _, _, _, cooldown = controller.update(state, ctx)
    assert regime == Regime.CAUTION


def test_kill_switch_activation_on_envelope_breach() -> None:
    loop = IterationLoop(
        enabled=True,
        delta_max=0.3,
        max_regime_flip_rate=0.3,
        max_oscillation_index=0.3,
    )
    env = ToyEnvironment(outcomes=[2.0, -2.0, 2.0, -2.0, 2.0, -2.0])
    state = IterationState(parameter=0.0, learning_rate=0.4)

    kill_switch_triggered = False
    for i in range(10):
        state, trace, safety = loop.step(state, env, _ctx(i))

        if state.kill_switch_active:
            kill_switch_triggered = True
            assert state.frozen is True
            assert state.cooldown_remaining > 0
            assert trace["update"]["applied"] is False
            assert safety.allow_next is False
            break

    assert kill_switch_triggered


def test_deterministic_instability_triggers_kill_switch() -> None:
    loop = IterationLoop(enabled=True, delta_max=1.0)
    env = ToyEnvironment(outcomes=[3.0, -3.0, 3.0, -3.0])
    state = IterationState(parameter=0.0, learning_rate=0.05)
    baseline_instability_events = state.instability_events_count

    kill_switch_state: IterationState | None = None
    kill_switch_trace: dict[str, Any] | None = None
    for i in range(4):
        state, trace, _ = loop.step(state, env, _ctx(i))
        if state.kill_switch_active:
            kill_switch_state = state
            kill_switch_trace = trace
            break

    assert kill_switch_state is not None
    assert kill_switch_trace is not None
    assert kill_switch_state.kill_switch_active is True
    assert kill_switch_state.regime == Regime.DEFENSIVE
    assert kill_switch_trace["update"]["applied"] is False
    assert kill_switch_state.instability_events_count == baseline_instability_events + 1
    assert kill_switch_state.time_to_kill_switch is not None
    assert kill_switch_state.time_to_kill_switch == kill_switch_state.steps


def test_cooldown_recovery_reenables_learning() -> None:
    loop = IterationLoop(enabled=True, delta_max=1.0)
    outcomes = [3.0, -3.0, 3.0, -3.0] + [0.1] * 12
    env = ToyEnvironment(outcomes=outcomes)
    state = IterationState(parameter=0.0, learning_rate=0.05)

    kill_switch_seen = False
    recovered_seen = False
    for i in range(len(outcomes)):
        state, trace, _ = loop.step(state, env, _ctx(i))
        if state.kill_switch_active:
            kill_switch_seen = True
            assert trace["update"]["applied"] is False
        if kill_switch_seen and not state.kill_switch_active:
            recovered_seen = True
            assert trace["update"]["applied"] is True
            assert state.recovered is True
            break

    assert kill_switch_seen is True
    assert recovered_seen is True


def test_default_off_regression_no_update_neutral_metrics() -> None:
    loop = IterationLoop(enabled=False)
    env = ToyEnvironment(outcomes=[0.8, 0.8])
    state = IterationState(parameter=0.3, learning_rate=0.2)

    new_state, trace, _ = loop.step(state, env, _ctx(0))

    assert new_state.parameter == pytest.approx(state.parameter)
    assert trace["prediction"] == [state.parameter]
    assert trace["observation"] == [0.8]
    assert trace["update"]["applied"] is False
    assert trace["update"]["parameter_deltas"] == {}
    assert trace["dynamics"]["effective_learning_rate"] == 0.0
    assert trace["dynamics"]["effective_lr"] == 0.0
    assert trace["dynamics"]["inhibition_scale"] == 1.0
    assert trace["dynamics"]["tau_scale"] == 1.0
    assert trace["safety"]["stability_guard"]["instability_events_count"] == 0
    assert trace["safety"]["stability_guard"]["max_abs_delta"] == pytest.approx(0.5)
    assert trace["safety"]["stability_guard"]["time_to_kill_switch"] is None


def test_guard_metrics_do_not_change_inference_trace() -> None:
    loop = IterationLoop(enabled=False)
    env = ToyEnvironment(outcomes=[0.4])
    state = IterationState(parameter=0.25, learning_rate=0.2)
    state.delta_signs = deque([1, -1, 1], maxlen=iteration_loop.GUARD_WINDOW)
    state.regime_flips_window = deque([1, 0, 1], maxlen=iteration_loop.GUARD_WINDOW)
    state.recent_abs_deltas = deque([0.1, 0.2, 0.3], maxlen=iteration_loop.GUARD_WINDOW)
    state.max_abs_delta = 0.3

    new_state, trace, _ = loop.step(state, env, _ctx(0))

    assert new_state.parameter == pytest.approx(state.parameter)
    assert trace["prediction"] == [state.parameter]
    assert trace["observation"] == [0.4]
    assert trace["update"]["applied"] is False
    assert "stability_guard" in trace["safety"]
    assert trace["safety"]["stability_guard"]["windowed_sign_flip_rate"] == pytest.approx(
        trace["safety"]["stability_metrics"]["windowed_sign_flip_rate"]
    )


def test_kill_switch_recovery_after_cooldown() -> None:
    loop = IterationLoop(enabled=True, delta_max=0.5)
    state = IterationState(parameter=0.0, learning_rate=0.2)
    state.frozen = True
    state.kill_switch_active = True
    state.cooldown_remaining = 2

    ctx = _ctx(0)

    pe = PredictionError(delta=[0.1], abs_delta=0.1, clipped_delta=[0.1])
    new_state, result, _ = loop.apply_updates(state, pe, ctx)

    assert new_state.kill_switch_active is True
    assert result.applied is False

    state = new_state
    state.cooldown_remaining = 0
    state.regime = Regime.DEFENSIVE
    state.regime_flips_window = deque(maxlen=iteration_loop.GUARD_WINDOW)
    state.delta_signs = deque(maxlen=iteration_loop.GUARD_WINDOW)
    new_state, result, _ = loop.apply_updates(state, pe, ctx)

    assert new_state.kill_switch_active is False
    assert new_state.recovered is True
    assert new_state.frozen is False
    assert result.applied is True
    assert new_state.parameter != state.parameter


def test_kill_switch_recovery_requires_stable_guard_metrics() -> None:
    loop = IterationLoop(enabled=True, delta_max=0.5)
    state = IterationState(parameter=0.0, learning_rate=0.2)
    state.frozen = True
    state.kill_switch_active = True
    state.cooldown_remaining = 0
    state.delta_signs = deque([1, -1, 1, -1], maxlen=iteration_loop.GUARD_WINDOW)
    state.regime_flips_window = deque(maxlen=iteration_loop.GUARD_WINDOW)

    ctx = _ctx(0)
    pe = PredictionError(delta=[0.1], abs_delta=0.1, clipped_delta=[0.1])
    new_state, result, _ = loop.apply_updates(state, pe, ctx)

    assert new_state.kill_switch_active is True
    assert new_state.recovered is False
    assert new_state.frozen is True
    assert result.applied is False


def test_kill_switch_resets_cooldown_on_repeated_breach() -> None:
    loop = IterationLoop(enabled=True)
    state = IterationState(parameter=0.0, learning_rate=0.2)
    state.frozen = True
    state.kill_switch_active = True
    state.cooldown_remaining = 1
    state.regime_flips_window = deque(maxlen=iteration_loop.GUARD_WINDOW)
    state.delta_signs = deque(maxlen=iteration_loop.GUARD_WINDOW)

    ctx = _ctx(0)
    breach_delta = iteration_loop.MAX_ABS_DELTA + 1.0
    pe = PredictionError(
        delta=[breach_delta],
        abs_delta=breach_delta,
        clipped_delta=[breach_delta],
    )

    new_state, result, _ = loop.apply_updates(state, pe, ctx)

    assert new_state.kill_switch_active is True
    assert new_state.cooldown_remaining == iteration_loop.COOLDOWN_STEPS
    assert new_state.recovered is False
    assert new_state.frozen is True
    assert result.applied is False


def test_frozen_state_prevents_updates() -> None:
    loop = IterationLoop(enabled=True)
    state = IterationState(parameter=5.0, learning_rate=0.2, frozen=True)
    state.kill_switch_active = True
    state.cooldown_remaining = 3

    env = ToyEnvironment(target=0.0)
    ctx = _ctx(0)

    new_state, trace, safety = loop.step(state, env, ctx)

    assert new_state.regime == Regime.DEFENSIVE
    assert trace["update"]["applied"] is False
    assert safety.allow_next is False
    assert safety.reason == "stability_envelope_breach"


def test_metrics_emitter_writes_to_file(tmp_path: Path) -> None:
    output_path = tmp_path / "metrics.jsonl"
    emitter = iteration_loop.IterationMetricsEmitter(enabled=True, output_path=output_path)

    loop = IterationLoop(enabled=True, metrics_emitter=emitter)
    env = ToyEnvironment(target=1.0)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    for i in range(3):
        state, _, _ = loop.step(state, env, _ctx(i))

    assert output_path.exists()

    lines = output_path.read_text().strip().split("\n")
    assert len(lines) == 3

    for line in lines:
        record = json.loads(line)
        assert "timestamp" in record
        assert "dt" in record
        assert "seed" in record
        assert "prediction_error" in record


def test_metrics_emitter_disabled_does_not_write() -> None:
    emitter = iteration_loop.IterationMetricsEmitter(enabled=False)

    loop = IterationLoop(enabled=True, metrics_emitter=emitter)
    env = ToyEnvironment(target=1.0)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    state, _, _ = loop.step(state, env, _ctx(0))


def test_metrics_emitter_creates_parent_directories(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "dir" / "metrics.jsonl"
    emitter = iteration_loop.IterationMetricsEmitter(enabled=True, output_path=output_path)

    loop = IterationLoop(enabled=True, metrics_emitter=emitter)
    env = ToyEnvironment(target=1.0)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    state, _, _ = loop.step(state, env, _ctx(0))

    assert output_path.exists()
    assert output_path.parent.exists()


@pytest.mark.parametrize(
    ("threat", "risk", "expected_regime"),
    [
        (0.8, 0.8, Regime.DEFENSIVE),
        (0.5, 0.3, Regime.CAUTION),
        (0.1, 0.1, Regime.NORMAL),
        (0.75, 0.2, Regime.DEFENSIVE),
        (0.3, 0.75, Regime.DEFENSIVE),
    ],
)
def test_regime_selection_by_threat_risk(threat: float, risk: float, expected_regime: Regime) -> None:
    loop = IterationLoop(enabled=True)
    env = ToyEnvironment(target=0.5)
    state = IterationState(parameter=0.0, learning_rate=0.2)

    new_state, _, _ = loop.step(state, env, _ctx(0, threat=threat, risk=risk))

    assert new_state.regime == expected_regime


def test_sign_flip_rate_calculation_with_zeros() -> None:
    _sign_flip_rate = iteration_loop._sign_flip_rate

    assert _sign_flip_rate([0, 0, 0]) == 0.0

    rate = _sign_flip_rate([1, -1, 1])
    assert rate == 1.0

    assert _sign_flip_rate([1]) == 0.0
