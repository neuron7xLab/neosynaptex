import numpy as np
from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step, adex_step_with_error_tracking


def test_adex_step_spikes_and_resets() -> None:
    p = AdExParams()
    V = np.array([p.Vpeak_mV + 1.0, p.EL_mV], dtype=float)
    w = np.zeros_like(V)
    s = AdExState(V_mV=V, w_pA=w, spiked=np.zeros_like(V, dtype=bool))
    out = adex_step(s, p, dt_ms=0.1, I_syn_pA=np.zeros(2), I_ext_pA=np.zeros(2))
    assert out.spiked[0]
    assert out.V_mV[0] == p.Vreset_mV
    assert out.w_pA[0] > 0


def test_adex_step_with_error_tracking_reports_metrics() -> None:
    p = AdExParams()
    V = np.array([p.EL_mV - 5.0, p.EL_mV + 2.0], dtype=float)
    w = np.zeros_like(V)
    state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros_like(V, dtype=bool))
    out, metrics = adex_step_with_error_tracking(
        state,
        p,
        dt_ms=0.1,
        I_syn_pA=np.zeros(2),
        I_ext_pA=np.zeros(2),
    )
    assert out.V_mV.shape == V.shape
    assert out.w_pA.shape == w.shape
    assert metrics.lte_estimate >= 0.0
    assert metrics.global_error_bound >= 0.0
    assert metrics.recommended_dt_ms > 0.0


def test_adex_step_uses_previous_voltage_for_adaptation() -> None:
    p = AdExParams()
    V = np.array([p.EL_mV + 5.0], dtype=float)
    w = np.array([1.0], dtype=float)
    state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros_like(V, dtype=bool))
    out = adex_step(state, p, dt_ms=0.1, I_syn_pA=np.zeros(1), I_ext_pA=np.zeros(1))
    expected_dw = (p.a_nS * (V[0] - p.EL_mV) - w[0]) / p.tauw_ms
    expected_w = w[0] + 0.1 * expected_dw
    assert np.isclose(out.w_pA[0], expected_w)
