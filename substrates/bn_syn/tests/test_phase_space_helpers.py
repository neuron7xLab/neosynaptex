from __future__ import annotations

import numpy as np
import pytest

from bnsyn.experiments.phase_space import (
    build_activity_map,
    build_phase_space_report,
    build_phase_trajectory_image,
    coherence_from_voltages,
)


def test_coherence_from_voltages_bounds_and_edge_branches() -> None:
    assert coherence_from_voltages(np.asarray([], dtype=np.float64), -58.0, -55.0) == 0.0

    voltages = np.asarray([-58.0, -58.0, -58.0], dtype=np.float64)
    coherence = coherence_from_voltages(voltages, -58.0, -55.0)
    assert 0.0 <= coherence <= 1.0
    assert coherence == pytest.approx(1.0)

    with pytest.raises(ValueError, match="finite"):
        coherence_from_voltages(np.asarray([np.nan], dtype=np.float64), -58.0, -55.0)


def test_phase_trajectory_image_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        build_phase_trajectory_image(
            np.asarray([0.0, 1.0], dtype=np.float64),
            np.asarray([0.0], dtype=np.float64),
        )


def test_phase_trajectory_image_deterministic_handcrafted_input() -> None:
    x = np.asarray([0.0, 1.0, 1.5, 3.0], dtype=np.float64)
    y = np.asarray([1.0, 2.0, 1.0, 3.0], dtype=np.float64)
    image_a = build_phase_trajectory_image(x, y, width=32, height=24)
    image_b = build_phase_trajectory_image(x, y, width=32, height=24)
    assert np.array_equal(image_a, image_b)


def test_activity_map_deterministic_handcrafted_input() -> None:
    rates = np.asarray([0.0, 1.0, 1.0, 2.0], dtype=np.float64)
    sigmas = np.asarray([1.0, 1.0, 2.0, 2.0], dtype=np.float64)
    image_a, metadata_a = build_activity_map(rates, sigmas, grid_size=16)
    image_b, metadata_b = build_activity_map(rates, sigmas, grid_size=16)
    assert np.array_equal(image_a, image_b)
    assert metadata_a == metadata_b
    assert metadata_a["axes"] == ["population_rate_hz", "sigma"]


def test_phase_space_report_rejects_nonfinite_traces() -> None:
    with pytest.raises(ValueError, match="finite"):
        build_phase_space_report(
            seed=1,
            n_neurons=2,
            dt_ms=1.0,
            duration_ms=3.0,
            steps=3,
            rate_trace_hz=np.asarray([1.0, np.inf, 3.0], dtype=np.float64),
            sigma_trace=np.asarray([1.0, 1.1, 1.2], dtype=np.float64),
            coherence_trace=np.asarray([0.1, 0.2, 0.3], dtype=np.float64),
        )


def test_phase_space_report_rejects_out_of_bounds_coherence() -> None:
    with pytest.raises(ValueError, match="bounded"):
        build_phase_space_report(
            seed=1,
            n_neurons=2,
            dt_ms=1.0,
            duration_ms=3.0,
            steps=3,
            rate_trace_hz=np.asarray([1.0, 2.0, 3.0], dtype=np.float64),
            sigma_trace=np.asarray([1.0, 1.1, 1.2], dtype=np.float64),
            coherence_trace=np.asarray([0.1, 1.2, 0.3], dtype=np.float64),
        )


def test_phase_space_report_trajectory_metric_semantics_3d() -> None:
    rates = np.asarray([0.0, 3.0], dtype=np.float64)
    sigmas = np.asarray([0.0, 4.0], dtype=np.float64)
    coherence = np.asarray([0.0, 0.12], dtype=np.float64)
    report = build_phase_space_report(
        seed=1,
        n_neurons=2,
        dt_ms=1.0,
        duration_ms=2.0,
        steps=2,
        rate_trace_hz=rates,
        sigma_trace=sigmas,
        coherence_trace=coherence,
    )
    expected = float(np.sqrt(3.0**2 + 4.0**2 + 0.12**2))
    assert report["trajectory_length_l2"] == pytest.approx(expected)


def test_coherence_from_voltages_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        coherence_from_voltages(np.asarray([0.0], dtype=np.float64), np.nan, -55.0)
    with pytest.raises(ValueError, match="greater than"):
        coherence_from_voltages(np.asarray([0.0], dtype=np.float64), -55.0, -55.0)


def test_phase_trajectory_image_rejects_invalid_dims_and_non_1d_trace() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        build_phase_trajectory_image(np.asarray([1.0]), np.asarray([1.0]), width=0)
    with pytest.raises(ValueError, match="1-D"):
        build_phase_trajectory_image(np.asarray([[1.0]], dtype=np.float64), np.asarray([1.0]))


def test_phase_trajectory_image_empty_trace_returns_blank_canvas() -> None:
    image = build_phase_trajectory_image(np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64), width=8, height=6)
    assert image.shape == (6, 8)
    assert np.all(image == 255)


def test_activity_map_rejects_mismatch_and_invalid_grid() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        build_activity_map(np.asarray([1.0]), np.asarray([1.0]), grid_size=0)
    with pytest.raises(ValueError, match="equal length"):
        build_activity_map(np.asarray([1.0, 2.0]), np.asarray([1.0]), grid_size=4)


def test_phase_space_report_rejects_negative_steps() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        build_phase_space_report(
            seed=1,
            n_neurons=2,
            dt_ms=1.0,
            duration_ms=1.0,
            steps=-1,
            rate_trace_hz=np.asarray([], dtype=np.float64),
            sigma_trace=np.asarray([], dtype=np.float64),
            coherence_trace=np.asarray([], dtype=np.float64),
        )
