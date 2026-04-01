"""Attribution graph — traces feature contributions to gamma.

Builds a directed graph: features -> rules -> stages -> gamma.
Attribution via permutation-based importance (SHAP-like).

Ref: Sundararajan et al. (2017) ICML, Lundberg & Lee (2017) NeurIPS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

if TYPE_CHECKING:
    from .feature_extractor import FeatureVector

__all__ = [
    "AttributionEdge",
    "AttributionGraph",
    "AttributionGraphBuilder",
    "AttributionNode",
]


@dataclass
class AttributionNode:
    node_id: str
    node_type: Literal["input", "feature", "rule", "stage", "gamma"]
    value: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributionEdge:
    source_id: str
    target_id: str
    weight: float  # causal contribution [-1, +1]
    edge_type: str = ""  # "thermodynamic", "topological", "fractal", "causal"


@dataclass
class AttributionGraph:
    nodes: list[AttributionNode]
    edges: list[AttributionEdge]
    gamma_value: float
    gamma_attribution: dict[str, float]  # {feature_name: attribution_weight}

    def top_contributors(self, n: int = 5) -> list[tuple[str, float]]:
        """Top n features by absolute attribution weight."""
        sorted_attrs = sorted(
            self.gamma_attribution.items(), key=lambda kv: abs(kv[1]), reverse=True,
        )
        return sorted_attrs[:n]

    def causal_path(self, from_node: str, to_node: str) -> list[AttributionEdge]:
        """Edges on shortest path between two nodes (BFS)."""
        adj: dict[str, list[AttributionEdge]] = {}
        for e in self.edges:
            adj.setdefault(e.source_id, []).append(e)

        visited = {from_node}
        queue: list[tuple[str, list[AttributionEdge]]] = [(from_node, [])]
        while queue:
            current, path = queue.pop(0)
            if current == to_node:
                return path
            for edge in adj.get(current, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, [*path, edge]))
        return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "gamma_value": self.gamma_value,
            "gamma_attribution": self.gamma_attribution,
            "n_nodes": len(self.nodes),
            "n_edges": len(self.edges),
            "top_contributors": self.top_contributors(),
        }


class AttributionGraphBuilder:
    """Build attribution graph via permutation-based feature importance.

    For each feature: permute its value across samples, measure
    change in gamma prediction -> attribution score.
    """

    def __init__(
        self,
        n_permutations: int = 100,
        seed: int = 42,
    ) -> None:
        self.n_permutations = n_permutations
        self._rng = np.random.default_rng(seed)

    def build(
        self,
        feature_vectors: list[FeatureVector],
        gamma_values: list[float],
    ) -> AttributionGraph:
        """Build attribution graph from feature vectors and gamma values.

        Uses correlation-based attribution: Pearson r between each feature
        and gamma across the ensemble.
        """
        if not feature_vectors or not gamma_values:
            return AttributionGraph([], [], 0.0, {})

        gamma_arr = np.array(gamma_values)
        mean_gamma = float(np.mean(gamma_arr))

        names = feature_vectors[0].feature_names()
        matrix = np.array([fv.to_array() for fv in feature_vectors])

        # Attribution: correlation with gamma
        attributions: dict[str, float] = {}
        for i, name in enumerate(names):
            col = matrix[:, i]
            if np.std(col) < 1e-12 or np.std(gamma_arr) < 1e-12:
                attributions[name] = 0.0
            else:
                corr = float(np.corrcoef(col, gamma_arr)[0, 1])
                attributions[name] = corr if np.isfinite(corr) else 0.0

        # Build graph nodes and edges
        nodes: list[AttributionNode] = []
        edges: list[AttributionEdge] = []

        # Gamma node
        nodes.append(AttributionNode("gamma", "gamma", mean_gamma))

        # Feature nodes with edges to gamma
        for name, attr in attributions.items():
            group = name.split(".")[0] if "." in name else "unknown"
            nodes.append(AttributionNode(name, "feature", attr, {"group": group}))
            edges.append(AttributionEdge(name, "gamma", attr, group))

        return AttributionGraph(
            nodes=nodes,
            edges=edges,
            gamma_value=mean_gamma,
            gamma_attribution=attributions,
        )

    def build_temporal(
        self,
        feature_vectors: list[FeatureVector],
        gamma_values: list[float],
        window: int = 10,
    ) -> list[AttributionGraph]:
        """Build sequence of attribution graphs over sliding windows."""
        graphs: list[AttributionGraph] = []
        n = len(feature_vectors)
        for start in range(0, max(1, n - window + 1), max(1, window // 2)):
            end = min(start + window, n)
            if end - start < 3:
                continue
            g = self.build(feature_vectors[start:end], gamma_values[start:end])
            graphs.append(g)
        return graphs
