import math

import numpy as np
import pytest

from mycelium_fractal_net.metrics import mse, psnr, snr, ssim

ITERATIONS = 5
NOISE_SMALL = 0.01
NOISE_LARGE = 0.1


def test_mse_nonnegative() -> None:
    rng = np.random.default_rng(0)
    for _ in range(ITERATIONS):
        a = rng.normal(size=128)
        b = rng.normal(size=128)
        assert mse(a, b) >= 0.0


def test_mse_zero_on_equal() -> None:
    rng = np.random.default_rng(1)
    a = rng.normal(size=64)
    assert mse(a, a) == pytest.approx(0.0)


def test_snr_infinite_on_equal() -> None:
    x = np.linspace(-1.0, 1.0, num=50)
    assert math.isinf(snr(x, x))


def test_snr_monotonic_noise() -> None:
    rng = np.random.default_rng(2)
    clean = rng.normal(size=256)
    noise_small = rng.normal(scale=NOISE_SMALL, size=256)
    noise_large = rng.normal(scale=NOISE_LARGE, size=256)
    snr_small = snr(clean, clean + noise_small)
    snr_large = snr(clean, clean + noise_large)
    assert snr_small > snr_large


def test_psnr_infinite_on_equal() -> None:
    x = np.ones(32)
    assert math.isinf(psnr(x, x))


def test_ssim_bounds() -> None:
    rng = np.random.default_rng(3)
    a = rng.normal(size=(32, 32))
    b = a + rng.normal(scale=0.05, size=(32, 32))
    score = ssim(a, b)
    assert -1.0 <= score <= 1.0
    assert ssim(a, a) == pytest.approx(1.0)
