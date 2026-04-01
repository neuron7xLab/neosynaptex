"""Tests for fault injection utilities."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.testing.faults import (
    FaultConfig,
    clamp_numeric,
    inject_io_fault,
    inject_numeric_fault,
    inject_stochastic_fault,
    inject_timing_fault,
    validate_numeric_health,
)


def test_inject_numeric_fault_nan() -> None:
    config = FaultConfig(enabled=True, seed=1, probability=1.0)
    with inject_numeric_fault(config, "nan") as inject:
        arr = np.array([1.0, 2.0, 3.0])
        faulty = inject(arr)
    assert np.isnan(faulty).any()
    with pytest.raises(ValueError, match="contains NaN"):
        validate_numeric_health(faulty, name="weights")


def test_inject_numeric_fault_inf() -> None:
    config = FaultConfig(enabled=True, seed=2, probability=1.0)
    with inject_numeric_fault(config, "inf") as inject:
        arr = np.array([1.0, 2.0, 3.0])
        faulty = inject(arr)
    assert np.isinf(faulty).any()
    with pytest.raises(ValueError, match="contains inf"):
        validate_numeric_health(faulty, name="weights")


def test_inject_numeric_fault_neg_inf() -> None:
    config = FaultConfig(enabled=True, seed=6, probability=1.0)
    with inject_numeric_fault(config, "neg_inf") as inject:
        arr = np.array([1.0, 2.0, 3.0])
        faulty = inject(arr)
    assert np.isneginf(faulty).any()


def test_clamp_numeric_replaces_invalid() -> None:
    arr = np.array([np.nan, np.inf, -np.inf, 0.5])
    clamped = clamp_numeric(arr, min_val=-1.0, max_val=1.0)
    np.testing.assert_allclose(clamped, np.array([-1.0, 1.0, -1.0, 0.5]))


def test_inject_timing_fault_bounds() -> None:
    config = FaultConfig(enabled=True, seed=3, probability=1.0)
    with inject_timing_fault(config, jitter_factor=0.2) as inject:
        dt = 0.1
        jittered = inject(dt)
    assert 0.08 <= jittered <= 0.12


def test_inject_faults_disabled_paths_return_inputs() -> None:
    config = FaultConfig(enabled=True, seed=10, probability=0.0)
    arr = np.array([1.0, 2.0, 3.0])
    with inject_numeric_fault(config, "nan") as inject:
        returned = inject(arr)
    assert returned is arr

    with inject_timing_fault(config, jitter_factor=0.2) as inject:
        dt = 0.1
        returned_dt = inject(dt)
    assert returned_dt == dt


def test_inject_stochastic_fault_behavior() -> None:
    config = FaultConfig(enabled=True, seed=4, probability=1.0)
    with inject_stochastic_fault(config) as reseed:
        new_seed = reseed({"state": 1})
    assert new_seed is not None

    disabled = FaultConfig(enabled=False, seed=4, probability=1.0)
    with inject_stochastic_fault(disabled) as reseed:
        assert reseed({"state": 1}) is None


def test_inject_io_fault_modes() -> None:
    config = FaultConfig(enabled=True, seed=5, probability=1.0)
    with inject_io_fault(config, "silent_fail") as fail:
        assert fail("out.json") is False

    with inject_io_fault(config, "corrupt") as fail:
        assert fail("out.json") is False

    with inject_io_fault(config, "exception") as fail:
        with pytest.raises(IOError, match="Simulated I/O fault"):
            fail("out.json")

    disabled = FaultConfig(enabled=False, seed=5, probability=1.0)
    with inject_io_fault(disabled, "silent_fail") as fail:
        assert fail("out.json") is True
