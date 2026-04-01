import numpy as np
from bnsyn.config import PlasticityParams
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)


def test_three_factor_bounds() -> None:
    p = PlasticityParams(w_min=0.0, w_max=1.0, eta=1.0)
    w = np.zeros((2, 3), dtype=float)
    elig = EligibilityTraces(e=np.zeros_like(w))
    neu = NeuromodulatorTrace(n=10.0)
    pre = np.array([1, 0], dtype=bool)
    post = np.array([1, 1, 1], dtype=bool)
    w2, elig2 = three_factor_update(w, elig, neu, pre, post, dt_ms=1.0, p=p)
    assert float(w2.max()) <= 1.0
    assert elig2.e.shape == w.shape
