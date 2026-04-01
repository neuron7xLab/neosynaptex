import pytest

from bnsyn.config import TemperatureParams
from bnsyn.temperature.schedule import TemperatureSchedule


class TestTemperatureEdgeCases:
    @pytest.mark.parametrize("T0,Tmin", [(0.1, 0.01), (1.0, 0.1), (10.0, 0.01), (100.0, 1.0)])
    def test_temperature_schedule_bounds(self, T0: float, Tmin: float) -> None:
        p = TemperatureParams(T0=T0, Tmin=Tmin, alpha=0.95, Tc=T0 * 0.5, gate_tau=0.02)
        sched = TemperatureSchedule(p)
        for _ in range(1000):
            sched.step_geometric()
            assert sched.T >= p.Tmin, f"Temperature below minimum: {sched.T} < {p.Tmin}"
            assert sched.T <= T0 + 1e-6, f"Temperature exceeded initial: {sched.T} > {T0}"

    @pytest.mark.parametrize("alpha", [0.1, 0.5, 0.9, 0.99, 0.999])
    def test_cooling_rate(self, alpha: float) -> None:
        p = TemperatureParams(T0=1.0, Tmin=0.01, alpha=alpha, Tc=0.5, gate_tau=0.02)
        sched = TemperatureSchedule(p)
        T_prev = sched.T
        for _ in range(100):
            sched.step_geometric()
            assert sched.T <= T_prev, "Temperature should decrease monotonically"
            T_prev = sched.T

    def test_gate_closes_over_time(self) -> None:
        p = TemperatureParams(T0=1.0, Tmin=0.01, alpha=0.95, Tc=0.5, gate_tau=0.02)
        sched = TemperatureSchedule(p)
        gate_init = sched.plasticity_gate()
        for _ in range(1000):
            sched.step_geometric()
        gate_final = sched.plasticity_gate()
        assert gate_final <= gate_init, "Plasticity gate should decrease as temperature cools"
