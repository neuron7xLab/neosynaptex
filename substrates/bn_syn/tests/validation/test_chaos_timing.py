"""Chaos engineering tests for timing fault resilience.

Tests system behavior when timing jitter is injected into dt values.
"""

from __future__ import annotations

import pytest

from bnsyn.testing import FaultConfig, inject_timing_fault


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_injection() -> None:
    """Test that timing jitter is injected into dt values."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)
    dt = 0.1

    with inject_timing_fault(config, jitter_factor=0.1) as inject:
        dt_jittered = inject(dt)

        # Should be different due to jitter
        assert dt_jittered != dt
        # Should be within ±10% of original
        assert abs(dt_jittered - dt) <= dt * 0.1


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_deterministic() -> None:
    """Test that timing fault injection is deterministic with same seed."""
    config = FaultConfig(enabled=True, seed=100, probability=1.0)
    dt = 0.1

    with inject_timing_fault(config, jitter_factor=0.1) as inject1:
        dt_jittered1 = inject1(dt)

    # Reset with same seed
    config2 = FaultConfig(enabled=True, seed=100, probability=1.0)
    with inject_timing_fault(config2, jitter_factor=0.1) as inject2:
        dt_jittered2 = inject2(dt)

    # Should produce same jitter
    assert dt_jittered1 == dt_jittered2


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_disabled() -> None:
    """Test that timing fault injection can be disabled."""
    config = FaultConfig(enabled=False, seed=42, probability=1.0)
    dt = 0.1

    with inject_timing_fault(config, jitter_factor=0.1) as inject:
        dt_result = inject(dt)

        # Should not inject jitter
        assert dt_result == dt


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_probability() -> None:
    """Test that timing fault injection respects probability."""
    # With probability 0, should never inject
    config = FaultConfig(enabled=True, seed=42, probability=0.0)
    dt = 0.1

    with inject_timing_fault(config, jitter_factor=0.1) as inject:
        for _ in range(10):
            dt_result = inject(dt)
            assert dt_result == dt


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_jitter_bounds() -> None:
    """Test that jitter stays within specified bounds."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)
    dt = 1.0
    jitter_factor = 0.2  # ±20%

    with inject_timing_fault(config, jitter_factor=jitter_factor) as inject:
        for _ in range(100):
            dt_jittered = inject(dt)
            # Should be within bounds
            assert dt * (1 - jitter_factor) <= dt_jittered <= dt * (1 + jitter_factor)


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_preserves_positivity() -> None:
    """Test that timing fault never produces negative dt."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)
    dt = 0.01
    jitter_factor = 0.5  # Large jitter

    with inject_timing_fault(config, jitter_factor=jitter_factor) as inject:
        for _ in range(100):
            dt_jittered = inject(dt)
            # dt should always remain positive
            assert dt_jittered > 0


@pytest.mark.validation
@pytest.mark.chaos
def test_timing_fault_multiple_injections() -> None:
    """Test that multiple injections produce different values (when enabled)."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)
    dt = 0.1

    with inject_timing_fault(config, jitter_factor=0.1) as inject:
        # Multiple injections should produce different jitter values
        values = [inject(dt) for _ in range(10)]

        # At least some should be different (stochastic test)
        unique_values = set(values)
        assert len(unique_values) > 1
