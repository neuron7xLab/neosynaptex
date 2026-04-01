"""Unit tests for AdaptiveTimestepController."""

import pytest

from mycelium_fractal_net.core.thermodynamic_kernel import AdaptiveTimestepController


class TestAdaptiveController:
    def test_reduces_on_high_drift(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4)
        new_dt, was_reduced = ctrl.adjust(0.01, energy_drift=1e-3)
        assert was_reduced
        assert new_dt < 0.01

    def test_never_below_dt_min(self):
        ctrl = AdaptiveTimestepController(
            target_drift_rate=1e-4, dt_min=1e-6, max_consecutive_reductions=50
        )
        dt = 0.01
        for _ in range(20):
            dt, _ = ctrl.adjust(dt, energy_drift=1e-3)
        assert dt >= 1e-6

    def test_expands_on_low_drift(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4, dt_max=0.1)
        new_dt, was_reduced = ctrl.adjust(0.01, energy_drift=1e-6)
        assert not was_reduced
        assert new_dt >= 0.01

    def test_never_above_dt_max(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4, dt_max=0.05)
        dt = 0.04
        for _ in range(50):
            dt, _ = ctrl.adjust(dt, energy_drift=1e-8)
        assert dt <= 0.05

    def test_stable_in_band(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4)
        new_dt, was_reduced = ctrl.adjust(0.01, energy_drift=5e-5)
        assert not was_reduced
        assert new_dt == 0.01

    def test_divergence_raises(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4, max_consecutive_reductions=3)
        dt = 0.01
        for _ in range(2):
            dt, _ = ctrl.adjust(dt, energy_drift=1e-2)
        with pytest.raises(ValueError, match="ThermodynamicDivergence"):
            ctrl.adjust(dt, energy_drift=1e-2)

    def test_reset(self):
        ctrl = AdaptiveTimestepController(target_drift_rate=1e-4, max_consecutive_reductions=5)
        for _ in range(4):
            ctrl.adjust(0.01, energy_drift=1e-2)
        ctrl.reset()
        # Should not raise after reset
        ctrl.adjust(0.01, energy_drift=1e-2)
