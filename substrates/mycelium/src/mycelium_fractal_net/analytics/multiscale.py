from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _downsample(field: NDArray[np.float64], factor: int) -> NDArray[np.float64]:
    rows = field.shape[0] // factor
    cols = field.shape[1] // factor
    trimmed = field[: rows * factor, : cols * factor]
    reshaped = trimmed.reshape(rows, factor, cols, factor)
    result: NDArray[np.float64] = reshaped.mean(axis=(1, 3))
    return result


def compute_multiscale_profile(field: NDArray[np.float64]) -> dict[str, float]:
    field = field.astype(np.float64)
    profile: dict[str, float] = {}
    thresholds = [-0.080, -0.070, -0.060, -0.050, -0.040]
    for thr in thresholds:
        profile[f"occupancy_thr_{int(thr * 1000)}"] = float(np.mean(field > thr))
    for factor in (1, 2, 4):
        if min(field.shape) // factor < 2:
            continue
        ds = field if factor == 1 else _downsample(field, factor)
        profile[f"scale_{factor}_mean"] = float(np.mean(ds))
        profile[f"scale_{factor}_std"] = float(np.std(ds))
        profile[f"scale_{factor}_range"] = float(np.max(ds) - np.min(ds))
    if min(field.shape) >= 4:
        coarse = _downsample(field, 2)
        coarse_up = coarse.repeat(2, axis=0)[: field.shape[0], :].repeat(2, axis=1)[
            :, : field.shape[1]
        ]
        profile["fine_structure_energy"] = float(np.mean(np.abs(field - coarse_up)))
    else:
        profile["fine_structure_energy"] = 0.0
    return profile
