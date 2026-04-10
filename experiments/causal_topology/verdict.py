"""Phase 11 — verdict logic for the causal-topology v4 protocol.

Nine gates. Any failure → TOPOLOGY_INDEPENDENT. Otherwise → CONVERGENCE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "VerdictInputs",
    "VerdictReport",
    "assign_verdict",
    "P_LIMIT",
    "NULL_P_LIMIT",
    "MOTIF_KL_MARGIN",
]

P_LIMIT = 0.01
NULL_P_LIMIT = 0.01
MOTIF_KL_MARGIN = 0.0
METRIC_AGREEMENT_MIN = 0.75  # ≥ 3/4
EDGE_PERSISTENCE_MIN = 0.6
DIRECTION_CONSISTENCY_MIN = 0.8


VerdictLabel = Literal["TOPOLOGY_CONVERGENCE", "TOPOLOGY_INDEPENDENT"]


@dataclass(frozen=True)
class VerdictInputs:
    delta_d: float
    mannwhitney_p: float
    null_worst_p: float
    motif_kl: float
    motif_kl_null: float
    metric_agreement_ratio: float
    segment_pass: bool
    edge_persistence: float
    direction_consistency: float
    aligned_vs_random_gap: float


@dataclass(frozen=True)
class VerdictReport:
    label: VerdictLabel
    gates_passed: tuple[str, ...]
    gates_failed: tuple[str, ...]


def assign_verdict(inp: VerdictInputs) -> VerdictReport:
    passed: list[str] = []
    failed: list[str] = []

    def _gate(name: str, ok: bool) -> None:
        (passed if ok else failed).append(name)

    _gate("delta_D>0", inp.delta_d > 0)
    _gate("mannwhitney_p<0.01", inp.mannwhitney_p < P_LIMIT)
    _gate("null_worst_p<0.01", inp.null_worst_p < NULL_P_LIMIT)
    _gate("motif_KL<motif_KL_null", inp.motif_kl < inp.motif_kl_null - MOTIF_KL_MARGIN)
    _gate("metric_agreement>=0.75", inp.metric_agreement_ratio >= METRIC_AGREEMENT_MIN)
    _gate("segment_pass", inp.segment_pass)
    _gate("edge_persistence>=0.6", inp.edge_persistence >= EDGE_PERSISTENCE_MIN)
    _gate("direction_consistency>=0.8", inp.direction_consistency >= DIRECTION_CONSISTENCY_MIN)
    _gate("aligned_vs_random_gap>0", inp.aligned_vs_random_gap > 0)

    label: VerdictLabel = "TOPOLOGY_CONVERGENCE" if not failed else "TOPOLOGY_INDEPENDENT"
    return VerdictReport(label=label, gates_passed=tuple(passed), gates_failed=tuple(failed))
