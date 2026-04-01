"""Chaos engineering tests for stochastic fault resilience.

Tests system behavior when RNG state is perturbed to detect determinism violations.
"""

from __future__ import annotations

import pytest

from bnsyn.testing import FaultConfig, inject_stochastic_fault


@pytest.mark.validation
@pytest.mark.chaos
def test_stochastic_fault_injection() -> None:
    """Test that stochastic fault forces RNG reseed."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_stochastic_fault(config) as reseed:
        # Should return a new seed
        new_seed = reseed(None)
        assert new_seed is not None
        assert isinstance(new_seed, int)


@pytest.mark.validation
@pytest.mark.chaos
def test_stochastic_fault_deterministic() -> None:
    """Test that stochastic fault is deterministic with same seed."""
    config = FaultConfig(enabled=True, seed=100, probability=1.0)

    with inject_stochastic_fault(config) as reseed1:
        new_seed1 = reseed1(None)

    # Reset with same seed
    config2 = FaultConfig(enabled=True, seed=100, probability=1.0)
    with inject_stochastic_fault(config2) as reseed2:
        new_seed2 = reseed2(None)

    # Should produce same new seed
    assert new_seed1 == new_seed2


@pytest.mark.validation
@pytest.mark.chaos
def test_stochastic_fault_disabled() -> None:
    """Test that stochastic fault can be disabled."""
    config = FaultConfig(enabled=False, seed=42, probability=1.0)

    with inject_stochastic_fault(config) as reseed:
        # Should not inject fault
        result = reseed(None)
        assert result is None


@pytest.mark.validation
@pytest.mark.chaos
def test_stochastic_fault_probability() -> None:
    """Test that stochastic fault respects probability."""
    # With probability 0, should never inject
    config = FaultConfig(enabled=True, seed=42, probability=0.0)

    with inject_stochastic_fault(config) as reseed:
        for _ in range(10):
            result = reseed(None)
            assert result is None


@pytest.mark.validation
@pytest.mark.chaos
def test_stochastic_fault_different_seeds() -> None:
    """Test that multiple stochastic faults produce different seeds."""
    config = FaultConfig(enabled=True, seed=42, probability=1.0)

    with inject_stochastic_fault(config) as reseed:
        seeds = [reseed(None) for _ in range(10)]

        # All should be valid integers
        assert all(isinstance(s, int) for s in seeds)
        # Should have variety in seeds
        unique_seeds = set(seeds)
        assert len(unique_seeds) > 1
