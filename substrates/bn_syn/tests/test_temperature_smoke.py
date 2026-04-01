import numpy as np
import pytest

from bnsyn.config import TemperatureParams
from bnsyn.temperature.schedule import TemperatureSchedule, gate_sigmoid


def _transition_width(tc: float, tau: float, lo: float = 0.1, hi: float = 0.9) -> float:
    t_lo = tc + tau * np.log(lo / (1.0 - lo))
    t_hi = tc + tau * np.log(hi / (1.0 - hi))
    return float(t_hi - t_lo)


def test_temperature_cools_and_gate_changes() -> None:
    sched = TemperatureSchedule(
        TemperatureParams(T0=1.0, Tmin=0.01, alpha=0.9, Tc=0.1, gate_tau=0.02)
    )
    g0 = sched.plasticity_gate()
    for _ in range(20):
        sched.step_geometric()
    g1 = sched.plasticity_gate()
    assert sched.T is not None
    assert sched.T >= 0.01
    assert g1 < g0


@pytest.mark.parametrize("tau", [0.015, 0.02, 0.05, 0.08])
def test_gate_sigmoid_is_monotone_in_temperature(tau: float) -> None:
    tc = 0.1
    temperatures = np.linspace(0.001, 1.0, 400)
    gates = np.array([gate_sigmoid(float(t), tc, tau) for t in temperatures])
    diffs = np.diff(gates)
    assert np.all(diffs >= 0.0)
    assert np.any(diffs > 0.0)


@pytest.mark.parametrize("tau_small,tau_large", [(0.015, 0.02), (0.02, 0.05), (0.05, 0.08)])
def test_gate_tau_controls_transition_width(tau_small: float, tau_large: float) -> None:
    tc = 0.1
    width_small = _transition_width(tc=tc, tau=tau_small)
    width_large = _transition_width(tc=tc, tau=tau_large)
    assert width_small < width_large


@pytest.mark.parametrize("tau", [0.015, 0.02, 0.05, 0.08])
def test_recommended_gate_tau_range_avoids_near_binary_behavior(tau: float) -> None:
    params = TemperatureParams(T0=1.0, Tmin=1e-3, alpha=0.95, Tc=0.1, gate_tau=tau)
    sched = TemperatureSchedule(params=params)

    gate_trace: list[float] = []
    for _ in range(200):
        gate_trace.append(sched.plasticity_gate())
        sched.step_geometric()

    intermediate_steps = sum(0.05 < gate < 0.95 for gate in gate_trace)
    max_step_jump = max(abs(curr - prev) for prev, curr in zip(gate_trace, gate_trace[1:]))

    assert intermediate_steps >= 10
    assert max_step_jump < 0.1



def test_gate_tau_changes_gate_slope_not_cooling_dynamics() -> None:
    params_fast = TemperatureParams(T0=1.0, Tmin=1e-3, alpha=0.95, Tc=0.1, gate_tau=0.015)
    params_slow = TemperatureParams(T0=1.0, Tmin=1e-3, alpha=0.95, Tc=0.1, gate_tau=0.08)
    sched_fast = TemperatureSchedule(params=params_fast)
    sched_slow = TemperatureSchedule(params=params_slow)

    for _ in range(30):
        t_fast = sched_fast.step_geometric()
        t_slow = sched_slow.step_geometric()
        assert t_fast == pytest.approx(t_slow)

    assert sched_fast.plasticity_gate() != pytest.approx(sched_slow.plasticity_gate())

def test_default_cooling_gate_trace_is_not_impulse_switch() -> None:
    params = TemperatureParams()
    sched = TemperatureSchedule(params=params)

    gate_trace: list[float] = []
    for _ in range(120):
        gate_trace.append(sched.plasticity_gate())
        sched.step_geometric()

    assert min(gate_trace) < 0.3
    assert max(gate_trace) > 0.7
    assert sum(0.1 < gate < 0.9 for gate in gate_trace) >= 10
