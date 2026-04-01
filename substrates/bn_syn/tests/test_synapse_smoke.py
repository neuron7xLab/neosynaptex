import numpy as np
from bnsyn.config import SynapseParams
from bnsyn.synapse.conductance import nmda_mg_block, ConductanceSynapses


def test_nmda_block_monotone() -> None:
    V = np.array([-80.0, -40.0, 0.0, 40.0])
    B = nmda_mg_block(V, mg_mM=1.0)
    assert float(B[0]) < float(B[1]) < float(B[2]) < float(B[3])


def test_conductance_decay_nonnegative() -> None:
    p = SynapseParams()
    syn = ConductanceSynapses(N=5, params=p, dt_ms=0.1)
    syn.queue_events(np.ones(5) * 1.0)
    g = syn.step()
    assert g.shape == (3, 5)
    assert (g >= 0).all()
