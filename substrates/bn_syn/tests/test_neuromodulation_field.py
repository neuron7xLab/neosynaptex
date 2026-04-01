"""Tests for neuromodulatory field dynamics."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.neuromodulation.field import (
    NeuromodulationParams,
    NeuromodulatoryField,
)


def _simple_ring_laplacian(N: int) -> np.ndarray:
    """Build a ring-graph Laplacian (each node connected to two neighbours)."""
    A = np.zeros((N, N), dtype=np.float64)
    for i in range(N):
        A[i, (i + 1) % N] = 1.0
        A[i, (i - 1) % N] = 1.0
    D = np.diag(A.sum(axis=1))
    return D - A


@pytest.fixture()
def params() -> NeuromodulationParams:
    return NeuromodulationParams(enabled=True)


@pytest.fixture()
def ring5(params: NeuromodulationParams) -> NeuromodulatoryField:
    N = 5
    L = _simple_ring_laplacian(N)
    return NeuromodulatoryField(N, L, params)


# ---- test_field_decays_without_spikes ----

def test_field_decays_without_spikes(params: NeuromodulationParams) -> None:
    """DA > 0 initially, no spikes -> DA decreases after step."""
    N = 5
    L = _simple_ring_laplacian(N)
    field = NeuromodulatoryField(N, L, params)

    # Inject DA manually
    field._DA[:] = 1.0
    initial_mean = float(np.mean(field._DA))

    no_spikes = np.zeros(N, dtype=bool)
    state = field.step(dt_ms=1.0, spiked=no_spikes, sigma=1.0,
                       spike_rate_hz=10.0, target_rate_hz=10.0)

    assert state.mean_DA < initial_mean, "DA should decay without input"


# ---- test_da_responds_to_rpe ----

def test_da_responds_to_rpe(ring5: NeuromodulatoryField) -> None:
    """Positive RPE + spikes -> DA increases for spiking neurons."""
    spiked = np.array([True, True, False, False, False])

    # Positive RPE: spike_rate > target_rate
    state = ring5.step(dt_ms=1.0, spiked=spiked, sigma=1.0,
                       spike_rate_hz=20.0, target_rate_hz=10.0)

    assert state.DA[0] > 0.0, "Spiking neuron should gain DA with positive RPE"
    assert state.DA[1] > 0.0
    # Non-spiking neurons should have zero or near-zero DA (only diffusion)
    assert state.DA[0] > state.DA[2]


# ---- test_ne_responds_to_criticality_deviation ----

def test_ne_responds_to_criticality_deviation(ring5: NeuromodulatoryField) -> None:
    """sigma far from 1.0 + spikes -> NE increases."""
    N = 5
    spiked = np.ones(N, dtype=bool)

    # sigma = 2.0 -> salience = |2.0 - 1.0| = 1.0
    state = ring5.step(dt_ms=1.0, spiked=spiked, sigma=2.0,
                       spike_rate_hz=10.0, target_rate_hz=10.0)

    assert state.mean_NE > 0.0, "NE should increase when sigma deviates from 1.0"


# ---- test_diffusion_spreads_field ----

def test_diffusion_spreads_field(params: NeuromodulationParams) -> None:
    """Set DA[0] = 1.0, all others 0, step -> DA[neighbours] > 0."""
    N = 5
    # Use higher diffusion to make the effect clearly visible
    p = NeuromodulationParams(
        enabled=True,
        diffusion_DA=0.5,
        tau_DA_ms=1e6,  # near-zero decay so we only see diffusion
    )
    L = _simple_ring_laplacian(N)
    field = NeuromodulatoryField(N, L, p)

    field._DA[0] = 1.0
    no_spikes = np.zeros(N, dtype=bool)

    state = field.step(dt_ms=1.0, spiked=no_spikes, sigma=1.0,
                       spike_rate_hz=10.0, target_rate_hz=10.0)

    # Neighbours of node 0 are nodes 1 and 4 on a ring
    assert state.DA[1] > 0.0, "Diffusion should spread DA to neighbour 1"
    assert state.DA[4] > 0.0, "Diffusion should spread DA to neighbour 4"


# ---- test_gating_matrix_shape ----

def test_gating_matrix_shape(ring5: NeuromodulatoryField) -> None:
    """gating_matrix returns array of correct length."""
    # Inject some field values so gating is non-trivial
    ring5._DA[:] = 0.5
    ring5._ACh[:] = 0.3
    ring5._NE[:] = 0.8

    pre = np.array([0, 1, 2], dtype=np.intp)
    post = np.array([1, 2, 3], dtype=np.intp)

    gate = ring5.gating_matrix(pre, post)
    assert gate.shape == (3,), f"Expected shape (3,), got {gate.shape}"
    assert np.all(gate > 0), "Gate values should be positive with positive fields"
