"""Tests for sparse connectivity utilities."""

from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from bnsyn.connectivity.sparse import SparseConnectivity, build_random_connectivity


def test_sparse_connectivity_dense_roundtrip() -> None:
    W = np.array([[0.0, 1.0], [2.0, 0.0]], dtype=np.float32)
    conn = SparseConnectivity(W, force_format="dense")

    x = np.array([1.0, 2.0], dtype=np.float64)
    y = conn.apply(x)
    assert y.dtype == np.float64
    np.testing.assert_allclose(y, np.dot(W, x))

    dense = conn.to_dense()
    np.testing.assert_allclose(dense, W)

    sparse = conn.to_sparse()
    np.testing.assert_allclose(sparse.todense(), W)


def test_sparse_connectivity_sparse_roundtrip() -> None:
    W = np.array([[0.0, 0.0], [3.0, 0.0]], dtype=np.float64)
    conn = SparseConnectivity(W, force_format="sparse")
    x = np.array([2.0, 1.0], dtype=np.float64)
    y = conn.apply(x)
    np.testing.assert_allclose(y, np.dot(W, x))
    dense = conn.to_dense()
    np.testing.assert_allclose(dense, W)

    sparse = conn.to_sparse()
    np.testing.assert_allclose(sparse.todense(), W)


def test_sparse_connectivity_sparse_internal_type_errors() -> None:
    W = np.array([[0.0, 0.0], [3.0, 0.0]], dtype=np.float64)
    conn = SparseConnectivity(W, force_format="sparse")
    conn.W = W  # type: ignore[assignment]
    with pytest.raises(TypeError, match="Expected csr_matrix"):
        conn.apply(np.array([1.0, 2.0]))
    with pytest.raises(TypeError, match="Expected csr_matrix"):
        conn.to_dense()


def test_sparse_connectivity_sparse_returns_sparse_y() -> None:
    W = np.array([[1.0, 0.0], [0.0, 2.0]], dtype=np.float64)
    conn = SparseConnectivity(W, force_format="sparse")
    x = sp.csr_matrix(np.array([[1.0], [2.0]]))
    y = conn.apply(x)
    np.testing.assert_allclose(y, np.array([1.0, 4.0]))


def test_sparse_connectivity_auto_density_threshold() -> None:
    dense = np.ones((2, 2), dtype=np.float64)
    dense_conn = SparseConnectivity(dense, density_threshold=0.9)
    assert dense_conn.format == "dense"

    sparse = np.zeros((2, 2), dtype=np.float64)
    sparse_conn = SparseConnectivity(sparse, density_threshold=0.9)
    assert sparse_conn.format == "sparse"


def test_sparse_connectivity_repr_contains_metrics() -> None:
    W = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.float64)
    conn = SparseConnectivity(W, force_format="dense")
    text = repr(conn)
    assert "SparseConnectivity" in text
    assert "density" in text


def test_sparse_connectivity_invalid_shape() -> None:
    with pytest.raises(ValueError, match="W must be 2D"):
        SparseConnectivity(np.zeros((2, 2, 2)))


def test_build_random_connectivity_validation() -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="n_pre and n_post must be positive"):
        build_random_connectivity(0, 1, 0.1, rng=rng)
    with pytest.raises(ValueError, match="connection_prob must be in \\[0,1\\]"):
        build_random_connectivity(1, 1, 1.5, rng=rng)


def test_build_random_connectivity_deterministic() -> None:
    rng = np.random.default_rng(123)
    conn = build_random_connectivity(2, 3, 0.5, rng=rng, weight_mean=1.0, weight_std=0.0)
    assert conn.W.shape == (2, 3) or conn.to_dense().shape == (2, 3)
    assert conn.metrics.nnz >= 0
