import numpy as np
import pytest

from bnsyn.config import DualWeightParams
from bnsyn.consolidation.dual_weight import DualWeights
from tests.tolerances import DEFAULT_RTOL


@pytest.mark.validation
def test_fast_weight_update_includes_dt_scaling() -> None:
    p = DualWeightParams()
    dw = DualWeights.init((1, 1), w0=0.0)
    dt_s = 0.1
    fast_update = np.array([[2.0]], dtype=float)
    dw.step(dt_s=dt_s, p=p, fast_update=fast_update)
    expected = p.eta_f * fast_update * dt_s
    expected += (-(expected - dw.w0) / p.tau_f_s) * dt_s
    assert np.allclose(dw.w_fast, expected, rtol=DEFAULT_RTOL)


@pytest.mark.validation
def test_consolidation_requires_tag_and_protein() -> None:
    p = DualWeightParams()
    dw = DualWeights.init((10, 10), w0=0.0)
    dt_s = 0.5
    fast_update = np.full((10, 10), p.theta_tag * 100.0)
    dw.step(dt_s=dt_s, p=p, fast_update=fast_update)
    assert dw.protein > 0.0
    assert np.any(dw.tags)
    assert np.any(dw.w_cons != 0.0)
