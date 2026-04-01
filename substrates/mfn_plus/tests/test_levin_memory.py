"""Tests for bio/memory_anonymization.py — gap junction diffusion on HDV memory."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.bio.memory_anonymization import (
    AnonymizationConfig,
    AnonymizationMetrics,
    GapJunctionDiffuser,
    HDVFieldEncoder,
)


@pytest.fixture
def small_field() -> np.ndarray:
    """4×4 synthetic field."""
    return np.random.default_rng(42).standard_normal((4, 4))


@pytest.fixture
def conductivities() -> tuple[np.ndarray, np.ndarray]:
    """Physarum-like conductivities for 4×4 grid."""
    rng = np.random.default_rng(42)
    D_h = np.abs(rng.standard_normal((4, 3))) + 0.01
    D_v = np.abs(rng.standard_normal((3, 4))) + 0.01
    return D_h, D_v


# === HDVFieldEncoder ===


def test_encoder_basic(small_field: np.ndarray) -> None:
    enc = HDVFieldEncoder(D=500, neighborhood=1, seed=0)
    memory = enc.encode(small_field)
    assert memory.shape == (16, 500)
    assert set(np.unique(memory)).issubset({-1.0, 1.0})


def test_encoder_no_nan(small_field: np.ndarray) -> None:
    enc = HDVFieldEncoder(D=1000, seed=0)
    memory = enc.encode(small_field)
    assert not np.any(np.isnan(memory))


def test_encoder_deterministic(small_field: np.ndarray) -> None:
    enc = HDVFieldEncoder(D=500, seed=42)
    m1 = enc.encode(small_field)
    m2 = enc.encode(small_field)
    np.testing.assert_array_equal(m1, m2)


def test_encoder_different_seeds(small_field: np.ndarray) -> None:
    m1 = HDVFieldEncoder(D=500, seed=0).encode(small_field)
    m2 = HDVFieldEncoder(D=500, seed=1).encode(small_field)
    # Different seeds should produce different encodings
    assert not np.array_equal(m1, m2)


def test_encoder_neighborhood_0(small_field: np.ndarray) -> None:
    """Neighborhood=0 means each cell encodes only itself."""
    enc = HDVFieldEncoder(D=500, neighborhood=0, seed=0)
    memory = enc.encode(small_field)
    assert memory.shape == (16, 500)


def test_encoder_larger_neighborhood(small_field: np.ndarray) -> None:
    enc = HDVFieldEncoder(D=500, neighborhood=2, seed=0)
    memory = enc.encode(small_field)
    assert memory.shape == (16, 500)


# === GapJunctionDiffuser — Laplacian ===


def test_laplacian_shape(
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    diffuser = GapJunctionDiffuser()
    L = diffuser.build_laplacian(D_h, D_v)
    assert L.shape == (16, 16)


def test_laplacian_symmetric(
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    diffuser = GapJunctionDiffuser()
    L = diffuser.build_laplacian(D_h, D_v)
    L_dense = L.toarray()
    np.testing.assert_allclose(L_dense, L_dense.T, atol=1e-10)


def test_laplacian_row_sum(
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    """Unnormalized Laplacian rows should sum to ~0 (off-diag = -w, diag = sum w)."""
    D_h, D_v = conductivities
    config = AnonymizationConfig(normalize_laplacian=False)
    diffuser = GapJunctionDiffuser(config)
    L = diffuser.build_laplacian(D_h, D_v)
    row_sums = np.array(L.sum(axis=1)).ravel()
    np.testing.assert_allclose(row_sums, 0.0, atol=1e-10)


def test_laplacian_positive_semidefinite(
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    config = AnonymizationConfig(normalize_laplacian=False)
    diffuser = GapJunctionDiffuser(config)
    L = diffuser.build_laplacian(D_h, D_v)
    eigvals = np.linalg.eigvalsh(L.toarray())
    assert np.all(eigvals >= -1e-10)


# === GapJunctionDiffuser — Diffusion ===


def test_diffusion_basic(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    diffuser = GapJunctionDiffuser()
    diffused, metrics = diffuser.diffuse(memory, D_h, D_v)
    assert diffused.shape == memory.shape
    assert isinstance(metrics, AnonymizationMetrics)


def test_diffusion_output_binary(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    diffuser = GapJunctionDiffuser()
    diffused, _ = diffuser.diffuse(memory, D_h, D_v)
    assert set(np.unique(diffused)).issubset({-1.0, 1.0})


def test_diffusion_no_nan(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    diffuser = GapJunctionDiffuser()
    diffused, _ = diffuser.diffuse(memory, D_h, D_v)
    assert not np.any(np.isnan(diffused))


def test_metrics_valid(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    diffuser = GapJunctionDiffuser()
    _, metrics = diffuser.diffuse(memory, D_h, D_v)
    assert metrics.n_cells == 16
    assert metrics.n_steps == 10
    assert metrics.effective_rank_before >= 1
    assert metrics.effective_rank_after >= 1
    assert 0.0 <= metrics.anonymization_score <= 1.0
    assert 0.0 <= metrics.cosine_anonymity <= 1.0


def test_metrics_to_dict(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    diffuser = GapJunctionDiffuser()
    _, metrics = diffuser.diffuse(memory, D_h, D_v)
    d = metrics.to_dict()
    assert "entropy_before" in d
    assert "anonymization_score" in d
    assert "cosine_anonymity" in d
    assert isinstance(d["n_cells"], int)


def test_zero_conductivity() -> None:
    """Zero conductivity → no diffusion → output ≈ input."""
    D_h = np.zeros((4, 3))
    D_v = np.zeros((3, 4))
    enc = HDVFieldEncoder(D=200, seed=0)
    field = np.random.default_rng(0).standard_normal((4, 4))
    memory = enc.encode(field)
    config = AnonymizationConfig(min_conductance=0.0, normalize_laplacian=False)
    diffuser = GapJunctionDiffuser(config)
    diffused, _ = diffuser.diffuse(memory, D_h, D_v)
    # With zero conductivity, Laplacian is zero → no diffusion
    np.testing.assert_array_equal(diffused, memory)


def test_high_alpha_changes_memory(
    small_field: np.ndarray,
    conductivities: tuple[np.ndarray, np.ndarray],
) -> None:
    """High alpha should produce noticeable diffusion effect."""
    D_h, D_v = conductivities
    enc = HDVFieldEncoder(D=500, seed=0)
    memory = enc.encode(small_field)
    config = AnonymizationConfig(alpha=10.0, dt=0.1, n_diffusion_steps=50)
    diffuser = GapJunctionDiffuser(config)
    diffused, _ = diffuser.diffuse(memory, D_h, D_v)
    # At least some cells should have changed
    changed = np.sum(diffused != memory)
    assert changed > 0
