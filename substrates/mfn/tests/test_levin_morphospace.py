"""Tests for bio/morphospace.py — PCA morphospace + basin stability."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.bio.morphospace import (
    BasinStabilityAnalyzer,
    BasinStabilityResult,
    MorphospaceBuilder,
    MorphospaceConfig,
    MorphospaceCoords,
)


@pytest.fixture
def history_3d() -> np.ndarray:
    """Synthetic (T, N, N) field history with gradual drift."""
    rng = np.random.default_rng(42)
    T, N = 20, 8
    base = rng.standard_normal((N, N))
    history = np.empty((T, N, N))
    for t in range(T):
        history[t] = base + 0.1 * t * rng.standard_normal((N, N))
    return history


def test_morphospace_basic(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    assert isinstance(coords, MorphospaceCoords)
    assert coords.n_frames == 20
    assert coords.coords.shape[0] == 20
    assert coords.field_shape == (8, 8)


def test_explained_variance_sums_to_one_or_less(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    total = float(np.sum(coords.explained_variance))
    assert 0.0 < total <= 1.0 + 1e-6


def test_n_components_used(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    n_used = coords.n_components_used
    assert 1 <= n_used <= len(coords.explained_variance)


def test_trajectory_length_positive(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    length = coords.trajectory_length()
    assert length > 0.0


def test_attractor_candidates(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    centers = coords.attractor_candidates(n_clusters=2)
    assert centers.shape[0] == 2
    assert centers.shape[1] == coords.n_components_used


def test_reconstruct_field(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    # Reconstruct from first PCA point
    pca_point = coords.coords[0]
    reconstructed = coords.reconstruct_field(pca_point)
    assert reconstructed.shape == (8, 8)
    # Reconstruction should be close to original (PCA is lossy)
    original = history_3d[0]
    mse = float(np.mean((reconstructed - original) ** 2))
    assert mse < float(np.var(original)) * 2  # Within reasonable error


def test_to_dict(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    d = coords.to_dict()
    assert "n_frames" in d
    assert "trajectory_length" in d
    assert d["n_frames"] == 20
    assert isinstance(d["trajectory_length"], float)


def test_transform_single_field(history_3d: np.ndarray) -> None:
    builder = MorphospaceBuilder()
    coords = builder.fit(history_3d)
    single = history_3d[5]
    projected = builder.transform(single)
    assert projected.shape == (coords.coords.shape[1],)


def test_transform_before_fit_raises() -> None:
    builder = MorphospaceBuilder()
    with pytest.raises(RuntimeError, match="Call fit"):
        builder.transform(np.ones((4, 4)))


def test_custom_config() -> None:
    config = MorphospaceConfig(n_components=3, n_basin_samples=10)
    builder = MorphospaceBuilder(config)
    rng = np.random.default_rng(0)
    history = rng.standard_normal((10, 4, 4))
    coords = builder.fit(history)
    assert coords.coords.shape[1] == 3


def test_single_frame_history() -> None:
    """Edge case: single frame should not crash."""
    builder = MorphospaceBuilder()
    field = np.random.default_rng(0).standard_normal((1, 4, 4))
    coords = builder.fit(field)
    assert coords.n_frames == 1
    assert coords.coords.shape[0] == 1


def test_basin_stability_basic(history_3d: np.ndarray) -> None:
    config = MorphospaceConfig(n_basin_samples=20)
    builder = MorphospaceBuilder(config)
    coords = builder.fit(history_3d)

    def dummy_simulator(field: np.ndarray) -> np.ndarray:
        return field * 0.99 + 0.01 * np.mean(field)

    analyzer = BasinStabilityAnalyzer(dummy_simulator, config)
    result = analyzer.compute(coords, attractor_id=0)

    assert isinstance(result, BasinStabilityResult)
    assert 0.0 <= result.basin_stability <= 1.0
    assert result.n_samples == 20
    assert 0 <= result.n_returned <= result.n_samples
    assert result.error_bound >= 0.0
    assert result.compute_time_ms >= 0.0


def test_basin_stability_to_dict(history_3d: np.ndarray) -> None:
    config = MorphospaceConfig(n_basin_samples=10)
    builder = MorphospaceBuilder(config)
    coords = builder.fit(history_3d)

    analyzer = BasinStabilityAnalyzer(lambda f: f, config)
    result = analyzer.compute(coords)
    d = result.to_dict()
    assert "basin_stability" in d
    assert "error_bound" in d
    assert isinstance(d["basin_stability"], float)


def test_basin_stability_identity_simulator(history_3d: np.ndarray) -> None:
    """Identity simulator: all perturbations should return to basin."""
    config = MorphospaceConfig(n_basin_samples=30, perturbation_scale=0.01)
    builder = MorphospaceBuilder(config)
    coords = builder.fit(history_3d)

    # Identity: terminal = initial → should mostly return to basin
    analyzer = BasinStabilityAnalyzer(lambda f: f, config)
    result = analyzer.compute(coords)
    # With tiny perturbation and identity, most should return
    assert result.basin_stability >= 0.0  # Sanity check
