from __future__ import annotations

import time

import numpy as np
import pytest

from bnsyn.regime import compute_gamma

pytestmark = pytest.mark.performance


def test_compute_gamma_performance_budget() -> None:
    rng = np.random.default_rng(2026)
    activations = rng.normal(size=4096)
    start = time.perf_counter()
    for _ in range(50):
        compute_gamma(activations)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.5
