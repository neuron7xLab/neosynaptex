import numpy as np
import pytest

from bnsyn.config import (
    AdExParams,
    CriticalityParams,
    PlasticityParams,
    SynapseParams,
    TemperatureParams,
)
from bnsyn.criticality.branching import BranchingEstimator, SigmaController
from bnsyn.neuron.adex import AdExState, adex_step
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)
from bnsyn.synapse.conductance import ConductanceSynapses
from bnsyn.temperature.schedule import TemperatureSchedule


@pytest.mark.validation
def test_minimal_circuit_spike_and_synaptic_decay() -> None:
    p = AdExParams()
    V = np.array([p.Vpeak_mV + 1.0], dtype=float)
    w = np.zeros_like(V)
    state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros_like(V, dtype=bool))
    state = adex_step(state, p, dt_ms=0.1, I_syn_pA=np.zeros(1), I_ext_pA=np.array([0.0]))
    assert state.spiked[0]

    syn = ConductanceSynapses(N=1, params=SynapseParams(), dt_ms=1.0)
    syn.queue_events(np.array([1.0]))
    g0 = syn.step()
    g1 = syn.step()
    assert np.all(g1 < g0)


@pytest.mark.validation
def test_plasticity_update_requires_modulator_and_spikes() -> None:
    p = PlasticityParams()
    w = np.zeros((1, 1))
    elig = EligibilityTraces(e=np.zeros((1, 1)))
    pre = np.array([True])
    post = np.array([True])
    w_static, _ = three_factor_update(
        w,
        elig,
        NeuromodulatorTrace(n=0.0),
        pre,
        post,
        dt_ms=0.1,
        p=p,
    )
    w_updated, _ = three_factor_update(
        w,
        elig,
        NeuromodulatorTrace(n=1.0),
        pre,
        post,
        dt_ms=0.1,
        p=p,
    )
    assert np.allclose(w_static, w)
    assert np.any(w_updated != w)


@pytest.mark.validation
def test_temperature_gate_switches_regimes() -> None:
    params = TemperatureParams(T0=1.0, Tmin=0.1, alpha=0.9, Tc=0.5, gate_tau=0.08)
    sched = TemperatureSchedule(params=params)
    gate_high = sched.plasticity_gate()
    sched.T = 0.1
    gate_low = sched.plasticity_gate()
    assert gate_high > gate_low


@pytest.mark.validation
def test_criticality_controller_moves_toward_target() -> None:
    estimator = BranchingEstimator(ema_alpha=0.5)
    params = CriticalityParams(sigma_target=1.0, gain_min=0.5, gain_max=1.5, eta_sigma=0.1)
    controller = SigmaController(params=params, gain=1.0)
    spikes_t = [10.0, 10.0, 10.0, 10.0]
    spikes_t1 = [15.0, 15.0, 15.0, 15.0]
    for a_t, a_t1 in zip(spikes_t, spikes_t1, strict=True):
        sigma = estimator.update(a_t, a_t1)
        gain = controller.step(sigma)
    assert gain < 1.0
