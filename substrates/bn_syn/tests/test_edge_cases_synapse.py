import numpy as np
import pytest

from bnsyn.config import SynapseParams
from bnsyn.synapse.conductance import ConductanceSynapses, nmda_mg_block


class TestSynapseEdgeCases:
    @pytest.mark.parametrize("V_mV", [-200.0, -100.0, -80.0, -40.0, 0.0, 40.0, 100.0, 200.0])
    def test_nmda_block_all_voltages(self, V_mV: float) -> None:
        V = np.array([V_mV], dtype=float)
        B = nmda_mg_block(V, mg_mM=1.0)
        assert 0 <= B[0] <= 1.0, f"NMDA block out of range at V={V_mV}"

    @pytest.mark.parametrize("mg_mM", [0.0, 0.1, 1.0, 5.0, 10.0])
    def test_nmda_block_mg_concentrations(self, mg_mM: float) -> None:
        V = np.linspace(-100, 100, 10)
        B = nmda_mg_block(V, mg_mM=mg_mM)
        assert np.all((B >= 0) & (B <= 1.0))

    def test_conductance_zero_events(self) -> None:
        p = SynapseParams()
        syn = ConductanceSynapses(N=10, params=p, dt_ms=0.1)
        g = syn.step()
        assert g.shape == (3, 10)
        assert np.all(g >= 0)

    def test_conductance_large_spike_train(self) -> None:
        p = SynapseParams()
        syn = ConductanceSynapses(N=100, params=p, dt_ms=0.1)
        for _ in range(1000):
            syn.queue_events(np.ones(100) * 100.0)
            g = syn.step()
            assert not np.any(np.isnan(g)) and not np.any(np.isinf(g))
