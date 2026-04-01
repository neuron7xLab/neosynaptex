"""Chaos engineering tests for numeric fault resilience.

Tests system behavior when NaN, inf, and other numeric faults are injected
into critical paths.
"""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.testing import FaultConfig, clamp_numeric, inject_numeric_fault, validate_numeric_health


@pytest.mark.validation
@pytest.mark.chaos
def test_numeric_fault_injection_nan() -> None:
    """Test that NaN injection is detected and handled correctly."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_numeric_fault(config, "nan") as inject:
        weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        faulty_weights = inject(weights)

        # Should contain at least one NaN
        assert np.any(np.isnan(faulty_weights))
        assert not np.all(np.isnan(faulty_weights))  # Not all should be NaN


@pytest.mark.validation
@pytest.mark.chaos
def test_numeric_fault_injection_inf() -> None:
    """Test that inf injection is detected and handled correctly."""
    config = FaultConfig(enabled=True, seed=43, probability=1.0)

    with inject_numeric_fault(config, "inf") as inject:
        weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        faulty_weights = inject(weights)

        # Should contain at least one inf
        assert np.any(np.isinf(faulty_weights))


@pytest.mark.validation
@pytest.mark.chaos
def test_numeric_health_validation_detects_nan() -> None:
    """Test that numeric health validation catches NaN values."""
    arr_with_nan = np.array([1.0, 2.0, np.nan, 4.0])

    with pytest.raises(ValueError, match="contains NaN"):
        validate_numeric_health(arr_with_nan)


@pytest.mark.validation
@pytest.mark.chaos
def test_numeric_health_validation_detects_inf() -> None:
    """Test that numeric health validation catches inf values."""
    arr_with_inf = np.array([1.0, 2.0, np.inf, 4.0])

    with pytest.raises(ValueError, match="contains inf"):
        validate_numeric_health(arr_with_inf)


@pytest.mark.validation
@pytest.mark.chaos
def test_numeric_health_validation_passes_clean() -> None:
    """Test that numeric health validation passes for clean arrays."""
    clean_arr = np.array([1.0, 2.0, 3.0, 4.0])

    # Should not raise
    validate_numeric_health(clean_arr)


@pytest.mark.validation
@pytest.mark.chaos
def test_clamp_numeric_handles_nan() -> None:
    """Test that clamping replaces NaN values with minimum bound."""
    arr_with_nan = np.array([1.0, 2.0, np.nan, 4.0])
    clamped = clamp_numeric(arr_with_nan, 0.0, 10.0)

    assert not np.any(np.isnan(clamped))
    assert np.all((clamped >= 0.0) & (clamped <= 10.0))


@pytest.mark.validation
@pytest.mark.chaos
def test_clamp_numeric_handles_inf() -> None:
    """Test that clamping replaces inf values with maximum bound."""
    arr_with_inf = np.array([1.0, 2.0, np.inf, -np.inf, 4.0])
    clamped = clamp_numeric(arr_with_inf, 0.0, 10.0)

    assert not np.any(np.isinf(clamped))
    assert np.all((clamped >= 0.0) & (clamped <= 10.0))


@pytest.mark.validation
@pytest.mark.chaos
def test_fault_injection_deterministic() -> None:
    """Test that fault injection is deterministic with same seed."""
    config = FaultConfig(enabled=True, seed=100, probability=1.0)

    with inject_numeric_fault(config, "nan") as inject1:
        arr1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        faulty1 = inject1(arr1)

    # Reset with same seed
    config2 = FaultConfig(enabled=True, seed=100, probability=1.0)
    with inject_numeric_fault(config2, "nan") as inject2:
        arr2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        faulty2 = inject2(arr2)

    # Should inject fault at same location
    nan_mask1 = np.isnan(faulty1)
    nan_mask2 = np.isnan(faulty2)
    assert np.array_equal(nan_mask1, nan_mask2)


@pytest.mark.validation
@pytest.mark.chaos
def test_fault_injection_disabled() -> None:
    """Test that fault injection can be disabled."""
    config = FaultConfig(enabled=False, seed=42, probability=1.0)

    with inject_numeric_fault(config, "nan") as inject:
        weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = inject(weights)

        # Should not inject any faults
        assert not np.any(np.isnan(result))
        assert np.array_equal(result, weights)


@pytest.mark.validation
@pytest.mark.chaos
def test_fault_injection_probability() -> None:
    """Test that fault injection respects probability parameter."""
    # With probability 0, should never inject
    config_zero = FaultConfig(enabled=True, seed=42, probability=0.0)

    with inject_numeric_fault(config_zero, "nan") as inject:
        for _ in range(10):
            weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
            result = inject(weights)
            assert not np.any(np.isnan(result))
