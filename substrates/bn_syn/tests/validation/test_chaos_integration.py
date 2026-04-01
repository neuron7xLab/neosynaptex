"""Real chaos engineering tests that test BN-Syn runtime resilience.

These tests inject faults into actual BN-Syn execution paths and verify
expected behavior (fail-fast or controlled degradation).

Unlike utility tests, these tests:
1. Import and run actual BN-Syn components
2. Inject faults during execution
3. Validate system response (error detection or graceful handling)

References
----------
docs/TESTING_MUTATION.md - Chaos engineering philosophy
"""

from __future__ import annotations

import contextlib
import numpy as np
import pytest

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step
from bnsyn.testing import FaultConfig, inject_numeric_fault, validate_numeric_health


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_detects_nan_in_state() -> None:
    """Test that AdEx detects and rejects NaN in state variables.

    Chaos scenario: NaN corruption in voltage array.
    Expected behavior: System should detect NaN and raise ValueError.
    """
    params = AdExParams()

    # Create state with NaN in voltage
    state = AdExState(
        V_mV=np.array([np.nan, -65.0, -70.0]),
        w_pA=np.array([0.0, 50.0, 30.0]),
        spiked=np.array([False, False, False]),
    )

    I_syn = np.zeros(3)
    I_ext = np.zeros(3)

    # AdEx should detect the NaN and raise error (fail-fast)
    with pytest.raises((ValueError, RuntimeError)):
        adex_step(state, params, 0.1, I_syn, I_ext)


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_detects_inf_in_inputs() -> None:
    """Test that AdEx detects and rejects inf in input currents.

    Chaos scenario: Inf corruption in external current.
    Expected behavior: System should detect inf and raise ValueError.
    """
    params = AdExParams()

    state = AdExState(
        V_mV=np.array([-65.0, -70.0]),
        w_pA=np.array([50.0, 30.0]),
        spiked=np.array([False, False]),
    )

    # Inject inf into external current
    I_syn = np.array([0.0, 0.0])
    I_ext = np.array([np.inf, 100.0])

    # AdEx should detect the inf and raise error (fail-fast)
    with pytest.raises((ValueError, RuntimeError)):
        adex_step(state, params, 0.1, I_syn, I_ext)


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_rejects_invalid_dt() -> None:
    """Test that AdEx rejects invalid dt values.

    Chaos scenario: Extreme dt jitter (negative, zero, or very large).
    Expected behavior: System should raise ValueError for invalid dt.
    """
    params = AdExParams()

    state = AdExState(
        V_mV=np.array([-65.0]),
        w_pA=np.array([50.0]),
        spiked=np.array([False]),
    )

    I_syn = np.zeros(1)
    I_ext = np.zeros(1)

    # Test negative dt
    with pytest.raises(ValueError):
        adex_step(state, params, -0.1, I_syn, I_ext)

    # Test zero dt
    with pytest.raises(ValueError):
        adex_step(state, params, 0.0, I_syn, I_ext)

    # Test extremely large dt (should raise or produce invalid results)
    with pytest.raises((ValueError, RuntimeError)):
        adex_step(state, params, 1000.0, I_syn, I_ext)


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_produces_valid_output_under_normal_conditions() -> None:
    """Test that AdEx produces valid (finite) outputs under normal conditions.

    This is a control test: without faults, output should always be valid.
    """
    params = AdExParams()

    state = AdExState(
        V_mV=np.array([-65.0, -70.0, -60.0]),
        w_pA=np.array([50.0, 30.0, 100.0]),
        spiked=np.array([False, False, False]),
    )

    I_syn = np.array([10.0, 5.0, 20.0])
    I_ext = np.array([100.0, 50.0, 150.0])

    # Should complete without error
    result = adex_step(state, params, 0.1, I_syn, I_ext)

    # Validate outputs are finite
    validate_numeric_health(result.V_mV, "V_mV")
    validate_numeric_health(result.w_pA, "w_pA")

    # All values should be finite
    assert np.all(np.isfinite(result.V_mV))
    assert np.all(np.isfinite(result.w_pA))


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_with_injected_nan_in_state_array() -> None:
    """Test AdEx behavior when NaN is injected into state during execution.

    Chaos scenario: Fault injection corrupts state mid-execution.
    Expected behavior: Subsequent steps should detect corruption.
    """
    config = FaultConfig(enabled=True, seed=42, probability=1.0)
    params = AdExParams()

    # Start with valid state
    state = AdExState(
        V_mV=np.array([-65.0, -70.0]),
        w_pA=np.array([50.0, 30.0]),
        spiked=np.array([False, False]),
    )

    # Run one normal step
    I_syn = np.array([10.0, 5.0])
    I_ext = np.array([100.0, 50.0])

    state = adex_step(state, params, 0.1, I_syn, I_ext)

    # Now inject NaN into voltage
    with inject_numeric_fault(config, "nan") as inject:
        state.V_mV = inject(state.V_mV)

    # Verify NaN was injected
    assert np.any(np.isnan(state.V_mV))

    # Next step should detect the NaN
    with pytest.raises((ValueError, RuntimeError)):
        adex_step(state, params, 0.1, I_syn, I_ext)


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_survives_mild_dt_jitter() -> None:
    """Test that AdEx produces reasonable results with mild dt jitter.

    Chaos scenario: Small dt variations (±5%) simulating timing noise.
    Expected behavior: System should complete without errors, outputs remain valid.
    """
    params = AdExParams()

    state = AdExState(
        V_mV=np.array([-65.0]),
        w_pA=np.array([50.0]),
        spiked=np.array([False]),
    )

    I_syn = np.array([10.0])
    I_ext = np.array([100.0])

    # Run 10 steps with mild jitter
    rng = np.random.default_rng(42)

    for _ in range(10):
        # Add ±5% jitter to dt
        dt_jitter = 0.1 * (1.0 + rng.uniform(-0.05, 0.05))

        # Should complete without error
        state = adex_step(state, params, dt_jitter, I_syn, I_ext)

        # Outputs should remain finite
        assert np.all(np.isfinite(state.V_mV))
        assert np.all(np.isfinite(state.w_pA))


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_state_shape_mismatch_detected() -> None:
    """Test that AdEx detects shape mismatches in inputs.

    Chaos scenario: Input arrays with wrong shapes.
    Expected behavior: Should raise ValueError for shape mismatch.
    """
    params = AdExParams()

    state = AdExState(
        V_mV=np.array([-65.0, -70.0]),
        w_pA=np.array([50.0, 30.0]),
        spiked=np.array([False, False]),
    )

    # Wrong shape for I_syn (should be size 2, is size 3)
    I_syn = np.array([10.0, 5.0, 20.0])
    I_ext = np.array([100.0, 50.0])

    # Should detect shape mismatch
    with pytest.raises((ValueError, RuntimeError)):
        adex_step(state, params, 0.1, I_syn, I_ext)


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_bounds_enforcement() -> None:
    """Test that AdEx enforces reasonable bounds on state variables.

    Chaos scenario: Extreme initial conditions.
    Expected behavior: System should either reject or safely handle extremes.
    """
    params = AdExParams()

    # Extreme voltage (way beyond spike threshold)
    state_extreme = AdExState(
        V_mV=np.array([1000.0]),  # Extremely high voltage
        w_pA=np.array([50.0]),
        spiked=np.array([False]),
    )

    I_syn = np.zeros(1)
    I_ext = np.zeros(1)

    # Should either reject extreme state or produce valid finite output
    with contextlib.suppress(ValueError):
        result = adex_step(state_extreme, params, 0.1, I_syn, I_ext)
        assert np.all(np.isfinite(result.V_mV))
        assert np.all(np.isfinite(result.w_pA))


@pytest.mark.validation
@pytest.mark.chaos
def test_adex_determinism_under_chaos() -> None:
    """Test that AdEx is deterministic even with identical fault injection.

    Chaos scenario: Same fault injection seed should produce identical results.
    Expected behavior: Deterministic chaos (same seed → same outcome).
    """
    config = FaultConfig(enabled=True, seed=100, probability=0.3)
    params = AdExParams()

    # Run 1
    state1 = AdExState(
        V_mV=np.array([-65.0, -70.0, -60.0]),
        w_pA=np.array([50.0, 30.0, 100.0]),
        spiked=np.array([False, False, False]),
    )

    I_syn = np.array([10.0, 5.0, 20.0])
    I_ext = np.array([100.0, 50.0, 150.0])

    with inject_numeric_fault(config, "nan") as inject:
        I_syn_corrupted1 = inject(I_syn)

    # If no NaN was injected, run step
    if not np.any(np.isnan(I_syn_corrupted1)):
        result1 = adex_step(state1, params, 0.1, I_syn_corrupted1, I_ext)
    else:
        result1 = None  # NaN was injected

    # Run 2 with same seed
    config2 = FaultConfig(enabled=True, seed=100, probability=0.3)
    state2 = AdExState(
        V_mV=np.array([-65.0, -70.0, -60.0]),
        w_pA=np.array([50.0, 30.0, 100.0]),
        spiked=np.array([False, False, False]),
    )

    with inject_numeric_fault(config2, "nan") as inject:
        I_syn_corrupted2 = inject(I_syn)

    # Same injection pattern
    assert np.array_equal(np.isnan(I_syn_corrupted1), np.isnan(I_syn_corrupted2))

    # If both had no NaN, results should be identical
    if result1 is not None:
        if not np.any(np.isnan(I_syn_corrupted2)):
            result2 = adex_step(state2, params, 0.1, I_syn_corrupted2, I_ext)
            np.testing.assert_array_equal(result1.V_mV, result2.V_mV)
            np.testing.assert_array_equal(result1.w_pA, result2.w_pA)
