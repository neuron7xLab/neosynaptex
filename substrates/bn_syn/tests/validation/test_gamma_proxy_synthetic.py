from __future__ import annotations

import numpy as np
import pytest

from bnsyn.regime import compute_gamma

pytestmark = pytest.mark.validation


def test_gamma_proxy_synthetic_signals() -> None:
    rng = np.random.default_rng(0)
    white = rng.normal(size=4096)
    const = np.ones(4096)
    sine = np.sin(np.linspace(0, 30*np.pi, 4096))
    assert np.isfinite(compute_gamma(white))
    assert np.isfinite(compute_gamma(sine))
    assert np.isfinite(compute_gamma(const))
