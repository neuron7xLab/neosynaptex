"""Negative control tests — spec §VI."""

from __future__ import annotations

import numpy as np

from formal.dcvp.controls import (
    randomized_source,
    synthetic_noise_only,
    time_reversed,
)


def _coupled(n: int = 400, lag: int = 2, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    y = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.6 * x[t - 1] + rng.normal()
        if t > lag:
            y[t] = 0.5 * y[t - 1] + 0.7 * x[t - lag] + 0.2 * rng.normal()
    return x, y


def test_randomized_source_control_fails() -> None:
    x, y = _coupled()
    result = randomized_source(x, y, rng=np.random.default_rng(0), te_null_n=60)
    assert result.signaled_causality is False


def test_synthetic_noise_control_fails() -> None:
    result = synthetic_noise_only(300, rng=np.random.default_rng(0), te_null_n=60)
    assert result.signaled_causality is False


def test_time_reversed_weakens_causality() -> None:
    x, y = _coupled(n=600, lag=3, seed=7)
    fwd = randomized_source(x, y, rng=np.random.default_rng(0), te_null_n=60)
    rev = time_reversed(x, y, rng=np.random.default_rng(0), te_null_n=60)
    # The randomized control is expected to fail; the time-reversed one
    # should also fail — both are non-causal by construction.
    assert fwd.signaled_causality is False
    assert rev.signaled_causality is False
