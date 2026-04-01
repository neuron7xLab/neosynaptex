from __future__ import annotations

import numpy as np
import pytest
from numpy.testing import assert_allclose

from bnsyn.config import AdExParams, PlasticityParams, TemperatureParams
from bnsyn.neuron.adex import AdExState, adex_step
from bnsyn.plasticity.stdp import stdp_kernel
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    decay,
    neuromod_step,
    three_factor_update,
)
from bnsyn.temperature.schedule import TemperatureSchedule, gate_sigmoid


def _single_neuron_state(v_mV: float, w_pA: float = 0.0) -> AdExState:
    return AdExState(
        V_mV=np.array([v_mV], dtype=np.float64),
        w_pA=np.array([w_pA], dtype=np.float64),
        spiked=np.array([False], dtype=np.bool_),
    )


def test_adex_boundary_vpeak_triggers_spike() -> None:
    params = AdExParams()
    state = _single_neuron_state(params.Vpeak_mV)

    updated = adex_step(
        state,
        params,
        dt_ms=0.1,
        I_syn_pA=np.zeros(1, dtype=np.float64),
        I_ext_pA=np.zeros(1, dtype=np.float64),
    )

    assert bool(updated.spiked[0]) is True
    assert_allclose(updated.V_mV, np.array([params.Vreset_mV], dtype=np.float64), rtol=0, atol=1e-12)


def test_adex_dt_validation_and_upper_bound_inclusive() -> None:
    params = AdExParams()
    state = _single_neuron_state(-60.0)
    zeros = np.zeros(1, dtype=np.float64)

    with pytest.raises(ValueError, match="positive"):
        adex_step(state, params, dt_ms=0.0, I_syn_pA=zeros, I_ext_pA=zeros)

    with pytest.raises(ValueError, match="<= 1.0"):
        adex_step(state, params, dt_ms=1.0000001, I_syn_pA=zeros, I_ext_pA=zeros)

    updated = adex_step(state, params, dt_ms=1.0, I_syn_pA=zeros, I_ext_pA=zeros)
    assert updated.V_mV.shape == (1,)


def test_adex_overflow_clamp_keeps_state_finite() -> None:
    params = AdExParams()
    state = _single_neuron_state(1e6)
    updated = adex_step(
        state,
        params,
        dt_ms=0.1,
        I_syn_pA=np.zeros(1, dtype=np.float64),
        I_ext_pA=np.zeros(1, dtype=np.float64),
    )

    assert np.isfinite(updated.V_mV).all()
    assert np.isfinite(updated.w_pA).all()


def test_adex_non_finite_input_current_rejected() -> None:
    params = AdExParams()
    state = _single_neuron_state(-60.0)

    with pytest.raises(ValueError, match="I_syn_pA contains non-finite"):
        adex_step(
            state,
            params,
            dt_ms=0.1,
            I_syn_pA=np.array([np.nan], dtype=np.float64),
            I_ext_pA=np.zeros(1, dtype=np.float64),
        )


def test_stdp_kernel_positive_negative_and_zero() -> None:
    p = PlasticityParams(A_plus=0.6, A_minus=0.7, tau_plus_ms=15.0, tau_minus_ms=25.0)

    dt_pos = 3.0
    expected_pos = p.A_plus * np.exp(-dt_pos / p.tau_plus_ms)
    assert_allclose(stdp_kernel(dt_pos, p), expected_pos, rtol=0, atol=1e-12)

    dt_neg = -4.0
    expected_neg = -p.A_minus * np.exp(dt_neg / p.tau_minus_ms)
    assert_allclose(stdp_kernel(dt_neg, p), expected_neg, rtol=0, atol=1e-12)

    assert stdp_kernel(0.0, p) == 0.0


def test_three_factor_decay_and_exact_update_with_clip() -> None:
    p = PlasticityParams(tau_e_ms=40.0, eta=0.5, w_min=0.0, w_max=0.6)
    dt_ms = 2.0

    w = np.array([[0.55, 0.1], [0.2, 0.59]], dtype=np.float64)
    elig0 = np.array([[0.2, 0.0], [0.3, 0.4]], dtype=np.float64)
    elig = EligibilityTraces(e=elig0)
    neuromod = NeuromodulatorTrace(n=1.5)
    pre_spikes = np.array([True, False], dtype=np.bool_)
    post_spikes = np.array([True, True], dtype=np.bool_)

    expected_decay = elig0 * np.exp(-dt_ms / p.tau_e_ms)
    assert_allclose(decay(elig0, dt_ms, p.tau_e_ms), expected_decay, rtol=0, atol=1e-12)

    expected_e = expected_decay + np.outer(pre_spikes.astype(np.float64), post_spikes.astype(np.float64))
    expected_w = np.clip(w + p.eta * expected_e * neuromod.n, p.w_min, p.w_max)

    w_new, elig_new = three_factor_update(w, elig, neuromod, pre_spikes, post_spikes, dt_ms, p)

    assert_allclose(elig_new.e, expected_e, rtol=0, atol=1e-12)
    assert_allclose(w_new, expected_w, rtol=0, atol=1e-12)


def test_three_factor_validation_errors() -> None:
    p = PlasticityParams()
    w = np.zeros((2, 2), dtype=np.float64)
    elig = EligibilityTraces(e=np.zeros((2, 2), dtype=np.float64))
    neuromod = NeuromodulatorTrace(n=1.0)
    pre_spikes = np.array([True, False], dtype=np.bool_)
    post_spikes = np.array([True, False], dtype=np.bool_)

    with pytest.raises(ValueError, match="dt_ms must be positive"):
        three_factor_update(w, elig, neuromod, pre_spikes, post_spikes, dt_ms=0.0, p=p)

    with pytest.raises(ValueError, match="pre_spikes shape mismatch"):
        three_factor_update(
            w,
            elig,
            neuromod,
            np.array([True], dtype=np.bool_),
            post_spikes,
            dt_ms=1.0,
            p=p,
        )


def test_neuromod_step_exact_formula() -> None:
    n = 1.25
    dt_ms = 2.0
    tau_ms = 5.0
    d_t = -0.1
    expected = n * np.exp(-dt_ms / tau_ms) + d_t

    assert_allclose(neuromod_step(n=n, dt_ms=dt_ms, tau_ms=tau_ms, d_t=d_t), expected, rtol=0, atol=1e-12)


def test_temperature_schedule_and_gate_equations() -> None:
    params = TemperatureParams(T0=0.3, Tmin=0.1, alpha=0.5, Tc=0.2, gate_tau=0.04)

    assert_allclose(gate_sigmoid(T=params.Tc, Tc=params.Tc, tau=params.gate_tau), 0.5, rtol=0, atol=1e-12)

    schedule = TemperatureSchedule(params=params, T=0.3)
    t1 = schedule.step_geometric()
    t2 = schedule.step_geometric()
    t3 = schedule.step_geometric()
    assert_allclose(np.array([t1, t2, t3]), np.array([0.15, 0.1, 0.1]), rtol=0, atol=1e-12)

    expected_gate = gate_sigmoid(schedule.T, params.Tc, params.gate_tau)
    assert_allclose(schedule.plasticity_gate(), expected_gate, rtol=0, atol=1e-12)
