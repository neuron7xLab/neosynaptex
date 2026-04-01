from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def compute_temporal_features(history: NDArray[np.float64] | None) -> dict[str, float]:
    if history is None or history.shape[0] < 2:
        return {
            "volatility": 0.0,
            "entropy_drift": 0.0,
            "recurrence": 1.0,
            "delta_mean_abs": 0.0,
            "delta_max_abs": 0.0,
            "temporal_smoothness": 1.0,
            "trajectory_energy": 0.0,
        }
    hist = history.astype(np.float64)
    deltas = np.diff(hist, axis=0)
    delta_mean_abs = float(np.mean(np.abs(deltas)))
    delta_max_abs = float(np.max(np.abs(deltas)))
    volatility = float(np.mean(np.std(deltas, axis=(1, 2))))
    trajectory_energy = float(np.mean(np.linalg.norm(deltas.reshape(deltas.shape[0], -1), axis=1)))
    temporal_smoothness = float(1.0 / (1.0 + delta_mean_abs * 200.0))
    value_min = float(np.min(hist))
    value_max = float(np.max(hist))
    if abs(value_max - value_min) < 1e-12:
        entropies = [0.0 for _ in range(hist.shape[0])]
    else:
        bins = np.linspace(value_min, value_max + 1e-12, 16)
        entropies = []
        for frame in hist:
            counts, _ = np.histogram(frame, bins=bins, density=False)
            probs = counts.astype(np.float64)
            probs = probs / max(1.0, probs.sum())
            probs = probs[probs > 0]
            entropies.append(float(-(probs * np.log(probs)).sum()))
    entropy_drift = float(entropies[-1] - entropies[0]) if len(entropies) >= 2 else 0.0
    baseline = hist[0].ravel()
    tail = hist[-1].ravel()
    norm = float(np.linalg.norm(baseline) * np.linalg.norm(tail))
    recurrence = float(np.dot(baseline, tail) / norm) if norm > 0 else 1.0
    return {
        "volatility": volatility,
        "entropy_drift": entropy_drift,
        "recurrence": recurrence,
        "delta_mean_abs": delta_mean_abs,
        "delta_max_abs": delta_max_abs,
        "temporal_smoothness": temporal_smoothness,
        "trajectory_energy": trajectory_energy,
    }
