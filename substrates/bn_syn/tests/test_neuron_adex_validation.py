"""Validation tests for AdEx neuron step edges."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.neuron.adex import AdExParams, AdExState, adex_step


def _make_state(params: AdExParams) -> AdExState:
    return AdExState(
        V_mV=np.array([params.EL_mV], dtype=float),
        w_pA=np.array([0.0], dtype=float),
        spiked=np.array([False]),
    )


def test_adex_step_rejects_large_dt() -> None:
    params = AdExParams()
    state = _make_state(params)
    with pytest.raises(ValueError, match="dt_ms out of bounds"):
        adex_step(state, params, dt_ms=1.1, I_syn_pA=np.array([0.0]), I_ext_pA=np.array([0.0]))


def test_adex_step_rejects_non_positive_dt() -> None:
    params = AdExParams()
    state = _make_state(params)
    with pytest.raises(ValueError, match="dt_ms must be positive"):
        adex_step(state, params, dt_ms=0.0, I_syn_pA=np.array([0.0]), I_ext_pA=np.array([0.0]))


def test_adex_step_rejects_nonfinite_external_current() -> None:
    params = AdExParams()
    state = _make_state(params)
    with pytest.raises(ValueError, match="I_ext_pA contains non-finite values"):
        adex_step(state, params, dt_ms=0.1, I_syn_pA=np.array([0.0]), I_ext_pA=np.array([np.inf]))
