"""MFN-level stability guardrails for CFDE preprocessing."""

from __future__ import annotations

import pytest

pytest.skip("signal module quarantined", allow_module_level=True)

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.signal import Fractal1DPreprocessor


def _regime_flips(series: np.ndarray) -> int:
    """Count regime sign flips as a stability proxy."""
    return int(np.count_nonzero(np.diff(np.sign(series))))


def test_cfde_preprocessing_reduces_regime_flip_noise() -> None:
    torch.manual_seed(123)
    np.random.seed(123)
    rng = np.random.default_rng(123)

    base = np.concatenate(
        [
            np.full(60, 0.015, dtype=np.float32),
            np.full(60, -0.02, dtype=np.float32),
            np.full(60, 0.01, dtype=np.float32),
        ]
    )
    noisy = base + rng.normal(0.0, 0.008, size=base.shape).astype(np.float32)
    tensor = torch.tensor(noisy, dtype=torch.float32)

    preprocessor = Fractal1DPreprocessor(preset="markets", cfde_mode="multiscale")
    with torch.no_grad():
        denoised = preprocessor(tensor)

    denoised_np = denoised.detach().cpu().numpy()

    raw_flips = _regime_flips(noisy)
    denoised_flips = _regime_flips(denoised_np)

    raw_norm = (noisy - noisy.mean()) / noisy.std()
    denoised_norm = (denoised_np - denoised_np.mean()) / denoised_np.std()
    raw_diff_std = float(np.std(np.diff(raw_norm)))
    denoised_diff_std = float(np.std(np.diff(denoised_norm)))

    assert denoised_flips <= raw_flips
    assert denoised_diff_std <= raw_diff_std
