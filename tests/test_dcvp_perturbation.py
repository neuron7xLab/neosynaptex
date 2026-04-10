"""Perturbation layer tests — spec §II."""

from __future__ import annotations

import numpy as np

from formal.dcvp.perturbation import apply_perturbation, identity
from formal.dcvp.protocol import PerturbationSpec


def test_identity_is_pure_copy() -> None:
    x = np.arange(10.0)
    y = identity(x)
    assert np.array_equal(x, y)
    assert y is not x  # defensive copy


def test_noise_scales_with_sigma() -> None:
    rng = np.random.default_rng(0)
    x = np.ones(1000)
    low = apply_perturbation(x, PerturbationSpec("noise", sigma=0.1), rng)
    rng = np.random.default_rng(0)
    high = apply_perturbation(x, PerturbationSpec("noise", sigma=1.0), rng)
    # Noise scales with std(x)+eps; constant x → eps floor, but high σ must
    # still be at least as noisy as low σ.
    assert np.std(high) >= np.std(low)


def test_noise_raises_variance_on_ar1() -> None:
    rng0 = np.random.default_rng(0)
    raw = np.zeros(512)
    for i in range(1, 512):
        raw[i] = 0.8 * raw[i - 1] + rng0.normal()
    rng = np.random.default_rng(1)
    perturbed = apply_perturbation(raw, PerturbationSpec("noise", sigma=0.5), rng)
    assert np.var(perturbed) > np.var(raw)


def test_delay_positive_shifts_right() -> None:
    x = np.arange(10.0)
    spec = PerturbationSpec("delay", sigma=0.0, delay_ticks=3)
    y = apply_perturbation(x, spec, np.random.default_rng(0))
    assert y[0] == y[1] == y[2] == 0.0
    assert np.array_equal(y[3:], x[:-3])


def test_delay_negative_shifts_left() -> None:
    x = np.arange(10.0)
    spec = PerturbationSpec("delay", sigma=0.0, delay_ticks=-2)
    y = apply_perturbation(x, spec, np.random.default_rng(0))
    assert np.array_equal(y[:-2], x[2:])


def test_topology_preserves_marginal_on_2d() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(100, 6))
    spec = PerturbationSpec("topology", sigma=0.0, topology_swap_frac=0.5)
    y = apply_perturbation(x, spec, rng)
    # Marginal distribution per feature is preserved (just permuted columns).
    assert sorted(np.sort(x.sum(axis=0))) == sorted(np.sort(y.sum(axis=0)))


def test_topology_no_op_on_1d() -> None:
    x = np.arange(10.0)
    spec = PerturbationSpec("topology", sigma=0.0, topology_swap_frac=0.5)
    y = apply_perturbation(x, spec, np.random.default_rng(0))
    assert np.array_equal(x, y)
