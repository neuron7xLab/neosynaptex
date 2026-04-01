import numpy as np
from bnsyn.consolidation.dual_weight import DualWeights
from bnsyn.config import DualWeightParams


def test_dual_weight_updates() -> None:
    dw = DualWeights.init((10, 10), w0=0.0)
    p = DualWeightParams(theta_tag=0.1, eta_f=1.0, eta_c=0.1)
    upd = np.ones((10, 10))
    dw.step(dt_s=1.0, p=p, fast_update=upd)
    assert dw.w_fast.shape == (10, 10)
    assert dw.w_total.shape == (10, 10)
