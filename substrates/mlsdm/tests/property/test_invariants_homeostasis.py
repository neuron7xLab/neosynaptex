"""
Property-based tests for homeostasis and neuromodulation invariants.
"""

from hypothesis import given
from hypothesis import strategies as st

from mlsdm.cognition.neuromodulation import NeuromodulatorState, enforce_governance_gate
from mlsdm.cognition.prediction_error import PredictionErrorAccumulator, PredictionErrorSignals


@given(
    perception=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    memory=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    policy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    memory_pressure=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    risk_mode=st.sampled_from(["normal", "guarded", "degraded", "emergency", None]),
)
def test_neuromodulator_bounds_hold(perception, memory, policy, memory_pressure, risk_mode) -> None:
    state = NeuromodulatorState()
    signals = PredictionErrorSignals.from_components(perception, memory, policy)

    state.update(signals, memory_pressure=memory_pressure, risk_mode=risk_mode)

    assert state.bounds.exploration_range[0] <= state.exploration_bias <= state.bounds.exploration_range[1]
    assert state.bounds.learning_rate_range[0] <= state.learning_rate <= state.bounds.learning_rate_range[1]
    assert (
        state.bounds.consolidation_range[0]
        <= state.memory_consolidation_bias
        <= state.bounds.consolidation_range[1]
    )
    assert (
        state.bounds.policy_strictness_range[0]
        <= state.policy_strictness
        <= state.bounds.policy_strictness_range[1]
    )


@given(
    total_error=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_prediction_error_accumulator_is_bounded(total_error) -> None:
    accumulator = PredictionErrorAccumulator(max_cumulative_error=2.0, decay=1.0)
    signals = PredictionErrorSignals.from_components(total_error, total_error, total_error)

    for _ in range(5):
        accumulator.update(signals)

    assert accumulator.cumulative_error <= 2.0


@given(policy_strictness=st.floats(min_value=0.0, max_value=1.0))
def test_governance_gate_dominates(policy_strictness) -> None:
    gate = enforce_governance_gate(False, policy_strictness=policy_strictness)

    assert gate["allow_execution"] is False
    assert gate["governance_locked"] is True
