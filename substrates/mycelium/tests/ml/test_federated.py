"""
Tests for federated aggregation (Hierarchical Krum).

Focuses on correctness of the Krum distance metric: the algorithm must use
**squared** Euclidean distances when scoring candidate gradients. Using
unsquared distances can pick a different gradient and weaken robustness.
"""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.core.federated import HierarchicalKrumAggregator


def _manual_krum_index(gradients: list[torch.Tensor], num_byzantine: int) -> int:
    """Compute the expected Krum winner using squared distances."""
    flat = torch.stack([g.flatten() for g in gradients])
    pairwise_sq = torch.cdist(flat, flat, p=2).pow(2)
    num_neighbors = max(1, len(gradients) - num_byzantine - 2)

    scores = []
    for i in range(len(gradients)):
        sorted_dists, _ = pairwise_sq[i].sort()
        neighbor_dists = sorted_dists[1 : num_neighbors + 1]
        scores.append(neighbor_dists.sum().item())

    return int(torch.tensor(scores).argmin().item())


def test_krum_uses_squared_distances_for_scoring() -> None:
    """Aggregator should score candidates with squared Euclidean distances."""
    gradients = [
        torch.tensor([0.5005284547805786, 1.0223426818847656]),
        torch.tensor([-0.4412919878959656, 0.8895311951637268]),
        torch.tensor([0.9340492486953735, -0.32078808546066284]),
        torch.tensor([-0.9385855197906494, -1.7110832929611206]),
        torch.tensor([-0.7507101893424988, -0.6043558716773987]),
    ]

    aggregator = HierarchicalKrumAggregator(
        num_clusters=1,
        byzantine_fraction=0.0,  # deterministic neighbor count (n - 2)
    )

    expected_byzantine = aggregator._estimate_byzantine_count(len(gradients))
    expected_index = _manual_krum_index(gradients, expected_byzantine)

    result = aggregator.aggregate(gradients, rng=np.random.default_rng(0))

    assert torch.allclose(result, gradients[expected_index])


def test_aggregate_rejects_inconsistent_gradient_shapes() -> None:
    """Aggregator should fail fast on mismatched gradient shapes."""
    gradients = [
        torch.tensor([0.1, 0.2, 0.3]),
        torch.tensor([0.4, 0.5]),
    ]
    aggregator = HierarchicalKrumAggregator(num_clusters=1, byzantine_fraction=0.0)

    with pytest.raises(ValueError, match="Inconsistent gradient dimensions"):
        aggregator.aggregate(gradients)
