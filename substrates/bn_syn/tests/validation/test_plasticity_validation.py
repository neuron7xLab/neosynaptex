import numpy as np
import pytest

from bnsyn.config import PlasticityParams
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    three_factor_update,
)
from tests.tolerances import DEFAULT_RTOL


@pytest.mark.validation
def test_eligibility_decay_matches_exponential() -> None:
    p = PlasticityParams()
    w = np.zeros((2, 2), dtype=float)
    elig = EligibilityTraces(e=np.ones((2, 2), dtype=float))
    neuromod = NeuromodulatorTrace(n=0.0)
    pre = np.zeros(2, dtype=bool)
    post = np.zeros(2, dtype=bool)

    _, out = three_factor_update(w, elig, neuromod, pre, post, dt_ms=0.1, p=p)
    expected = np.exp(-0.1 / p.tau_e_ms)
    assert np.allclose(out.e, expected, rtol=DEFAULT_RTOL)


@pytest.mark.validation
def test_weight_update_bounds_and_requires_modulator() -> None:
    p = PlasticityParams()
    w = np.full((1, 1), p.w_max - 1e-6, dtype=float)
    elig = EligibilityTraces(e=np.zeros((1, 1), dtype=float))
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
    assert np.allclose(w_static, w)

    w_new, _ = three_factor_update(
        w,
        elig,
        NeuromodulatorTrace(n=1.0),
        pre,
        post,
        dt_ms=0.1,
        p=p,
    )
    assert w_new <= p.w_max
    assert w_new >= p.w_min
