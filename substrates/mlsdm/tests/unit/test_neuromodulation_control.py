import pytest

from mlsdm.cognition.neuromodulation import NeuromodulatorState, enforce_governance_gate
from mlsdm.cognition.prediction_error import PredictionErrorAccumulator, PredictionErrorSignals


def test_neuromodulator_state_stays_in_bounds() -> None:
    state = NeuromodulatorState()
    signals = PredictionErrorSignals.from_components(
        perception_error=1.5,
        memory_error=-0.5,
        policy_error=2.0,
    )

    updated = state.update(signals, memory_pressure=1.0, risk_mode="emergency")

    assert 0.0 <= updated["exploration_bias"] <= 1.0
    assert 0.001 <= updated["learning_rate"] <= 0.5
    assert 0.0 <= updated["memory_consolidation_bias"] <= 1.0
    assert 0.0 <= updated["policy_strictness"] <= 1.0


def test_governance_gate_does_not_override_inhibition() -> None:
    result = enforce_governance_gate(False, policy_strictness=0.0)

    assert result["allow_execution"] is False
    assert result["governance_locked"] is True


def test_prediction_error_accumulator_is_bounded() -> None:
    accumulator = PredictionErrorAccumulator(max_cumulative_error=1.0, decay=1.0)
    signals = PredictionErrorSignals.from_components(1.0, 1.0, 1.0)

    for _ in range(5):
        accumulator.update(signals)

    assert accumulator.cumulative_error == pytest.approx(1.0)
