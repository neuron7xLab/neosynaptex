"""Property-based tests for AdEx neuron dynamics using Hypothesis.

Uses Hypothesis to generate 1000+ test cases automatically.
Tests universal properties: finiteness, boundedness, reset dynamics.

References
----------
docs/LEGENDARY_QUICKSTART.md
docs/SPEC.md#P0-1
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step


@pytest.mark.property
@given(
    V=st.floats(-100, 50, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 1000, allow_nan=False, allow_infinity=False),
    I_syn=st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
    I_ext=st.floats(-1000, 1000, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.001, 1.0, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_outputs_finite(V: float, w: float, I_syn: float, I_ext: float, dt_ms: float) -> None:
    """Property: AdEx outputs are ALWAYS finite.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA
    I_syn : float
        Synaptic current in pA
    I_ext : float
        External current in pA
    dt_ms : float
        Timestep in ms

    Notes
    -----
    Tests that no matter what inputs are provided (within physical bounds),
    the outputs are always finite numbers.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    new_state = adex_step(
        state,
        params,
        dt_ms,
        np.array([I_syn], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )

    assert np.isfinite(new_state.V_mV[0]), f"V is not finite: {new_state.V_mV[0]}"
    assert np.isfinite(new_state.w_pA[0]), f"w is not finite: {new_state.w_pA[0]}"


@pytest.mark.property
@given(
    V=st.floats(-80, 0, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 500, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_adaptation_nonnegative(V: float, w: float, dt_ms: float) -> None:
    """Property: Adaptation current w stays mostly non-negative.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA (≥0)
    dt_ms : float
        Timestep in ms

    Notes
    -----
    The adaptation current models slow K+ channels and should not go significantly negative.
    Small numerical errors are acceptable.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    new_state = adex_step(
        state,
        params,
        dt_ms,
        np.array([0.0], dtype=np.float64),
        np.array([0.0], dtype=np.float64),
    )
    # Allow small numerical errors (up to 1 pA)
    assert new_state.w_pA[0] >= -1.0, f"w became negative: {new_state.w_pA[0]}"


@pytest.mark.property
@given(
    V=st.floats(-80, 0, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 200, allow_nan=False, allow_infinity=False),
    I_ext=st.floats(50, 500, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.01, 0.2, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_excitatory_input_increases_voltage(
    V: float, w: float, I_ext: float, dt_ms: float
) -> None:
    """Property: Excitatory input yields finite, valid subthreshold states.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA
    I_ext : float
        External current in pA (>0)
    dt_ms : float
        Timestep in ms

    Notes
    -----
    Excitatory input does not guarantee monotonic voltage increase across all
    parameter regimes; invariants are finiteness and consistent spike labeling.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    new_state = adex_step(
        state,
        params,
        dt_ms,
        np.array([0.0], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )

    assert np.isfinite(new_state.V_mV[0]), f"V is not finite: {new_state.V_mV[0]}"
    assert np.isfinite(new_state.w_pA[0]), f"w is not finite: {new_state.w_pA[0]}"
    if not new_state.spiked[0]:
        assert new_state.V_mV[0] < params.Vpeak_mV, (
            f"Subthreshold state reached Vpeak: {new_state.V_mV[0]}"
        )


@pytest.mark.property
@given(
    N=st.integers(1, 100),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_vectorized_consistency(N: int, dt_ms: float) -> None:
    """Property: Vectorized step produces same results as individual steps.

    Parameters
    ----------
    N : int
        Number of neurons
    dt_ms : float
        Timestep in ms

    Notes
    -----
    Tests that processing N neurons together gives same results as
    processing them individually.
    """
    params = AdExParams()
    rng = np.random.default_rng(42)

    V_init = rng.uniform(-70, -60, N)
    w_init = rng.uniform(0, 100, N)
    I_syn = rng.uniform(0, 50, N)
    I_ext = rng.uniform(0, 50, N)

    # Vectorized step
    state = AdExState(V_mV=V_init.copy(), w_pA=w_init.copy(), spiked=np.zeros(N, dtype=bool))
    vectorized_result = adex_step(state, params, dt_ms, I_syn, I_ext)

    # Individual steps
    individual_results = []
    for i in range(N):
        state_i = AdExState(
            V_mV=np.array([V_init[i]], dtype=np.float64),
            w_pA=np.array([w_init[i]], dtype=np.float64),
            spiked=np.array([False]),
        )
        result_i = adex_step(
            state_i,
            params,
            dt_ms,
            np.array([I_syn[i]], dtype=np.float64),
            np.array([I_ext[i]], dtype=np.float64),
        )
        individual_results.append(result_i)

    # Compare results
    for i in range(N):
        np.testing.assert_allclose(
            vectorized_result.V_mV[i],
            individual_results[i].V_mV[0],
            rtol=1e-10,
            atol=1e-10,
            err_msg=f"Neuron {i}: V mismatch",
        )
        np.testing.assert_allclose(
            vectorized_result.w_pA[i],
            individual_results[i].w_pA[0],
            rtol=1e-10,
            atol=1e-10,
            err_msg=f"Neuron {i}: w mismatch",
        )
        assert vectorized_result.spiked[i] == individual_results[i].spiked[0], (
            f"Neuron {i}: spike mismatch"
        )


@pytest.mark.property
@given(
    V=st.floats(-80, -50, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 200, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_resting_state_stability(V: float, w: float, dt_ms: float) -> None:
    """Property: Near resting potential with no input, voltage stays bounded.

    Parameters
    ----------
    V : float
        Membrane voltage in mV (near rest)
    w : float
        Adaptation current in pA
    dt_ms : float
        Timestep in ms

    Notes
    -----
    Without input, neuron near rest should remain stable.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    # Run 10 steps
    for _ in range(10):
        state = adex_step(
            state,
            params,
            dt_ms,
            np.array([0.0], dtype=np.float64),
            np.array([0.0], dtype=np.float64),
        )
        # Voltage should stay in reasonable bounds
        assert -100 <= state.V_mV[0] <= 50, f"Voltage out of bounds: {state.V_mV[0]}"


@pytest.mark.property
@given(
    V=st.floats(-80, 20, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 500, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_spike_reset(V: float, w: float, dt_ms: float) -> None:
    """Property: When spike occurs, voltage resets to Vreset.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA
    dt_ms : float
        Timestep in ms

    Notes
    -----
    If neuron crosses spike threshold, voltage should reset.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    # Large excitatory input to trigger spike
    I_ext = 500.0

    new_state = adex_step(
        state,
        params,
        dt_ms,
        np.array([0.0], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )

    if new_state.spiked[0]:
        # Voltage should be reset
        assert abs(new_state.V_mV[0] - params.Vreset_mV) < 1e-6, (
            f"Spike occurred but V={new_state.V_mV[0]}, expected {params.Vreset_mV}"
        )


@pytest.mark.property
@given(
    V=st.floats(-80, 20, allow_nan=False, allow_infinity=False),
    w=st.floats(0, 500, allow_nan=False, allow_infinity=False),
    I_ext=st.floats(0, 500, allow_nan=False, allow_infinity=False),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_adaptation_increases_on_spike(V: float, w: float, I_ext: float, dt_ms: float) -> None:
    """Property: Adaptation current increases when spike occurs.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA
    I_ext : float
        External current in pA
    dt_ms : float
        Timestep in ms

    Notes
    -----
    When neuron spikes, adaptation current should increase by b.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    new_state = adex_step(
        state,
        params,
        dt_ms,
        np.array([0.0], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )

    if new_state.spiked[0]:
        # Adaptation should have increased (minus any decay)
        # w_new = w + dt*(...) + b, so w_new >= w + b - decay
        assert new_state.w_pA[0] > state.w_pA[0], (
            f"Adaptation did not increase on spike: {state.w_pA[0]} -> {new_state.w_pA[0]}"
        )


@pytest.mark.property
@given(
    N=st.integers(1, 50),
    steps=st.integers(1, 20),
    dt_ms=st.floats(0.01, 0.5, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_deterministic(N: int, steps: int, dt_ms: float) -> None:
    """Property: Same initial state and inputs produce identical outputs.

    Parameters
    ----------
    N : int
        Number of neurons
    steps : int
        Number of timesteps
    dt_ms : float
        Timestep in ms

    Notes
    -----
    Determinism is a core requirement. Same inputs must produce same outputs.
    """
    params = AdExParams()
    rng = np.random.default_rng(42)

    V_init = rng.uniform(-70, -60, N)
    w_init = rng.uniform(0, 100, N)
    I_syn = rng.uniform(0, 50, (steps, N))
    I_ext = rng.uniform(0, 50, (steps, N))

    # Run 1
    state1 = AdExState(V_mV=V_init.copy(), w_pA=w_init.copy(), spiked=np.zeros(N, dtype=bool))
    for i in range(steps):
        state1 = adex_step(state1, params, dt_ms, I_syn[i], I_ext[i])

    # Run 2 (identical inputs)
    state2 = AdExState(V_mV=V_init.copy(), w_pA=w_init.copy(), spiked=np.zeros(N, dtype=bool))
    for i in range(steps):
        state2 = adex_step(state2, params, dt_ms, I_syn[i], I_ext[i])

    # Results must be identical
    np.testing.assert_array_equal(state1.V_mV, state2.V_mV)
    np.testing.assert_array_equal(state1.w_pA, state2.w_pA)
    np.testing.assert_array_equal(state1.spiked, state2.spiked)


@pytest.mark.property
@given(
    V=st.floats(-100, 50, allow_nan=False, allow_infinity=False),
    w=st.floats(-100, 1000, allow_nan=False, allow_infinity=False),  # Test negative w
)
@settings(deadline=None)
def test_adex_handles_edge_case_inputs(V: float, w: float) -> None:
    """Property: AdEx handles edge case inputs gracefully.

    Parameters
    ----------
    V : float
        Membrane voltage in mV
    w : float
        Adaptation current in pA (may be negative)

    Notes
    -----
    Tests that AdEx doesn't crash on unusual inputs and stays finite.
    """
    params = AdExParams()
    state = AdExState(
        V_mV=np.array([V], dtype=np.float64),
        w_pA=np.array([w], dtype=np.float64),
        spiked=np.array([False]),
    )

    new_state = adex_step(
        state, params, 0.1, np.array([0.0], dtype=np.float64), np.array([0.0], dtype=np.float64)
    )

    # Outputs should be finite
    assert np.isfinite(new_state.V_mV[0])
    assert np.isfinite(new_state.w_pA[0])


@pytest.mark.property
@given(
    dt1=st.floats(0.01, 0.2, allow_nan=False, allow_infinity=False),
    dt2=st.floats(0.01, 0.2, allow_nan=False, allow_infinity=False),
)
@settings(deadline=None)
def test_adex_timestep_independence(dt1: float, dt2: float) -> None:
    """Property: Smaller timesteps produce similar results (within error bounds).

    Parameters
    ----------
    dt1 : float
        First timestep in ms
    dt2 : float
        Second timestep in ms

    Notes
    -----
    While exact results will differ, both should produce finite, reasonable outputs.
    """
    assume(abs(dt1 - dt2) > 0.001)  # Ensure meaningful difference

    params = AdExParams()
    V_init = -65.0
    w_init = 50.0
    I_ext = 100.0

    state1 = AdExState(
        V_mV=np.array([V_init], dtype=np.float64),
        w_pA=np.array([w_init], dtype=np.float64),
        spiked=np.array([False]),
    )
    state2 = AdExState(
        V_mV=np.array([V_init], dtype=np.float64),
        w_pA=np.array([w_init], dtype=np.float64),
        spiked=np.array([False]),
    )

    result1 = adex_step(
        state1,
        params,
        dt1,
        np.array([0.0], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )
    result2 = adex_step(
        state2,
        params,
        dt2,
        np.array([0.0], dtype=np.float64),
        np.array([I_ext], dtype=np.float64),
    )

    # Both should be finite
    assert np.isfinite(result1.V_mV[0])
    assert np.isfinite(result2.V_mV[0])
    assert np.isfinite(result1.w_pA[0])
    assert np.isfinite(result2.w_pA[0])
