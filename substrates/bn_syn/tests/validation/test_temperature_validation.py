import pytest

from bnsyn.config import TemperatureParams
from bnsyn.temperature.schedule import TemperatureSchedule


@pytest.mark.validation
def test_temperature_geometric_cooling_and_gate() -> None:
    p = TemperatureParams(T0=1.0, Tmin=0.1, alpha=0.5, Tc=0.5, gate_tau=0.08)
    sched = TemperatureSchedule(params=p)
    t1 = sched.step_geometric()
    t2 = sched.step_geometric()
    assert t1 == pytest.approx(0.5)
    assert t2 == pytest.approx(0.25)
    gate_high = sched.plasticity_gate()
    sched.T = 0.1
    gate_low = sched.plasticity_gate()
    assert gate_high > gate_low
