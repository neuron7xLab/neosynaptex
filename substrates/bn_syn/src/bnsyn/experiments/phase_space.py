"""Deterministic phase-space analysis helpers for canonical evidence artifacts."""

from __future__ import annotations

from typing import Any

import numpy as np


def _validate_positive_int(value: int, *, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_nonnegative_int(value: int, *, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _as_valid_trace(name: str, values: np.ndarray) -> np.ndarray:
    trace = np.asarray(values, dtype=np.float64)
    if trace.ndim != 1:
        raise ValueError(f"{name} must be a 1-D array")
    if not np.all(np.isfinite(trace)):
        raise ValueError(f"{name} must contain only finite values")
    return trace


def coherence_from_voltages(voltages_mV: np.ndarray, vreset_mV: float, vthreshold_mV: float) -> float:
    """Compute a bounded Kuramoto-style coherence proxy from membrane voltages."""
    if not np.isfinite(vreset_mV) or not np.isfinite(vthreshold_mV):
        raise ValueError("vreset_mV and vthreshold_mV must be finite")
    if vthreshold_mV <= vreset_mV:
        raise ValueError("vthreshold_mV must be greater than vreset_mV")

    voltages = _as_valid_trace("voltages_mV", voltages_mV)
    if voltages.size == 0:
        return 0.0

    phases = np.clip((voltages - vreset_mV) / (vthreshold_mV - vreset_mV), 0.0, 1.0)
    theta = 2.0 * np.pi * phases
    coherence = float(np.abs(np.mean(np.exp(1j * theta))))
    return float(np.clip(coherence, 0.0, 1.0))


def _trace_index(values: np.ndarray, lower: float, upper: float, bins: int) -> np.ndarray:
    _validate_positive_int(bins, name="bins")
    if upper <= lower:
        return np.zeros(values.size, dtype=np.int64)
    scaled = (values - lower) / (upper - lower)
    return np.clip((scaled * (bins - 1)).astype(np.int64), 0, bins - 1)


def _draw_line(image: np.ndarray, x0: int, y0: int, x1: int, y1: int, value: int) -> None:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0

    while True:
        image[y, x] = min(image[y, x], value)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def build_phase_trajectory_image(x_trace: np.ndarray, y_trace: np.ndarray, width: int = 512, height: int = 512) -> np.ndarray:
    """Build deterministic grayscale trajectory image for a 2D phase-space trace."""
    _validate_positive_int(width, name="width")
    _validate_positive_int(height, name="height")

    x = _as_valid_trace("x_trace", x_trace)
    y = _as_valid_trace("y_trace", y_trace)
    if x.size != y.size:
        raise ValueError("x_trace and y_trace must have equal length")

    image = np.full((height, width), 255, dtype=np.uint8)
    if x.size == 0:
        return image

    x_idx = _trace_index(x, float(np.min(x)), float(np.max(x)), width)
    y_idx = _trace_index(y, float(np.min(y)), float(np.max(y)), height)
    y_idx = (height - 1) - y_idx

    image[y_idx, x_idx] = 0
    for idx in range(1, x.size):
        _draw_line(image, int(x_idx[idx - 1]), int(y_idx[idx - 1]), int(x_idx[idx]), int(y_idx[idx]), value=64)

    return image


def build_activity_map(rate_trace_hz: np.ndarray, sigma_trace: np.ndarray, grid_size: int = 64) -> tuple[np.ndarray, dict[str, float | int | list[str]]]:
    """Build deterministic occupancy map image and metadata for rate/sigma phase space."""
    _validate_positive_int(grid_size, name="grid_size")

    rates = _as_valid_trace("rate_trace_hz", rate_trace_hz)
    sigmas = _as_valid_trace("sigma_trace", sigma_trace)
    if rates.size != sigmas.size:
        raise ValueError("rate_trace_hz and sigma_trace must have equal length")

    counts = np.zeros((grid_size, grid_size), dtype=np.int64)
    if rates.size:
        x_idx = _trace_index(rates, float(np.min(rates)), float(np.max(rates)), grid_size)
        y_idx = _trace_index(sigmas, float(np.min(sigmas)), float(np.max(sigmas)), grid_size)
        for x_bin, y_bin in zip(x_idx.tolist(), y_idx.tolist()):
            counts[y_bin, x_bin] += 1

    occupied = int(np.count_nonzero(counts))
    total_cells = int(grid_size * grid_size)
    max_count = int(np.max(counts)) if rates.size else 0

    image = np.full((grid_size, grid_size), 255, dtype=np.uint8)
    if max_count > 0:
        scaled = np.floor(255.0 * (counts.astype(np.float64) / max_count)).astype(np.uint8)
        image = np.clip(255 - scaled, 0, 255).astype(np.uint8)
    image = np.flipud(image)

    metadata: dict[str, float | int | list[str]] = {
        "axes": ["population_rate_hz", "sigma"],
        "grid_size": int(grid_size),
        "occupied_cell_count": occupied,
        "occupied_cell_fraction": float(occupied / total_cells),
        "max_cell_count": max_count,
        "density_mean": float(np.mean(counts)),
    }
    return image, metadata


def build_phase_space_report(
    *,
    seed: int,
    n_neurons: int,
    dt_ms: float,
    duration_ms: float,
    steps: int,
    rate_trace_hz: np.ndarray,
    sigma_trace: np.ndarray,
    coherence_trace: np.ndarray,
) -> dict[str, Any]:
    """Build deterministic machine-readable phase-space evidence report."""
    _validate_nonnegative_int(steps, name="steps")

    rates = _as_valid_trace("rate_trace_hz", rate_trace_hz)
    sigmas = _as_valid_trace("sigma_trace", sigma_trace)
    coherence = _as_valid_trace("coherence_trace", coherence_trace)

    if rates.size != sigmas.size or rates.size != coherence.size:
        raise ValueError("rate_trace_hz, sigma_trace, and coherence_trace must have equal length")
    if rates.size != steps:
        raise ValueError("trace lengths must equal steps")
    if not np.all((coherence >= 0.0) & (coherence <= 1.0)):
        raise ValueError("coherence_trace must be bounded in [0, 1]")

    if rates.size == 0:
        rate_sigma_correlation = 0.0
        rate_coherence_correlation = 0.0
        trajectory_length_l2 = 0.0
        bbox = {"rate_min": 0.0, "rate_max": 0.0, "sigma_min": 0.0, "sigma_max": 0.0, "coherence_min": 0.0, "coherence_max": 0.0}
        centroid = {"rate": 0.0, "sigma": 0.0, "coherence": 0.0}
    else:
        rate_std = float(np.std(rates))
        sigma_std = float(np.std(sigmas))
        coherence_std = float(np.std(coherence))
        rate_sigma_correlation = 0.0 if rates.size < 2 or rate_std == 0.0 or sigma_std == 0.0 else float(np.corrcoef(rates, sigmas)[0, 1])
        rate_coherence_correlation = 0.0 if rates.size < 2 or rate_std == 0.0 or coherence_std == 0.0 else float(np.corrcoef(rates, coherence)[0, 1])

        d_rate = np.diff(rates)
        d_sigma = np.diff(sigmas)
        d_coherence = np.diff(coherence)
        trajectory_length_l2 = float(np.sum(np.sqrt(np.square(d_rate) + np.square(d_sigma) + np.square(d_coherence))))

        bbox = {
            "rate_min": float(np.min(rates)),
            "rate_max": float(np.max(rates)),
            "sigma_min": float(np.min(sigmas)),
            "sigma_max": float(np.max(sigmas)),
            "coherence_min": float(np.min(coherence)),
            "coherence_max": float(np.max(coherence)),
        }
        centroid = {
            "rate": float(np.mean(rates)),
            "sigma": float(np.mean(sigmas)),
            "coherence": float(np.mean(coherence)),
        }

    _, activity_map = build_activity_map(rates, sigmas)
    return {
        "schema_version": "1.1.0",
        "seed": seed,
        "N": int(n_neurons),
        "dt_ms": float(dt_ms),
        "duration_ms": float(duration_ms),
        "steps": int(steps),
        "state_axes": ["population_rate_hz", "sigma", "coherence"],
        "point_count": int(rates.size),
        "rate_mean_hz": float(np.mean(rates)) if rates.size else 0.0,
        "sigma_mean": float(np.mean(sigmas)) if sigmas.size else 0.0,
        "coherence_mean": float(np.mean(coherence)) if coherence.size else 0.0,
        "coherence_std": float(np.std(coherence)) if coherence.size else 0.0,
        "coherence_min": float(np.min(coherence)) if coherence.size else 0.0,
        "coherence_max": float(np.max(coherence)) if coherence.size else 0.0,
        "rate_sigma_correlation": rate_sigma_correlation,
        "rate_coherence_correlation": rate_coherence_correlation,
        "trajectory_length_l2": trajectory_length_l2,
        "bounding_box": bbox,
        "centroid": centroid,
        "activity_map": activity_map,
        "artifacts": {
            "plots": [
                "phase_space_rate_sigma.png",
                "phase_space_rate_coherence.png",
                "phase_space_activity_map.png",
            ],
            "traces": [
                "population_rate_trace.npy",
                "sigma_trace.npy",
                "coherence_trace.npy",
            ],
        },
    }
