"""Geometric Integrated Information (Phi*) approximation via coalitional MI.

Notes
-----
Computes Phi* on random subnetworks using Gaussian mutual information
and exhaustive bipartition search (n <= 16) or greedy spectral bisection (n > 16).

References
----------
Oizumi, Albantakis, Tononi (2014). From the Phenomenology to the Mechanisms
of Consciousness: Integrated Information Theory 3.0. PLoS Comput Biol.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]
Float64Array = NDArray[np.float64]

logger = logging.getLogger(__name__)

_EXHAUSTIVE_LIMIT = 16


@dataclass(frozen=True)
class PhiProxyParams:
    """Parameters for the Phi-Proxy engine.

    Parameters
    ----------
    subnetwork_size : int
        Number of neurons per random subsample.
    n_subsamples : int
        Number of random subnetwork draws.
    time_lag : int
        Lag in bins between X_t and X_{t+1}.
    bin_ms : float
        Bin width in milliseconds for spike count vectors.
    min_observations : int
        Minimum number of time bins required before computing.
    regularization : float
        Tikhonov regularization added to covariance diagonal.
    """

    subnetwork_size: int = 12
    n_subsamples: int = 5
    time_lag: int = 1
    bin_ms: float = 5.0
    min_observations: int = 200
    regularization: float = 1e-6


@dataclass(frozen=True)
class PhiResult:
    """Result of a Phi* computation.

    Parameters
    ----------
    phi_mean : float
        Mean Phi* across subsamples.
    phi_std : float
        Standard deviation of Phi* across subsamples.
    phi_max : float
        Maximum Phi* across subsamples.
    phi_shuffled_mean : float
        Mean Phi* from time-shuffled null model.
    phi_z_score : float
        Z-score: (phi_mean - phi_shuffled_mean) / phi_shuffled_std.
    n_subsamples : int
        Number of subsamples actually used.
    best_partition : tuple[list[int], list[int]]
        Minimum information partition for the most integrated subsample.
    timestamp_step : int
        Simulation step at which this result was computed.
    """

    phi_mean: float
    phi_std: float
    phi_max: float
    phi_shuffled_mean: float
    phi_z_score: float
    n_subsamples: int
    best_partition: tuple[list[int], list[int]]
    timestamp_step: int


def _regularized_cov(
    data: Float64Array, reg: float
) -> Float64Array:
    """Compute regularized covariance matrix.

    Parameters
    ----------
    data : Float64Array
        Shape (n_observations, n_features).
    reg : float
        Regularization strength added to diagonal.

    Returns
    -------
    Float64Array
        Regularized covariance matrix of shape (n_features, n_features).
    """
    cov = np.cov(data, rowvar=False)
    if cov.ndim == 0:
        cov = cov.reshape(1, 1)
    cov += reg * np.eye(cov.shape[0])
    return cov


def _log_det_cholesky(cov: Float64Array) -> float:
    """Log-determinant via Cholesky decomposition.

    Parameters
    ----------
    cov : Float64Array
        Positive-definite covariance matrix.

    Returns
    -------
    float
        log(det(cov)).
    """
    L = np.linalg.cholesky(cov)
    return float(2.0 * np.sum(np.log(np.diag(L))))


def _gaussian_mi(
    X: Float64Array, Y: Float64Array, reg: float
) -> float:
    """Gaussian mutual information I(X; Y).

    Computes 0.5 * log(det(Sigma_X) * det(Sigma_Y) / det(Sigma_XY)).

    Parameters
    ----------
    X : Float64Array
        Shape (T, d_x).
    Y : Float64Array
        Shape (T, d_y).
    reg : float
        Regularization for covariance matrices.

    Returns
    -------
    float
        Mutual information in nats.
    """
    cov_x = _regularized_cov(X, reg)
    cov_y = _regularized_cov(Y, reg)
    XY = np.hstack([X, Y])
    cov_xy = _regularized_cov(XY, reg)

    log_det_x = _log_det_cholesky(cov_x)
    log_det_y = _log_det_cholesky(cov_y)
    log_det_xy = _log_det_cholesky(cov_xy)

    mi = 0.5 * (log_det_x + log_det_y - log_det_xy)
    return max(mi, 0.0)


def _exhaustive_min_partition(
    X_t: Float64Array,
    X_t1: Float64Array,
    reg: float,
) -> tuple[float, list[int], list[int]]:
    """Find the minimum information partition via exhaustive bipartition search.

    Parameters
    ----------
    X_t : Float64Array
        Shape (T, n). Present-time binned spike counts.
    X_t1 : Float64Array
        Shape (T, n). Future-time binned spike counts.
    reg : float
        Regularization.

    Returns
    -------
    tuple[float, list[int], list[int]]
        (max_partitioned_mi, part_A_indices, part_B_indices).
    """
    n = X_t.shape[1]
    indices = list(range(n))
    half = n // 2
    best_mi = -np.inf
    best_a: list[int] = []
    best_b: list[int] = []

    for combo in itertools.combinations(indices, half):
        a = list(combo)
        b = [i for i in indices if i not in combo]
        # Avoid double-counting symmetric partitions when n is even
        # by only considering combos where the first element is 0
        if n % 2 == 0 and len(combo) > 0 and combo[0] != 0:
            continue

        mi_a = _gaussian_mi(X_t[:, a], X_t1[:, a], reg)
        mi_b = _gaussian_mi(X_t[:, b], X_t1[:, b], reg)
        mi_sum = mi_a + mi_b

        if mi_sum > best_mi:
            best_mi = mi_sum
            best_a = a
            best_b = b

    return best_mi, best_a, best_b


def _spectral_bisection(
    X_t: Float64Array,
    X_t1: Float64Array,
    reg: float,
) -> tuple[float, list[int], list[int]]:
    """Greedy spectral bisection for large subnetworks (n > 16).

    Uses the Fiedler vector of the cross-covariance to split.

    Parameters
    ----------
    X_t : Float64Array
        Shape (T, n).
    X_t1 : Float64Array
        Shape (T, n).
    reg : float
        Regularization.

    Returns
    -------
    tuple[float, list[int], list[int]]
        (partitioned_mi, part_A_indices, part_B_indices).
    """
    n = X_t.shape[1]
    # Build affinity from cross-covariance magnitude
    XY = np.hstack([X_t, X_t1])
    cov_full = _regularized_cov(XY, reg)
    cross_cov = cov_full[:n, n:]
    affinity = np.abs(cross_cov) + np.abs(cross_cov.T)
    np.fill_diagonal(affinity, 0.0)

    # Laplacian
    degree = np.diag(affinity.sum(axis=1))
    laplacian = degree - affinity

    eigvals, eigvecs = np.linalg.eigh(laplacian)
    # Fiedler vector is the second smallest eigenvector
    fiedler = eigvecs[:, 1]

    a = [i for i in range(n) if fiedler[i] <= 0.0]
    b = [i for i in range(n) if fiedler[i] > 0.0]

    # Ensure non-trivial partition
    if len(a) == 0 or len(b) == 0:
        half = n // 2
        a = list(range(half))
        b = list(range(half, n))

    mi_a = _gaussian_mi(X_t[:, a], X_t1[:, a], reg)
    mi_b = _gaussian_mi(X_t[:, b], X_t1[:, b], reg)

    return mi_a + mi_b, a, b


def _compute_phi_star(
    X_t: Float64Array,
    X_t1: Float64Array,
    reg: float,
) -> tuple[float, list[int], list[int]]:
    """Compute Phi* for a single subnetwork.

    Parameters
    ----------
    X_t : Float64Array
        Shape (T, n).
    X_t1 : Float64Array
        Shape (T, n).
    reg : float
        Regularization.

    Returns
    -------
    tuple[float, list[int], list[int]]
        (phi_star, part_A, part_B).
    """
    n = X_t.shape[1]
    whole_mi = _gaussian_mi(X_t, X_t1, reg)

    if n <= _EXHAUSTIVE_LIMIT:
        part_mi, a, b = _exhaustive_min_partition(X_t, X_t1, reg)
    else:
        part_mi, a, b = _spectral_bisection(X_t, X_t1, reg)

    phi = whole_mi - part_mi
    return max(phi, 0.0), a, b


class PhiProxyEngine:
    """Geometric Integrated Information (Phi*) approximation engine.

    Parameters
    ----------
    N : int
        Total number of neurons in the network.
    params : PhiProxyParams
        Configuration parameters.
    rng : numpy.random.Generator
        Random number generator for reproducibility.
    """

    def __init__(
        self,
        N: int,
        params: PhiProxyParams,
        rng: np.random.Generator,
    ) -> None:
        self._N = N
        self._params = params
        self._rng = rng

        # Ring buffer: store raw spike vectors, will bin later
        # Need enough raw steps so that after binning we have >= min_observations bins
        bin_size = max(1, int(params.bin_ms))
        self._capacity = params.min_observations * bin_size * 4
        self._buffer: list[BoolArray] = []
        self._step_buffer: list[int] = []
        self._last_step = -1

    def observe(self, spiked: BoolArray, step: int) -> None:
        """Record a spike observation.

        Parameters
        ----------
        spiked : BoolArray
            Boolean array of shape (N,) indicating which neurons spiked.
        step : int
            Current simulation step.
        """
        self._buffer.append(spiked.copy())
        self._step_buffer.append(step)
        self._last_step = step

        # Trim ring buffer
        if len(self._buffer) > self._capacity:
            excess = len(self._buffer) - self._capacity
            self._buffer = self._buffer[excess:]
            self._step_buffer = self._step_buffer[excess:]

    def _bin_spikes(self) -> Float64Array:
        """Bin raw spike observations into spike count vectors.

        Returns
        -------
        Float64Array
            Shape (n_bins, N) of spike counts per bin.
        """
        if len(self._buffer) == 0:
            return np.empty((0, self._N), dtype=np.float64)

        raw = np.array(self._buffer, dtype=np.float64)  # (T_raw, N)
        n_raw = raw.shape[0]
        bin_size = max(1, int(self._params.bin_ms))
        n_bins = n_raw // bin_size

        if n_bins == 0:
            return np.empty((0, self._N), dtype=np.float64)

        trimmed = raw[: n_bins * bin_size]
        binned = trimmed.reshape(n_bins, bin_size, self._N).sum(axis=1)
        return np.asarray(binned)

    def compute(self) -> PhiResult | None:
        """Compute Phi* across random subnetwork subsamples.

        Returns
        -------
        PhiResult or None
            Phi* statistics, or None if insufficient data.
        """
        binned = self._bin_spikes()
        n_bins = binned.shape[0]
        lag = self._params.time_lag

        if n_bins - lag < self._params.min_observations:
            return None

        X_full_t = binned[:-lag]
        X_full_t1 = binned[lag:]
        X_full_t.shape[0]

        sub_size = min(self._params.subnetwork_size, self._N)
        if sub_size < 2:
            return None

        phi_values: list[float] = []
        best_phi = -1.0
        best_part: tuple[list[int], list[int]] = ([], [])
        best_neurons: list[int] = []
        sampled_neuron_sets: list[list[int]] = []

        for _ in range(self._params.n_subsamples):
            neurons = sorted(
                self._rng.choice(self._N, size=sub_size, replace=False).tolist()
            )
            sampled_neuron_sets.append(neurons)
            X_t = X_full_t[:, neurons]
            X_t1 = X_full_t1[:, neurons]

            phi, a, b = _compute_phi_star(X_t, X_t1, self._params.regularization)
            phi_values.append(phi)

            if phi > best_phi:
                best_phi = phi
                best_part = (a, b)
                best_neurons = neurons

        # Null model: time-shuffle the same subnetworks and recompute
        n_shuffles = max(5, self._params.n_subsamples)
        shuffled_phis: list[float] = []

        for i in range(n_shuffles):
            neurons = sampled_neuron_sets[i % len(sampled_neuron_sets)]
            X_t = X_full_t[:, neurons].copy()
            X_t1 = X_full_t1[:, neurons].copy()

            # Shuffle each neuron's time series independently
            for col in range(sub_size):
                self._rng.shuffle(X_t[:, col])
                self._rng.shuffle(X_t1[:, col])

            phi_s, _, _ = _compute_phi_star(X_t, X_t1, self._params.regularization)
            shuffled_phis.append(phi_s)

        phi_arr = np.array(phi_values)
        shuf_arr = np.array(shuffled_phis)
        shuf_std = float(np.std(shuf_arr))
        shuf_mean = float(np.mean(shuf_arr))

        if shuf_std > 0:
            z_score = (float(np.mean(phi_arr)) - shuf_mean) / shuf_std
        else:
            z_score = 0.0 if float(np.mean(phi_arr)) == shuf_mean else float("inf")

        # Map local partition indices back to global neuron IDs
        global_a = [best_neurons[i] for i in best_part[0]]
        global_b = [best_neurons[i] for i in best_part[1]]

        return PhiResult(
            phi_mean=float(np.mean(phi_arr)),
            phi_std=float(np.std(phi_arr)),
            phi_max=float(np.max(phi_arr)),
            phi_shuffled_mean=shuf_mean,
            phi_z_score=z_score,
            n_subsamples=len(phi_values),
            best_partition=(global_a, global_b),
            timestamp_step=self._last_step,
        )
