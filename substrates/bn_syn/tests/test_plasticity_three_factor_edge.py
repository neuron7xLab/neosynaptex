"""Tests for three-factor plasticity edge cases."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.config import PlasticityParams
from bnsyn.plasticity.three_factor import (
    EligibilityTraces,
    NeuromodulatorTrace,
    neuromod_step,
    three_factor_update,
)


def test_three_factor_update_shape_checks() -> None:
    params = PlasticityParams()
    w = np.zeros((2, 2), dtype=np.float64)
    elig = EligibilityTraces(e=np.zeros((2, 2), dtype=np.float64))
    neuromod = NeuromodulatorTrace(n=1.0)
    pre = np.array([True, False])
    post = np.array([True, False])

    with pytest.raises(ValueError, match="w must be 2D"):
        three_factor_update(
            w=np.zeros(2),
            elig=elig,
            neuromod=neuromod,
            pre_spikes=pre,
            post_spikes=post,
            dt_ms=1.0,
            p=params,
        )

    with pytest.raises(ValueError, match="eligibility shape"):
        three_factor_update(
            w=w,
            elig=EligibilityTraces(e=np.zeros((1, 1), dtype=np.float64)),
            neuromod=neuromod,
            pre_spikes=pre,
            post_spikes=post,
            dt_ms=1.0,
            p=params,
        )

    with pytest.raises(ValueError, match="pre_spikes shape"):
        three_factor_update(
            w=w,
            elig=elig,
            neuromod=neuromod,
            pre_spikes=np.array([True]),
            post_spikes=post,
            dt_ms=1.0,
            p=params,
        )

    with pytest.raises(ValueError, match="post_spikes shape"):
        three_factor_update(
            w=w,
            elig=elig,
            neuromod=neuromod,
            pre_spikes=pre,
            post_spikes=np.array([True]),
            dt_ms=1.0,
            p=params,
        )

    with pytest.raises(ValueError, match="dt_ms must be positive"):
        three_factor_update(
            w=w,
            elig=elig,
            neuromod=neuromod,
            pre_spikes=pre,
            post_spikes=post,
            dt_ms=0.0,
            p=params,
        )


def test_neuromod_step_decay_and_drive() -> None:
    updated = neuromod_step(n=1.0, dt_ms=1.0, tau_ms=10.0, d_t=0.5)
    assert updated > 0.5
