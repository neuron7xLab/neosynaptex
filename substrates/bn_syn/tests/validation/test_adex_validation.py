import numpy as np
import pytest

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step
from tests.tolerances import CONVERGENCE_FACTOR, DEFAULT_ATOL


@pytest.mark.validation
def test_adex_convergence_with_dt_halving() -> None:
    p = AdExParams()
    V0 = np.array([p.EL_mV - 2.0, p.EL_mV + 1.0], dtype=float)
    w0 = np.zeros_like(V0)
    state = AdExState(V_mV=V0, w_pA=w0, spiked=np.zeros_like(V0, dtype=bool))

    def integrate(dt: float, steps: int) -> AdExState:
        s = state
        for _ in range(steps):
            s = adex_step(s, p, dt_ms=dt, I_syn_pA=np.zeros(2), I_ext_pA=np.zeros(2))
        return s

    out_dt = integrate(0.2, 5)
    out_dt2 = integrate(0.1, 10)
    out_dt4 = integrate(0.05, 20)

    err_dt = np.linalg.norm(out_dt.V_mV - out_dt4.V_mV) + np.linalg.norm(out_dt.w_pA - out_dt4.w_pA)
    err_dt2 = np.linalg.norm(out_dt2.V_mV - out_dt4.V_mV) + np.linalg.norm(
        out_dt2.w_pA - out_dt4.w_pA
    )
    assert err_dt >= CONVERGENCE_FACTOR * max(err_dt2, DEFAULT_ATOL)


@pytest.mark.validation
def test_adex_exp_clamp_prevents_overflow() -> None:
    p = AdExParams()
    V = np.array([p.VT_mV + 1000.0], dtype=float)
    w = np.zeros_like(V)
    state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros_like(V, dtype=bool))
    out = adex_step(state, p, dt_ms=0.1, I_syn_pA=np.zeros(1), I_ext_pA=np.zeros(1))
    assert np.isfinite(out.V_mV).all()
    assert np.isfinite(out.w_pA).all()
