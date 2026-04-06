"""Tests for core.objection_energy_budget — OEB controller (Task 3)."""

from __future__ import annotations

import numpy as np
import pytest

from core.coherence_state_space import (
    CoherenceState,
    CoherenceStateSpace,
)
from core.objection_energy_budget import (
    ObjectionBudget,
    OEBController,
    simulate_with_oeb,
)

# ── ObjectionBudget construction ───────────────────────────────────────


class TestObjectionBudget:
    def test_construction(self) -> None:
        b = ObjectionBudget(energy_total=10.0, energy_spent=3.0, critic_gain=1.5, cycle=0)
        assert b.energy_total == 10.0
        assert b.energy_spent == 3.0
        assert b.critic_gain == 1.5
        assert b.cycle == 0

    def test_energy_remaining(self) -> None:
        b = ObjectionBudget(energy_total=10.0, energy_spent=3.0, critic_gain=1.0, cycle=0)
        assert b.energy_remaining == pytest.approx(7.0)

    def test_energy_remaining_clamped(self) -> None:
        b = ObjectionBudget(energy_total=5.0, energy_spent=6.0, critic_gain=1.0, cycle=0)
        assert b.energy_remaining == 0.0

    def test_frozen(self) -> None:
        b = ObjectionBudget(energy_total=10.0, energy_spent=0.0, critic_gain=1.0, cycle=0)
        with pytest.raises(AttributeError):
            b.energy_total = 5.0  # type: ignore[misc]

    def test_negative_energy_total_rejected(self) -> None:
        with pytest.raises(ValueError, match="energy_total"):
            ObjectionBudget(energy_total=-1.0, energy_spent=0.0, critic_gain=1.0, cycle=0)

    def test_negative_critic_gain_rejected(self) -> None:
        with pytest.raises(ValueError, match="critic_gain"):
            ObjectionBudget(energy_total=1.0, energy_spent=0.0, critic_gain=-0.1, cycle=0)

    def test_negative_cycle_rejected(self) -> None:
        with pytest.raises(ValueError, match="cycle"):
            ObjectionBudget(energy_total=1.0, energy_spent=0.0, critic_gain=1.0, cycle=-1)


# ── OEBController construction ────────────────────────────────────────


class TestOEBControllerConstruction:
    def test_defaults(self) -> None:
        c = OEBController()
        assert c.energy_per_cycle == 10.0
        assert c.min_gain == 0.1
        assert c.max_gain == 5.0

    def test_negative_energy_rejected(self) -> None:
        with pytest.raises(ValueError, match="energy_per_cycle"):
            OEBController(energy_per_cycle=-1.0)

    def test_max_lt_min_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_gain"):
            OEBController(min_gain=5.0, max_gain=1.0)

    def test_zero_dt_rejected(self) -> None:
        with pytest.raises(ValueError, match="dt"):
            OEBController(dt=0.0)


# ── PID behaviour ─────────────────────────────────────────────────────


class TestPIDBehaviour:
    def test_high_halluc_increases_gain(self) -> None:
        """When hallucination rate is well above target, gain should rise."""
        c = OEBController(gain_kp=2.0, gain_ki=0.0, gain_kd=0.0, energy_per_cycle=100.0)
        initial_gain = c.critic_gain
        # Feed high halluc, zero false reject for several steps
        for _ in range(10):
            c.step(hallucination_rate=0.5, false_reject_rate=0.0)
        assert c.critic_gain > initial_gain

    def test_high_false_reject_decreases_gain(self) -> None:
        """When false_reject_rate is high and halluc is at target, gain should drop."""
        c = OEBController(gain_kp=2.0, gain_ki=0.0, gain_kd=0.0, energy_per_cycle=100.0)
        initial_gain = c.critic_gain
        for _ in range(10):
            c.step(hallucination_rate=0.05, false_reject_rate=0.5)
        assert c.critic_gain < initial_gain

    def test_gain_clamped_to_range(self) -> None:
        """Gain never exceeds [min_gain, max_gain]."""
        c = OEBController(
            gain_kp=10.0,
            gain_ki=0.0,
            gain_kd=0.0,
            min_gain=0.5,
            max_gain=3.0,
            energy_per_cycle=1000.0,
        )
        for _ in range(50):
            c.step(hallucination_rate=1.0, false_reject_rate=0.0)
        assert c.critic_gain <= 3.0
        # Now drive gain down
        for _ in range(50):
            c.step(hallucination_rate=0.0, false_reject_rate=1.0)
        assert c.critic_gain >= 0.5


# ── Energy budget depletion ───────────────────────────────────────────


class TestEnergyDepletion:
    def test_energy_depleted_clamps_to_min(self) -> None:
        """Once energy is exhausted, critic_gain is forced to min_gain."""
        c = OEBController(
            energy_per_cycle=1.0,
            min_gain=0.2,
            max_gain=5.0,
            dt=0.1,
            gain_kp=5.0,
            gain_ki=0.0,
            gain_kd=0.0,
        )
        budgets: list[ObjectionBudget] = []
        for _ in range(200):
            b = c.step(hallucination_rate=0.8, false_reject_rate=0.0)
            budgets.append(b)
        last = budgets[-1]
        assert last.energy_remaining == 0.0
        assert last.critic_gain == pytest.approx(0.2)

    def test_energy_monotonically_increases(self) -> None:
        c = OEBController(energy_per_cycle=50.0)
        prev = 0.0
        for _ in range(20):
            b = c.step(0.1, 0.01)
            assert b.energy_spent >= prev
            prev = b.energy_spent


# ── Cycle reset ───────────────────────────────────────────────────────


class TestCycleReset:
    def test_reset_restores_budget(self) -> None:
        c = OEBController(energy_per_cycle=5.0)
        for _ in range(10):
            c.step(0.1, 0.01)
        assert c.energy_spent > 0.0
        old_cycle = c.cycle
        c.reset_cycle()
        assert c.energy_spent == 0.0
        assert c.cycle == old_cycle + 1


# ── Rollout ───────────────────────────────────────────────────────────


class TestRollout:
    def test_rollout_length(self) -> None:
        c = OEBController(energy_per_cycle=100.0)
        n = 15
        budgets = c.rollout([0.1] * n, [0.01] * n)
        assert len(budgets) == n

    def test_rollout_energy_monotonic(self) -> None:
        c = OEBController(energy_per_cycle=100.0)
        budgets = c.rollout([0.1] * 20, [0.01] * 20)
        energies = [b.energy_spent for b in budgets]
        for i in range(1, len(energies)):
            assert energies[i] >= energies[i - 1]

    def test_rollout_mismatched_lengths(self) -> None:
        c = OEBController()
        with pytest.raises(ValueError):
            c.rollout([0.1, 0.2], [0.01])


# ── Pareto point ──────────────────────────────────────────────────────


class TestParetoPoint:
    def test_pareto_returns_valid_values(self) -> None:
        c = OEBController(energy_per_cycle=50.0)
        c.step(0.1, 0.02)
        quality, cost, gain = c.pareto_point()
        assert 0.0 <= quality <= 1.0
        assert cost >= 0.0
        assert gain >= c.min_gain
        assert gain <= c.max_gain

    def test_pareto_quality_reflects_halluc(self) -> None:
        c = OEBController(energy_per_cycle=50.0)
        c.step(0.3, 0.0)
        quality, _, _ = c.pareto_point()
        assert quality == pytest.approx(0.7)


# ── simulate_with_oeb ────────────────────────────────────────────────


class TestSimulateWithOEB:
    def test_trajectory_shape(self) -> None:
        model = CoherenceStateSpace()
        oeb = OEBController(energy_per_cycle=50.0)
        x0 = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3)
        rng = np.random.default_rng(42)
        traj, budgets = simulate_with_oeb(model, oeb, x0, n_steps=20, rng=rng)
        assert traj.shape == (21, 4)
        assert len(budgets) == 20

    def test_trajectory_initial_state(self) -> None:
        model = CoherenceStateSpace()
        oeb = OEBController(energy_per_cycle=50.0)
        x0 = CoherenceState(S=0.6, gamma=1.0, E_obj=0.0, sigma2=1e-3)
        traj, _ = simulate_with_oeb(model, oeb, x0, n_steps=5)
        np.testing.assert_array_almost_equal(traj[0], x0.as_vector())

    def test_deterministic_given_same_seed(self) -> None:
        model = CoherenceStateSpace()
        x0 = CoherenceState(S=0.4, gamma=1.1, E_obj=0.05, sigma2=1e-3)

        oeb1 = OEBController(energy_per_cycle=50.0)
        traj1, bud1 = simulate_with_oeb(model, oeb1, x0, 10, np.random.default_rng(99))

        oeb2 = OEBController(energy_per_cycle=50.0)
        traj2, bud2 = simulate_with_oeb(model, oeb2, x0, 10, np.random.default_rng(99))

        np.testing.assert_array_equal(traj1, traj2)
        for b1, b2 in zip(bud1, bud2):
            assert b1.critic_gain == b2.critic_gain
            assert b1.energy_spent == b2.energy_spent

    def test_n_steps_zero(self) -> None:
        model = CoherenceStateSpace()
        oeb = OEBController()
        x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3)
        traj, budgets = simulate_with_oeb(model, oeb, x0, 0)
        assert traj.shape == (1, 4)
        assert len(budgets) == 0

    def test_negative_n_steps_rejected(self) -> None:
        model = CoherenceStateSpace()
        oeb = OEBController()
        x0 = CoherenceState(S=0.5, gamma=1.0, E_obj=0.0, sigma2=1e-3)
        with pytest.raises(ValueError, match="n_steps"):
            simulate_with_oeb(model, oeb, x0, -1)


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_energy_budget(self) -> None:
        """With zero energy, gain should immediately clamp to min."""
        c = OEBController(energy_per_cycle=0.0, min_gain=0.1, max_gain=5.0)
        b = c.step(0.5, 0.0)
        assert b.critic_gain == pytest.approx(0.1)
        assert b.energy_remaining == 0.0

    def test_zero_rates(self) -> None:
        """Zero hallucination and false-reject rates should not crash."""
        c = OEBController(energy_per_cycle=50.0)
        b = c.step(0.0, 0.0)
        assert b.critic_gain >= c.min_gain
        assert b.critic_gain <= c.max_gain

    def test_equal_min_max_gain(self) -> None:
        """When min_gain == max_gain, gain is fixed."""
        c = OEBController(min_gain=1.0, max_gain=1.0, energy_per_cycle=50.0)
        b = c.step(0.5, 0.0)
        assert b.critic_gain == pytest.approx(1.0)
