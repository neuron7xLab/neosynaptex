from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def detect_change_points(history: NDArray[np.float64] | None) -> dict[str, float]:
    if history is None or history.shape[0] < 3:
        return {
            "change_score": 0.0,
            "change_index": 0.0,
            "baseline_delta": 0.0,
            "peak_delta": 0.0,
        }
    deltas = np.mean(np.abs(np.diff(history.astype(np.float64), axis=0)), axis=(1, 2))
    baseline = float(np.median(deltas))
    mad = float(np.median(np.abs(deltas - baseline))) + 1e-12
    idx = int(np.argmax(deltas))
    peak = float(deltas[idx])
    robust_z = (peak - baseline) / (1.4826 * mad)
    score = float(1.0 / (1.0 + np.exp(-0.75 * (robust_z - 1.0))))
    return {
        "change_score": score,
        "change_index": float(idx + 1),
        "baseline_delta": baseline,
        "peak_delta": peak,
    }
