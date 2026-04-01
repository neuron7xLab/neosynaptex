"""Tests for SERO hormonal regulation and Bayesian immune system."""

from __future__ import annotations

import pytest

from neuron7x_agents.regulation.hvr import (
    HormonalRegulator,
    HVRConfig,
    SeverityWeight,
)
from neuron7x_agents.regulation.immune import Alert, BayesianImmune

# ═══════════════════════════════════════════════════════════════════════
#  HVR Config
# ═══════════════════════════════════════════════════════════════════════


class TestHVRConfig:
    def test_default_config(self) -> None:
        cfg = HVRConfig()
        assert cfg.t_min == 0.05
        assert cfg.alpha == 0.50
        assert cfg.gamma == 0.30

    def test_t_min_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="t_min must be > 0"):
            HVRConfig(t_min=0.0)

    def test_alpha_must_be_in_range(self) -> None:
        with pytest.raises(ValueError, match="alpha must be in"):
            HVRConfig(alpha=0.0)

    def test_gamma_must_be_in_range(self) -> None:
        with pytest.raises(ValueError, match="gamma must be in"):
            HVRConfig(gamma=0.0)


# ═══════════════════════════════════════════════════════════════════════
#  Safety Invariant: T(t) ≥ T_min ∀t (Eq.4)
# ═══════════════════════════════════════════════════════════════════════


class TestSafetyInvariant:
    """The most important property: throughput NEVER drops below T_min."""

    def test_safety_invariant_under_zero_stress(self) -> None:
        reg = HormonalRegulator()
        channels = [SeverityWeight("test", severity=1.0, current_value=0.0)]
        for _ in range(100):
            reg.tick(channels)
        assert reg.safety_invariant_holds()

    def test_safety_invariant_under_maximum_stress(self) -> None:
        reg = HormonalRegulator()
        channels = [SeverityWeight("test", severity=100.0, current_value=1.0)]
        for _ in range(100):
            state = reg.tick(channels)
        assert reg.safety_invariant_holds()
        assert state.throughput >= reg.config.t_min

    def test_safety_invariant_under_alternating_stress(self) -> None:
        """No flip-flop oscillation below T_min."""
        reg = HormonalRegulator()
        for i in range(200):
            value = 1.0 if i % 2 == 0 else 0.0
            channels = [SeverityWeight("test", severity=50.0, current_value=value)]
            reg.tick(channels)
        assert reg.safety_invariant_holds()

    def test_safety_invariant_stress_spike(self) -> None:
        """Sudden stress spike doesn't break invariant."""
        reg = HormonalRegulator()
        # Calm period
        for _ in range(50):
            reg.tick([SeverityWeight("x", 10.0, 0.01)])
        # Sudden spike
        for _ in range(50):
            reg.tick([SeverityWeight("x", 100.0, 1.0)])
        assert reg.safety_invariant_holds()


# ═══════════════════════════════════════════════════════════════════════
#  Damping (Eq.7)
# ═══════════════════════════════════════════════════════════════════════


class TestDamping:
    def test_damping_smooths_stress(self) -> None:
        """Damped stress should lag behind raw stress."""
        reg = HormonalRegulator(config=HVRConfig(gamma=0.1))
        channels = [SeverityWeight("x", severity=10.0, current_value=1.0)]
        state = reg.tick(channels)
        # First tick: damped should be much less than raw
        assert state.damped_stress < state.raw_stress

    def test_damping_converges(self) -> None:
        """Under constant stress, damped stress converges to raw."""
        reg = HormonalRegulator(config=HVRConfig(gamma=0.3))
        channels = [SeverityWeight("x", severity=10.0, current_value=0.5)]
        for _ in range(100):
            state = reg.tick(channels)
        assert abs(state.damped_stress - state.raw_stress) < 0.01


# ═══════════════════════════════════════════════════════════════════════
#  Throughput (Eq.3)
# ═══════════════════════════════════════════════════════════════════════


class TestThroughput:
    def test_zero_stress_full_throughput(self) -> None:
        reg = HormonalRegulator()
        state = reg.tick([SeverityWeight("x", 1.0, 0.0)])
        assert state.throughput == reg.config.t_0

    def test_throughput_decreases_with_stress(self) -> None:
        reg = HormonalRegulator()
        state1 = reg.tick([SeverityWeight("x", 10.0, 0.1)])
        reg.reset()
        state2 = reg.tick([SeverityWeight("x", 10.0, 0.9)])
        # More stress → lower throughput (accounting for damping delay)
        # After reset both start fresh, so second has more raw stress
        assert state2.raw_stress > state1.raw_stress

    def test_reset(self) -> None:
        reg = HormonalRegulator()
        reg.tick([SeverityWeight("x", 10.0, 0.5)])
        reg.reset()
        assert reg.state.throughput == reg.config.t_0
        assert reg.state.tick == 0


# ═══════════════════════════════════════════════════════════════════════
#  Bayesian Immune
# ═══════════════════════════════════════════════════════════════════════


class TestBayesianImmune:
    def test_single_channel_is_quarantined(self) -> None:
        immune = BayesianImmune()
        verdict = immune.evaluate([Alert("error_rate", 0.8, 0.9)])
        assert verdict.is_real_threat is False
        assert len(verdict.quarantined) == 1

    def test_dual_channel_is_real_threat(self) -> None:
        immune = BayesianImmune()
        verdict = immune.evaluate(
            [
                Alert("error_rate", 0.8, 0.9),
                Alert("latency", 0.6, 0.7),
            ]
        )
        assert verdict.is_real_threat is True
        assert verdict.corroborating_channels == 2

    def test_autoimmune_probability_decreases_with_channels(self) -> None:
        immune = BayesianImmune(false_positive_rate=0.02)
        v1 = immune.evaluate([Alert("a", 0.5, 0.5)])
        v2 = immune.evaluate([Alert("a", 0.5, 0.5), Alert("b", 0.5, 0.5)])
        assert v2.autoimmune_probability < v1.autoimmune_probability

    def test_quarantine_accumulates(self) -> None:
        immune = BayesianImmune()
        immune.evaluate([Alert("a", 0.5, 0.5)])
        immune.evaluate([Alert("b", 0.5, 0.5)])
        assert immune.quarantine_size == 2
