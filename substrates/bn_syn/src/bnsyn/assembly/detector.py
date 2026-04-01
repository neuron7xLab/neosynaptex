"""Assembly detection via PCA + Marchenko-Pastur thresholding.

Reference: Lopes-dos-Santos et al., 2013 — detecting cell assemblies
from large neuronal populations using PCA and the Marchenko-Pastur
distribution as a significance threshold for eigenvalues of the
correlation matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]
Float64Array = NDArray[np.float64]


@dataclass(frozen=True)
class Assembly:
    """A single detected cell assembly."""

    index: int
    weights: Float64Array       # neuron participation weights (N,)
    eigenvalue: float           # explained variance
    core_neurons: list[int]     # neurons with |weight| > 2σ


@dataclass(frozen=True)
class AssemblyDetectionResult:
    """Result of assembly detection on a spike-count matrix."""

    assemblies: list[Assembly]
    n_significant: int
    marchenko_pastur_threshold: float
    total_variance_explained: float
    activation_traces: dict[int, Float64Array]  # assembly_idx → activation(t)
    timestamp_step: int


class AssemblyDetector:
    """Detect cell assemblies from spiking data using PCA + MP threshold.

    Parameters
    ----------
    N : int
        Number of neurons.
    bin_ms : float
        Bin width in milliseconds for spike-count binning.
    buffer_bins : int
        Maximum number of time bins stored in the ring buffer.
    """

    def __init__(self, N: int, bin_ms: float = 10.0, buffer_bins: int = 500) -> None:
        self._N = N
        self._bin_ms = bin_ms
        self._buffer_bins = buffer_bins

        # Ring buffer for spike counts: shape (N, buffer_bins)
        self._buffer: Float64Array = np.zeros((N, buffer_bins), dtype=np.float64)
        self._write_pos: int = 0
        self._total_bins_written: int = 0

        # Accumulator for current bin
        self._current_bin: Float64Array = np.zeros(N, dtype=np.float64)
        self._current_bin_start_step: int | None = None

        self._last_step: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(self, spiked: BoolArray, step: int) -> None:
        """Record a spike vector at the given simulation step.

        Parameters
        ----------
        spiked : BoolArray
            Boolean array of shape (N,) indicating which neurons spiked.
        step : int
            Current simulation time-step (integer, in dt units).
        """
        if self._current_bin_start_step is None:
            self._current_bin_start_step = step

        self._current_bin += spiked.astype(np.float64)
        self._last_step = step

        # Check if we have accumulated enough steps for one bin.
        # Assume 1 step = 1 ms for bin boundary calculation.
        elapsed = step - self._current_bin_start_step + 1
        if elapsed >= self._bin_ms:
            self._flush_bin()

    def detect(self) -> AssemblyDetectionResult:
        """Run assembly detection on the current buffer contents.

        Returns
        -------
        AssemblyDetectionResult
        """
        # Flush any partial bin so we don't lose data
        if np.any(self._current_bin > 0):
            self._flush_bin()

        T = min(self._total_bins_written, self._buffer_bins)
        if T < 2:
            return AssemblyDetectionResult(
                assemblies=[],
                n_significant=0,
                marchenko_pastur_threshold=0.0,
                total_variance_explained=0.0,
                activation_traces={},
                timestamp_step=self._last_step,
            )

        # Extract the filled portion of the buffer
        if self._total_bins_written <= self._buffer_bins:
            Z = self._buffer[:, :T].copy()
        else:
            # Ring buffer wrapped — reconstruct in temporal order
            Z = np.concatenate(
                [self._buffer[:, self._write_pos:],
                 self._buffer[:, :self._write_pos]],
                axis=1,
            )

        N = self._N

        # Z-score each neuron's time series
        means = Z.mean(axis=1, keepdims=True)
        stds = Z.std(axis=1, keepdims=True)
        stds[stds == 0] = 1.0  # avoid division by zero; row stays zero
        Z = (Z - means) / stds

        # Correlation matrix C = (1/T) Z Z^T
        C = Z @ Z.T / T

        # Eigendecomposition (symmetric)
        eigenvalues, eigenvectors = np.linalg.eigh(C)

        # Sort descending
        idx_sorted = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx_sorted]
        eigenvectors = eigenvectors[:, idx_sorted]

        # Marchenko-Pastur upper bound
        q = N / T
        lambda_mp = (1.0 + np.sqrt(q)) ** 2

        # Significant assemblies
        assemblies: list[Assembly] = []
        activation_traces: dict[int, Float64Array] = {}

        total_var = float(np.sum(eigenvalues))
        sig_var = 0.0

        for k in range(len(eigenvalues)):
            if eigenvalues[k] <= lambda_mp:
                break

            v_k = eigenvectors[:, k]
            ev = float(eigenvalues[k])
            sig_var += ev

            # Core neurons: |weight| > 2 * std(weights)
            weight_std = float(np.std(v_k))
            if weight_std > 0:
                core = [int(i) for i in range(N) if abs(v_k[i]) > 2.0 * weight_std]
            else:
                core = []

            assembly = Assembly(
                index=k,
                weights=v_k.copy(),
                eigenvalue=ev,
                core_neurons=core,
            )
            assemblies.append(assembly)

            # Activation trace: a_k(t) = z(t)^T P_k z(t)
            # where P_k = v_k v_k^T - I/N
            P_k = np.outer(v_k, v_k) - np.eye(N) / N
            trace = np.array(
                [float(Z[:, t] @ P_k @ Z[:, t]) for t in range(T)],
                dtype=np.float64,
            )
            activation_traces[k] = trace

        tve = sig_var / total_var if total_var > 0 else 0.0

        return AssemblyDetectionResult(
            assemblies=assemblies,
            n_significant=len(assemblies),
            marchenko_pastur_threshold=float(lambda_mp),
            total_variance_explained=tve,
            activation_traces=activation_traces,
            timestamp_step=self._last_step,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _flush_bin(self) -> None:
        """Write the current accumulator into the ring buffer and reset."""
        self._buffer[:, self._write_pos] = self._current_bin
        self._write_pos = (self._write_pos + 1) % self._buffer_bins
        self._total_bins_written += 1
        self._current_bin = np.zeros(self._N, dtype=np.float64)
        self._current_bin_start_step = None
