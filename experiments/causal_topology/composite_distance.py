"""Phase 4 — composite topology distance.

D(G1, G2) = w_ged * GED_norm
          + w_spec * spectral_L2
          + w_motif * motif_KL
          + w_deg  * degree_corr_distance

Each term lives in [0, 1] (approximately) so the uniform weighting is
directly interpretable as an average similarity score. The scalar D
returned here feeds the regime-conditional analysis and the null
ensembles.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

from experiments.causal_topology.graph_similarity import (
    degree_sequence_distance,
    graph_edit_distance_normalized,
    spectral_graph_distance,
)
from experiments.causal_topology.motifs import kl_divergence, motif_distribution

__all__ = [
    "CompositeWeights",
    "composite_distance",
    "composite_components",
]


@dataclass(frozen=True)
class CompositeWeights:
    ged: float = 0.25
    spectral: float = 0.25
    motif: float = 0.25
    degree: float = 0.25

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.ged, self.spectral, self.motif, self.degree)


def composite_components(
    g1: nx.DiGraph,
    g2: nx.DiGraph,
    *,
    ged_timeout: float = 1.5,
) -> dict[str, float]:
    """Return the per-metric distance components."""
    ged = graph_edit_distance_normalized(g1, g2, timeout=ged_timeout)
    spec = spectral_graph_distance(g1, g2)
    m1 = motif_distribution(g1)
    m2 = motif_distribution(g2)
    motif = min(1.0, kl_divergence(m1.distribution, m2.distribution))
    deg = degree_sequence_distance(g1, g2)
    return {"ged": ged, "spectral": spec, "motif": motif, "degree": deg}


def composite_distance(
    g1: nx.DiGraph,
    g2: nx.DiGraph,
    weights: CompositeWeights | None = None,
    *,
    ged_timeout: float = 1.5,
) -> float:
    """Composite distance in [0, 1]."""
    w = weights or CompositeWeights()
    comps = composite_components(g1, g2, ged_timeout=ged_timeout)
    total = w.ged + w.spectral + w.motif + w.degree
    if total <= 0:
        return 0.0
    num = (
        w.ged * comps["ged"]
        + w.spectral * comps["spectral"]
        + w.motif * comps["motif"]
        + w.degree * comps["degree"]
    )
    return float(np.clip(num / total, 0.0, 1.0))
