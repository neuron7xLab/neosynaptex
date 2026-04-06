"""Tests for core.expelliarmus — the Disarming Theorem.

"You cannot take the wand from someone whose magic IS the motion."
"""

from __future__ import annotations

import numpy as np
import pytest

from core.expelliarmus import DisarmResult, Expelliarmus


class TestDisarmLivingSystem:
    """A living system (stochastic, driven) should be RESILIENT."""

    def test_stochastic_model_is_resilient(self) -> None:
        spell = Expelliarmus(epsilon=0.3, tau_recovery=50)
        result = spell.cast_on_model(seed=42)
        assert isinstance(result, DisarmResult)
        assert result.resilient is True
        assert result.disarmed is False
        assert "RESILIENT" in result.verdict

    def test_recovery_time_finite(self) -> None:
        spell = Expelliarmus()
        result = spell.cast_on_model(seed=7)
        assert result.recovery_time < spell.tau_recovery

    def test_gamma_preserved_after_perturbation(self) -> None:
        spell = Expelliarmus()
        result = spell.cast_on_model(seed=99)
        # γ should stay in metastable zone after recovery
        assert abs(result.gamma_after - 1.0) < 0.5


class TestDisarmDeadSystem:
    """A dead system (constant trajectory) should be DISARMED."""

    def test_constant_trajectory_disarmed(self) -> None:
        # Flatline: no dynamics, no gradient, no life
        traj = np.ones((100, 4)) * 0.5
        spell = Expelliarmus(epsilon=0.01)  # tiny perturbation
        result = spell.cast(traj)
        assert result.disarmed is True
        assert result.resilient is False
        assert "DISARMED" in result.verdict

    def test_dead_system_has_zero_delta_v(self) -> None:
        traj = np.ones((100, 4)) * 0.5
        spell = Expelliarmus(epsilon=0.01)
        result = spell.cast(traj)
        assert result.delta_v_before < 0.01


class TestDisarmEdgeCases:
    def test_short_trajectory_rejected(self) -> None:
        with pytest.raises(ValueError, match="T >= 10"):
            Expelliarmus().cast(np.zeros((5, 4)))

    def test_1d_trajectory_rejected(self) -> None:
        with pytest.raises(ValueError):
            Expelliarmus().cast(np.zeros(100))

    def test_custom_epsilon(self) -> None:
        spell = Expelliarmus(epsilon=0.01)
        assert spell.epsilon == 0.01

    def test_custom_tau(self) -> None:
        spell = Expelliarmus(tau_recovery=200)
        assert spell.tau_recovery == 200


class TestDisarmResultImmutable:
    def test_frozen(self) -> None:
        spell = Expelliarmus()
        result = spell.cast_on_model(seed=42)
        with pytest.raises(AttributeError):
            result.disarmed = True  # type: ignore[misc]


class TestVerdictStrings:
    def test_resilient_verdict_contains_wand(self) -> None:
        spell = Expelliarmus()
        result = spell.cast_on_model(seed=42)
        if result.resilient:
            assert "wand" in result.verdict.lower()

    def test_disarmed_verdict_contains_capacitor(self) -> None:
        traj = np.ones((100, 4)) * 0.5
        spell = Expelliarmus(epsilon=0.01)
        result = spell.cast(traj)
        if result.disarmed:
            assert "capacitor" in result.verdict.lower()
