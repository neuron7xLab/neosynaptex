"""Chaos engineering tests for I/O fault resilience.

Tests graceful degradation when I/O operations fail.
"""

from __future__ import annotations

import pytest

from bnsyn.testing import FaultConfig, inject_io_fault


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_injection_silent_fail() -> None:
    """Test that I/O silent failure is injected correctly."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_io_fault(config, "silent_fail") as fail:
        success = fail("output.json")
        # Should indicate failure
        assert not success


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_injection_exception() -> None:
    """Test that I/O exception mode raises IOError."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_io_fault(config, "exception") as fail:
        with pytest.raises(IOError, match="Simulated I/O fault"):
            fail("output.json")


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_deterministic() -> None:
    """Test that I/O fault injection is deterministic with same seed."""
    config = FaultConfig(enabled=True, seed=100, probability=1.0)

    with inject_io_fault(config, "silent_fail") as fail1:
        result1 = fail1("output.json")

    # Reset with same seed
    config2 = FaultConfig(enabled=True, seed=100, probability=1.0)
    with inject_io_fault(config2, "silent_fail") as fail2:
        result2 = fail2("output.json")

    # Should produce same result
    assert result1 == result2


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_disabled() -> None:
    """Test that I/O fault injection can be disabled."""
    config = FaultConfig(enabled=False, seed=42, probability=1.0)

    with inject_io_fault(config, "silent_fail") as fail:
        success = fail("output.json")
        # Should succeed (no fault injected)
        assert success


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_probability() -> None:
    """Test that I/O fault injection respects probability."""
    # With probability 0, should never inject fault
    config = FaultConfig(enabled=True, seed=42, probability=0.0)

    with inject_io_fault(config, "silent_fail") as fail:
        for _ in range(10):
            success = fail("output.json")
            assert success  # Should always succeed


@pytest.mark.validation
@pytest.mark.chaos
def test_io_fault_corrupt_mode() -> None:
    """Test that I/O corrupt mode returns False."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_io_fault(config, "corrupt") as fail:
        success = fail("output.json")
        # Should indicate corruption/failure
        assert not success
