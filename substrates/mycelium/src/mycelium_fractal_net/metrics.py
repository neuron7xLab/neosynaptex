from __future__ import annotations

import math
from typing import Any, Union

import numpy as np

try:  # optional torch surface
    import torch
except Exception:  # pragma: no cover
    torch = None

ArrayLike = Union[np.ndarray, Any]
_EPS = 1e-12


def _to_numpy(a: ArrayLike) -> np.ndarray:
    if torch is not None and hasattr(torch, "is_tensor") and torch.is_tensor(a):
        a = a.detach().cpu().numpy()
    return np.asarray(a, dtype=np.float64)


def _validate_inputs(a: np.ndarray, b: np.ndarray) -> None:
    if a.shape != b.shape:
        raise ValueError(f"Input shapes must match, got {a.shape} and {b.shape}")
    if a.size == 0:
        raise ValueError("Inputs must be non-empty")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Inputs must be finite")


def _compute_data_range(
    clean_np: np.ndarray, test_np: np.ndarray, data_range: float | None
) -> float:
    if data_range is not None:
        return data_range
    max_val = float(np.maximum(clean_np.max(), test_np.max()))
    min_val = float(np.minimum(clean_np.min(), test_np.min()))
    return max(_EPS, max_val - min_val)


def _mse_from_arrays(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.square(a - b)))


def _snr_from_arrays(clean_np: np.ndarray, noisy_np: np.ndarray) -> float:
    noise = noisy_np - clean_np
    signal_power = float(np.mean(np.square(clean_np)))
    noise_power = float(np.mean(np.square(noise)))
    if noise_power == 0.0:
        return math.inf
    if signal_power == 0.0:
        return -math.inf
    return float(10.0 * math.log10(signal_power / noise_power))


def mse(a: ArrayLike, b: ArrayLike) -> float:
    a_np, b_np = _to_numpy(a), _to_numpy(b)
    _validate_inputs(a_np, b_np)
    return _mse_from_arrays(a_np, b_np)


def snr(clean: ArrayLike, noisy: ArrayLike) -> float:
    clean_np, noisy_np = _to_numpy(clean), _to_numpy(noisy)
    _validate_inputs(clean_np, noisy_np)
    return _snr_from_arrays(clean_np, noisy_np)


def psnr(clean: ArrayLike, test: ArrayLike, data_range: float | None = None) -> float:
    clean_np, test_np = _to_numpy(clean), _to_numpy(test)
    _validate_inputs(clean_np, test_np)
    err = _mse_from_arrays(clean_np, test_np)
    if err == 0.0:
        return math.inf
    data_range = _compute_data_range(clean_np, test_np, data_range)
    return float(10.0 * math.log10((data_range * data_range) / err))


def ssim(
    clean: ArrayLike,
    test: ArrayLike,
    data_range: float | None = None,
    k1: float = 0.01,
    k2: float = 0.03,
) -> float:
    clean_np, test_np = _to_numpy(clean), _to_numpy(test)
    _validate_inputs(clean_np, test_np)

    data_range = _compute_data_range(clean_np, test_np, data_range)

    c1 = (k1 * data_range) ** 2
    c2 = (k2 * data_range) ** 2

    mu_x = float(clean_np.mean())
    mu_y = float(test_np.mean())
    sigma_x = float(clean_np.var())
    sigma_y = float(test_np.var())
    sigma_xy = float(np.mean((clean_np - mu_x) * (test_np - mu_y)))

    numerator = (2 * mu_x * mu_y + c1) * (2 * sigma_xy + c2)
    denominator = (mu_x**2 + mu_y**2 + c1) * (sigma_x + sigma_y + c2)
    if denominator == 0.0:
        return 1.0

    score = numerator / denominator
    return float(np.clip(score, -1.0, 1.0))


def validate_quality_metrics(
    clean: ArrayLike, test: ArrayLike
) -> tuple[float, float, float, float]:
    clean_np, test_np = _to_numpy(clean), _to_numpy(test)
    _validate_inputs(clean_np, test_np)
    mse_val = _mse_from_arrays(clean_np, test_np)
    snr_val = _snr_from_arrays(clean_np, test_np)
    data_range = _compute_data_range(clean_np, test_np, None)
    psnr_val = (
        math.inf
        if mse_val == 0.0
        else float(10.0 * math.log10((data_range * data_range) / mse_val))
    )
    ssim_val = ssim(clean_np, test_np, data_range=data_range)
    return mse_val, snr_val, psnr_val, ssim_val


__all__ = ["mse", "psnr", "snr", "ssim", "validate_quality_metrics"]
