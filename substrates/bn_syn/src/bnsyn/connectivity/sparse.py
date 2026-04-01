"""Sparse connectivity utilities with CSR representation.

Parameters
----------
None

Returns
-------
None

Notes
-----
Implements deterministic connectivity construction and metrics for SPEC P2-11.

References
----------
docs/SPEC.md#P2-11
docs/SSOT.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy.sparse as sp
from numpy.typing import NDArray

Float64Array = NDArray[np.float64]


@dataclass(frozen=True)
class SparseConnectivityMetrics:
    """Sparsity metrics and performance estimates.

    Parameters
    ----------
    density : float
        Fraction of non-zero entries.
    sparsity : float
        Fraction of zero entries.
    nnz : int
        Number of non-zero entries.
    memory_dense_mb : float
        Dense matrix size estimate in MB.
    memory_sparse_mb : float
        Sparse CSR size estimate in MB.
    speedup_estimated : float
        Heuristic speedup estimate for sparse vs dense.

    Notes
    -----
    Metrics are used for auditability and performance tracking.

    References
    ----------
    docs/SPEC.md#P2-11
    """

    density: float
    sparsity: float
    nnz: int
    memory_dense_mb: float
    memory_sparse_mb: float
    speedup_estimated: float


class SparseConnectivity:
    """Adaptive sparse/dense matrix dispatcher.

    Parameters
    ----------
    W : Float64Array
        Dense weight matrix (shape: [n_pre, n_post]).
    density_threshold : float, optional
        Density cutoff for sparse vs dense format.
    force_format : Literal["auto", "dense", "sparse"], optional
        Explicit format override.

    Raises
    ------
    ValueError
        If W is not 2D.

    Notes
    -----
    Automatically selects dense or sparse representation based on density.

    References
    ----------
    docs/SPEC.md#P2-11
    """

    def __init__(
        self,
        W: Float64Array,
        density_threshold: float = 0.10,
        force_format: Literal["auto", "dense", "sparse"] = "auto",
    ) -> None:
        """Initialize sparse connectivity storage and dispatch strategy.

        Parameters
        ----------
        W : Float64Array
            Synaptic weight matrix with shape ``(n_pre, n_post)``.
        density_threshold : float, optional
            Density cutoff used when ``force_format='auto'``; below cutoff selects CSR.
        force_format : Literal["auto", "dense", "sparse"], optional
            Explicit representation override. ``auto`` computes density from ``W``.

        Raises
        ------
        ValueError
            If ``W`` is not 2D.

        Notes
        -----
        Normalizes all numeric storage to float64 and computes stable metrics
        (density, nnz, memory estimates) used by downstream diagnostics.
        """
        if W.ndim != 2:
            raise ValueError("W must be 2D")
        if W.dtype != np.float64:
            W = np.asarray(W, dtype=np.float64)

        self.shape = W.shape
        n_pre, n_post = W.shape
        nnz = int(np.count_nonzero(W))
        density = nnz / (n_pre * n_post) if (n_pre * n_post) > 0 else 0.0

        if force_format == "auto":
            self.format: Literal["dense", "sparse"] = (
                "sparse" if density < density_threshold else "dense"
            )
        else:
            self.format = force_format

        if self.format == "sparse":
            self.W: sp.csr_matrix | Float64Array = sp.csr_matrix(W, dtype=np.float64)
        else:
            self.W = W.astype(np.float64, copy=False)

        self.metrics = SparseConnectivityMetrics(
            density=density,
            sparsity=1.0 - density,
            nnz=nnz,
            memory_dense_mb=(n_pre * n_post * 8) / (1024**2),
            memory_sparse_mb=self._estimate_sparse_size(n_pre, nnz),
            speedup_estimated=self._estimate_speedup(density),
        )

    @staticmethod
    def _estimate_sparse_size(n_pre: int, nnz: int) -> float:
        bytes_used = nnz * 8 + nnz * 4 + (n_pre + 1) * 4
        return bytes_used / (1024**2)

    @staticmethod
    def _estimate_speedup(density: float) -> float:
        if density >= 0.1:
            return 1.0
        return min(10.0, 2.0 ** (1.0 - density) / density) if density > 0 else 10.0

    def apply(self, x: Float64Array) -> Float64Array:
        """Compute y = W @ x with automatic format dispatch.

        Parameters
        ----------
        x : Float64Array
            Input vector (shape: [n_post]).

        Returns
        -------
        Float64Array
            Output vector (shape: [n_pre]).

        Notes
        -----
        Dispatches to dense or CSR multiplication based on internal format.
        """
        if self.format == "sparse":
            if not isinstance(self.W, sp.csr_matrix):
                raise TypeError(f"Expected csr_matrix for sparse format, got {type(self.W)}")
            y = self.W @ x
            if sp.issparse(y):
                return np.asarray(y.todense(), dtype=np.float64).ravel()
            return np.asarray(y, dtype=np.float64).ravel()
        return np.asarray(np.dot(self.W, x), dtype=np.float64)

    def to_dense(self) -> Float64Array:
        """Convert to dense matrix.

        Returns
        -------
        Float64Array
            Dense weight matrix.

        Notes
        -----
        Copies data if the internal representation is sparse.
        """
        if self.format == "sparse":
            if not isinstance(self.W, sp.csr_matrix):
                raise TypeError(f"Expected csr_matrix for sparse format, got {type(self.W)}")
            return np.asarray(self.W.todense(), dtype=np.float64)
        return np.asarray(self.W, dtype=np.float64)

    def to_sparse(self) -> sp.csr_matrix:
        """Convert to sparse CSR.

        Returns
        -------
        sp.csr_matrix
            Sparse CSR matrix representation.

        Notes
        -----
        Copies data if the internal representation is dense.
        """
        if self.format == "sparse":
            return self.W.copy()
        return sp.csr_matrix(self.W, dtype=np.float64)

    # ------------------------------------------------------------------
    # Mutation helpers for structural plasticity
    # ------------------------------------------------------------------

    def _recalculate_metrics(self) -> None:
        """Recalculate metrics from current W."""
        n_pre, n_post = self.shape
        if self.format == "sparse":
            assert isinstance(self.W, sp.csr_matrix)
            nnz = self.W.nnz
        else:
            nnz = int(np.count_nonzero(self.W))
        density = nnz / (n_pre * n_post) if (n_pre * n_post) > 0 else 0.0
        self.metrics = SparseConnectivityMetrics(
            density=density,
            sparsity=1.0 - density,
            nnz=nnz,
            memory_dense_mb=(n_pre * n_post * 8) / (1024**2),
            memory_sparse_mb=self._estimate_sparse_size(n_pre, nnz),
            speedup_estimated=self._estimate_speedup(density),
        )

    def mutate_add(self, row: int, col: int, value: float) -> None:
        """Add or update a synapse. Works on both dense and sparse formats."""
        if self.format == "dense":
            self.W[row, col] = value
        else:
            assert isinstance(self.W, sp.csr_matrix)
            lil = self.W.tolil()
            lil[row, col] = value
            self.W = lil.tocsr()
        self._recalculate_metrics()

    def mutate_remove(self, row: int, col: int) -> None:
        """Remove a synapse (set to zero). Works on both dense and sparse formats."""
        if self.format == "dense":
            self.W[row, col] = 0.0
        else:
            assert isinstance(self.W, sp.csr_matrix)
            lil = self.W.tolil()
            lil[row, col] = 0.0
            self.W = lil.tocsr()
            self.W.eliminate_zeros()
        self._recalculate_metrics()

    def rebuild_from_coo(
        self, rows: np.ndarray, cols: np.ndarray, values: np.ndarray
    ) -> None:
        """Rebuild internal storage from COO-format arrays. Updates metrics."""
        coo = sp.coo_matrix(
            (values.astype(np.float64), (rows, cols)), shape=self.shape
        )
        if self.format == "sparse":
            self.W = coo.tocsr()
        else:
            self.W = np.asarray(coo.todense(), dtype=np.float64)
        self._recalculate_metrics()

    def __repr__(self) -> str:
        return (
            f"SparseConnectivity(shape={self.shape}, "
            f"format={self.format}, density={self.metrics.density:.1%}, "
            f"memory={self.metrics.memory_sparse_mb:.2f}MB)"
        )


def build_random_connectivity(
    n_pre: int,
    n_post: int,
    connection_prob: float,
    *,
    rng: np.random.Generator,
    weight_mean: float = 1.0,
    weight_std: float = 0.1,
) -> SparseConnectivity:
    """Build Erdős-Rényi random connectivity with explicit RNG control.

    Parameters
    ----------
    n_pre : int
        Number of presynaptic neurons.
    n_post : int
        Number of postsynaptic neurons.
    connection_prob : float
        Connection probability in [0, 1].
    rng : np.random.Generator
        NumPy Generator for deterministic sampling.
    weight_mean : float, optional
        Mean weight for absolute normal sampling.
    weight_std : float, optional
        Standard deviation of weights.

    Returns
    -------
    SparseConnectivity
        SparseConnectivity instance.

    Raises
    ------
    ValueError
        If shapes or probabilities are invalid.

    Notes
    -----
    Determinism is achieved by passing a managed NumPy Generator.

    References
    ----------
    docs/SPEC.md#P2-11
    """
    if n_pre <= 0 or n_post <= 0:
        raise ValueError("n_pre and n_post must be positive")
    if not (0.0 <= connection_prob <= 1.0):
        raise ValueError("connection_prob must be in [0,1]")
    is_connected = rng.binomial(1, connection_prob, (n_pre, n_post))
    weights = np.abs(rng.normal(weight_mean, weight_std, (n_pre, n_post)))
    W = np.asarray(is_connected * weights, dtype=np.float64)
    return SparseConnectivity(W)
