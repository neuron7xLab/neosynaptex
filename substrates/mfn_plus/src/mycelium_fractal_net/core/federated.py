"""
Federated Learning Module — Byzantine-Robust Aggregation.

This module provides the public API for Byzantine-robust gradient aggregation
using Hierarchical Krum algorithm.

Conceptual domain: Federated learning, Byzantine fault tolerance

Reference:
    - docs/MFN_MATH_MODEL.md Appendix E (Byzantine-Robust Aggregation)
    - docs/ARCHITECTURE.md Section 7 (Federated Learning)

Mathematical Model:
    Krum(g_1, ..., g_n) = g_i where i = argmin_j s(g_j)

    s(g_j) = Σ_{k ∈ N_j} ||g_j - g_k||²

    N_j = set of (n - f - 2) nearest neighbors of g_j

Byzantine Tolerance:
    f < (n - 2) / 2

    With f_frac = 0.2 (20%), tolerates up to 20% adversarial clients.

Hierarchical Extension:
    Level 1: Cluster-wise Krum → One representative per cluster
    Level 2: 0.7 * Krum_result + 0.3 * Median_result

Parameters:
    num_clusters = 100      - Default cluster count
    byzantine_fraction = 0.2 - 20% tolerance
    sample_fraction = 0.1   - Sampling for large client counts

Example:
    >>> import torch
    >>> import numpy as np
    >>> from mycelium_fractal_net.core.federated import HierarchicalKrumAggregator
    >>> aggregator = HierarchicalKrumAggregator(num_clusters=10)
    >>> gradients = [torch.randn(100) for _ in range(50)]
    >>> rng = np.random.default_rng(42)
    >>> aggregated = aggregator.aggregate(gradients, rng)
    >>> aggregated.shape
    torch.Size([100])
"""

from __future__ import annotations

import math

import numpy as np

from mycelium_fractal_net._optional import require_ml_dependency

torch = require_ml_dependency("torch")

# Default federated learning parameters
NUM_CLUSTERS_DEFAULT: int = 100
BYZANTINE_FRACTION_DEFAULT: float = 0.2
SAMPLE_FRACTION_DEFAULT: float = 0.1

__all__ = [
    "BYZANTINE_FRACTION_DEFAULT",
    # Constants
    "NUM_CLUSTERS_DEFAULT",
    "SAMPLE_FRACTION_DEFAULT",
    # Classes
    "HierarchicalKrumAggregator",
    # Functions
    "aggregate_gradients_krum",
]


class HierarchicalKrumAggregator:
    """
    Hierarchical Krum aggregator for Byzantine-robust federated learning.

    Provides convergence guarantees when f < (n - 2) / 2 Byzantine clients.

    Parameters
    ----------
    num_clusters : int, optional
        Number of clusters for Level 1 aggregation, default 100.
    byzantine_fraction : float, optional
        Expected fraction of Byzantine clients, default 0.2.
    sample_fraction : float, optional
        Sampling fraction for large client counts, default 0.1.

    Raises
    ------
    ValueError
        If parameters are outside valid ranges.

    Reference
    ---------
    Blanchard, P. et al. (2017). Machine Learning with Adversaries:
    Byzantine Tolerant Gradient Descent. NeurIPS.
    """

    # Valid parameter ranges
    BYZANTINE_FRACTION_MAX: float = 0.5  # Must be < 50%
    MIN_CLIENTS_FOR_KRUM: int = 3

    def __init__(
        self,
        num_clusters: int = NUM_CLUSTERS_DEFAULT,
        byzantine_fraction: float = BYZANTINE_FRACTION_DEFAULT,
        sample_fraction: float = SAMPLE_FRACTION_DEFAULT,
    ) -> None:
        if num_clusters < 1:
            raise ValueError(f"num_clusters={num_clusters} must be >= 1")
        if not (0 <= byzantine_fraction < self.BYZANTINE_FRACTION_MAX):
            raise ValueError(
                f"byzantine_fraction={byzantine_fraction} must be in "
                f"[0, {self.BYZANTINE_FRACTION_MAX})"
            )
        if not (0 < sample_fraction <= 1):
            raise ValueError(f"sample_fraction={sample_fraction} must be in (0, 1]")

        self.num_clusters = num_clusters
        self.byzantine_fraction = byzantine_fraction
        self.sample_fraction = sample_fraction

    def _estimate_byzantine_count(self, group_size: int) -> int:
        """Estimate Byzantine budget while respecting Krum constraints.

        The theoretical guarantee for Krum requires ``n > 2f + 2`` where ``n``
        is the number of gradients and ``f`` the expected Byzantine count.
        This helper clamps the estimate to the maximum value that still
        satisfies the constraint and never forces at least one Byzantine client
        when the configured ``byzantine_fraction`` is zero.

        Args:
            group_size: Number of gradients available for aggregation.

        Returns:
            Clamped Byzantine count consistent with the current group size.
        """

        if group_size <= 0:
            return 0

        estimated = math.ceil(group_size * self.byzantine_fraction)
        max_allowed = max(0, (group_size - 3) // 2)

        return min(estimated, max_allowed)

    @staticmethod
    def _validate_gradient_shapes(gradients: list[torch.Tensor]) -> None:
        """Ensure all gradients share the same shape."""
        if not gradients:
            return
        reference_shape = gradients[0].shape
        for idx, grad in enumerate(gradients[1:], start=1):
            if grad.shape != reference_shape:
                raise ValueError(
                    "Inconsistent gradient dimensions: "
                    f"gradient[0] shape={reference_shape} "
                    f"!= gradient[{idx}] shape={grad.shape}"
                )

    def krum_select(
        self,
        gradients: list[torch.Tensor],
        num_byzantine: int,
    ) -> torch.Tensor:
        """
        Select gradient using Krum algorithm.

        Parameters
        ----------
        gradients : List[torch.Tensor]
            List of gradient tensors.
        num_byzantine : int
            Expected number of Byzantine gradients.

        Returns
        -------
        torch.Tensor
            Selected gradient.
        """
        n = len(gradients)
        if n == 0:
            raise ValueError("No gradients provided")
        if n == 1:
            return gradients[0]

        self._validate_gradient_shapes(gradients)

        # Krum requires at least n > 2f + 2 points to compute scores using
        # (n - f - 2) neighbors. Without this, the neighbor set is empty and
        # the algorithm loses its Byzantine robustness guarantee. The model
        # layer enforces this; the core implementation should mirror that
        # contract instead of silently proceeding with an invalid configuration.
        if n <= 2 * num_byzantine + 2:
            raise ValueError("Insufficient gradients for Krum: need more than 2f + 2 points")

        flat_grads = torch.stack([g.reshape(-1) for g in gradients])
        # Krum scoring uses squared Euclidean distances. Use the Gram-matrix
        # identity ||a-b||^2 = ||a||^2 + ||b||^2 - 2 a·b to avoid materializing
        # a huge (n, n, d) difference tensor for large gradient vectors.
        flat_grads = flat_grads.to(dtype=torch.float32, copy=False)
        gram = flat_grads @ flat_grads.T
        norms = gram.diag().unsqueeze(1)
        distances = (norms + norms.T - 2.0 * gram).clamp_min_(0.0)

        num_neighbors = max(1, n - num_byzantine - 2)

        scores = []
        for i in range(n):
            sorted_dists, _ = distances[i].sort()
            neighbor_dists = sorted_dists[1 : num_neighbors + 1]
            scores.append(neighbor_dists.sum().item())

        best_idx = int(np.argmin(scores))
        return gradients[best_idx].clone()

    def aggregate(
        self,
        client_gradients: list[torch.Tensor],
        rng: np.random.Generator | None = None,
    ) -> torch.Tensor:
        """
        Hierarchical aggregation with Krum + median.

        Parameters
        ----------
        client_gradients : List[torch.Tensor]
            Gradients from all clients.
        rng : np.random.Generator, optional
            Random generator for sampling and clustering.

        Returns
        -------
        torch.Tensor
            Aggregated gradient.
        """
        if len(client_gradients) == 0:
            raise ValueError("No gradients to aggregate")

        self._validate_gradient_shapes(client_gradients)

        if rng is None:
            rng = np.random.default_rng()

        n_clients = len(client_gradients)
        flat_dim = client_gradients[0].numel()

        # Fast path for extremely large gradients: avoid hierarchical Krum's
        # repeated full pairwise distance evaluations and instead compute a
        # robust center using coordinate-wise median plus trimmed-nearest mean.
        # This keeps large-model aggregation bounded while preserving a strong
        # outlier resistance profile for v1 local execution.
        if flat_dim >= 50_000 and n_clients >= 4:
            stacked = torch.stack([g.reshape(-1) for g in client_gradients]).to(dtype=torch.float32)
            median = torch.median(stacked, dim=0).values
            deviations = ((stacked - median) * (stacked - median)).sum(dim=1)
            keep = max(1, n_clients - self._estimate_byzantine_count(n_clients))
            keep_idx = torch.argsort(deviations)[:keep]
            trimmed_mean = stacked[keep_idx].mean(dim=0)
            return (
                (0.5 * trimmed_mean + 0.5 * median)
                .reshape(client_gradients[0].shape)
                .to(client_gradients[0].dtype)
            )

        # Sample clients if too many
        if n_clients > 1000:
            sample_size = max(1, int(np.ceil(n_clients * self.sample_fraction)))
            indices = rng.choice(n_clients, size=sample_size, replace=False)
            client_gradients = [client_gradients[i] for i in indices]

        # Assign to clusters
        n = len(client_gradients)
        actual_clusters = min(self.num_clusters, n)
        cluster_assignments = rng.integers(0, actual_clusters, size=n)

        # Level 1: Aggregate within clusters using Krum
        cluster_gradients = []
        for c in range(actual_clusters):
            cluster_mask = cluster_assignments == c
            cluster_grads = [g for g, m in zip(client_gradients, cluster_mask, strict=False) if m]
            if len(cluster_grads) > 0:
                cluster_byzantine = self._estimate_byzantine_count(len(cluster_grads))
                if len(cluster_grads) == 1:
                    # Single client in cluster: no neighbors to compare
                    selected = cluster_grads[0].clone()
                elif len(cluster_grads) <= 2 * cluster_byzantine + 2:
                    # Not enough gradients to satisfy Krum neighbor requirement;
                    # fall back to simple mean to retain stability.
                    selected = torch.stack(cluster_grads).mean(dim=0)
                else:
                    selected = self.krum_select(cluster_grads, cluster_byzantine)
                cluster_gradients.append(selected)

        if len(cluster_gradients) == 0:
            return client_gradients[0].clone()

        # Level 2: Global aggregation using Krum + median
        global_byzantine = self._estimate_byzantine_count(len(cluster_gradients))
        if len(cluster_gradients) <= 2 * global_byzantine + 2:
            krum_result = torch.stack(cluster_gradients).mean(dim=0)
        else:
            krum_result = self.krum_select(cluster_gradients, global_byzantine)

        stacked = torch.stack(cluster_gradients)
        median_result = torch.median(stacked, dim=0).values

        # Combine Krum and median (weighted average)
        result = 0.7 * krum_result + 0.3 * median_result

        return result


def aggregate_gradients_krum(
    gradients: list[torch.Tensor],
    num_clusters: int = NUM_CLUSTERS_DEFAULT,
    byzantine_fraction: float = BYZANTINE_FRACTION_DEFAULT,
    rng: np.random.Generator | None = None,
) -> torch.Tensor:
    """
    Convenience function for Byzantine-robust gradient aggregation.

    Parameters
    ----------
    gradients : List[torch.Tensor]
        Client gradients to aggregate.
    num_clusters : int, optional
        Number of clusters, default 100.
    byzantine_fraction : float, optional
        Expected Byzantine fraction, default 0.2.
    rng : np.random.Generator, optional
        Random generator for reproducibility.

    Returns
    -------
    torch.Tensor
        Aggregated gradient.

    Example
    -------
    >>> grads = [torch.randn(50) for _ in range(20)]
    >>> agg = aggregate_gradients_krum(grads, num_clusters=5)
    >>> agg.shape
    torch.Size([50])
    """
    aggregator = HierarchicalKrumAggregator(
        num_clusters=num_clusters,
        byzantine_fraction=byzantine_fraction,
    )
    return aggregator.aggregate(gradients, rng)
