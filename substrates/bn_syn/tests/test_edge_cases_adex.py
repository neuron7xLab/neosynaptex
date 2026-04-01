import numpy as np
import pytest

from bnsyn.config import AdExParams
from bnsyn.neuron.adex import AdExState, adex_step


class TestAdExEdgeCases:
    @pytest.mark.parametrize(
        "V_init",
        [
            1e-10,
            1e-6,
            0.0,
            AdExParams().EL_mV,
            AdExParams().Vpeak_mV,
            AdExParams().Vpeak_mV + 1e-6,
            AdExParams().Vpeak_mV + 10.0,
            -1e3,
        ],
    )
    def test_voltage_initialization(self, V_init: float) -> None:
        p = AdExParams()
        V = np.array([V_init], dtype=float)
        w = np.zeros(1)
        state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros(1, dtype=bool))
        out = adex_step(state, p, dt_ms=0.1, I_syn_pA=np.zeros(1), I_ext_pA=np.zeros(1))
        assert not np.isnan(out.V_mV[0]) and not np.isinf(out.V_mV[0])

    @pytest.mark.parametrize("w_init", [-100.0, -1e-6, 0.0, 1.0, 1e3])
    def test_adaptation_initialization(self, w_init: float) -> None:
        p = AdExParams()
        V = np.array([p.EL_mV], dtype=float)
        w = np.array([w_init], dtype=float)
        state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros(1, dtype=bool))
        out = adex_step(state, p, dt_ms=0.1, I_syn_pA=np.zeros(1), I_ext_pA=np.zeros(1))
        assert not np.isnan(out.w_pA[0]) and not np.isinf(out.w_pA[0])

    @pytest.mark.parametrize("dt_ms", [1e-6, 1e-4, 0.1, 1.0])
    def test_dt_stability(self, dt_ms: float) -> None:
        p = AdExParams()
        V = np.array([p.EL_mV + 5.0], dtype=float)
        w = np.zeros(1)
        state = AdExState(V_mV=V, w_pA=w, spiked=np.zeros(1, dtype=bool))
        out = adex_step(state, p, dt_ms=dt_ms, I_syn_pA=np.zeros(1), I_ext_pA=np.zeros(1))
        assert not np.isnan(out.V_mV[0]) and not np.isinf(out.V_mV[0])
