"""Mathematical Frontier — unified report from 5 mechanisms.

Single call: report = run_math_frontier(seq)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from .causal_emergence import (
    compute_causal_emergence,
    discretize_field_pca,
)
from .fisher_information import FIMResult, compute_fim
from .rmt_spectral import RMTDiagnostics, rmt_diagnostics
from .tda_ews import TopologicalSignature, compute_tda
from .unified_score import UnifiedScore, compute_unified_score
from .wasserstein_geometry import wasserstein_distance

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["MathFrontierReport", "run_math_frontier"]


@dataclass
class MathFrontierReport:
    """Unified report from all 5 mathematical mechanisms."""

    topology: TopologicalSignature
    w2_trajectory_speed: float
    causal_emergence_score: float
    fim: FIMResult | None
    rmt: RMTDiagnostics | None
    unified: UnifiedScore | None
    compute_time_ms: float

    def summary(self) -> str:
        """Single-line summary."""
        topo = (
            f"b0={self.topology.beta_0} b1={self.topology.beta_1} "
            f"TP0={self.topology.total_pers_0:.3f}"
        )
        w2 = f"W2={self.w2_trajectory_speed:.4f}"
        ce = f"CE={self.causal_emergence_score:.4f}"
        fim = f"FIM={self.fim.epistemic_value:.3f}" if self.fim else "FIM=skip"
        rmt_label = (
            "struct"
            if self.rmt and "Poisson" in self.rmt.structure_type
            else "random"
            if self.rmt and "GOE" in self.rmt.structure_type
            else "inter"
            if self.rmt
            else ""
        )
        rmt = f"r={self.rmt.r_ratio:.3f}({rmt_label})" if self.rmt else "RMT=skip"
        jko = self.unified.summary() if self.unified else "JKO=skip"
        return f"[MATH] {topo} | {w2} | {ce} | {fim} | {rmt} | {jko} ({self.compute_time_ms:.0f}ms)"

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict of all frontier results."""
        return {
            "topology": self.topology.to_dict(),
            "w2_trajectory_speed": round(self.w2_trajectory_speed, 4),
            "causal_emergence": round(self.causal_emergence_score, 4),
            "fim": self.fim.to_dict() if self.fim else None,
            "rmt": self.rmt.to_dict() if self.rmt else None,
            "unified": self.unified.to_dict() if self.unified else None,
            "compute_time_ms": round(self.compute_time_ms, 1),
        }


def run_math_frontier(
    seq: Any,
    run_rmt: bool = True,
    run_fim: bool = False,
    fim_simulate_fn: Callable[[np.ndarray], np.ndarray] | None = None,
    fim_theta: np.ndarray | None = None,
    physarum_state: Any | None = None,
) -> MathFrontierReport:
    """Run all 5 mechanisms on a FieldSequence. ~300ms for N=32.

    Args:
        physarum_state: Pre-computed PhysarumState (with D_h, D_v).
            If provided AND run_rmt=True, RMT uses this state's conductivity
            directly instead of re-creating a Physarum engine from scratch.
            Pass bio.physarum_state from BioExtension to avoid duplication.
    """
    t0 = time.perf_counter()

    # 1. TDA
    topo = compute_tda(seq.field, min_persistence_frac=0.005)

    # 2. W2 trajectory speed (sinkhorn for N<=64, sliced for N>64)
    w2_speed = wasserstein_distance(seq.history[0], seq.field, method="auto")

    # 3. Causal Emergence — PCA-based discretization replaces per-frame heuristic
    seq.history.shape[0]
    states_micro = discretize_field_pca(seq.history, n_macro_states=4)
    tpm_micro = np.zeros((4, 4))
    for t in range(len(states_micro) - 1):
        tpm_micro[states_micro[t], states_micro[t + 1]] += 1
    row_s = tpm_micro.sum(axis=1, keepdims=True)
    row_s[row_s < 1] = 1
    tpm_micro /= row_s
    # Macro: 2-state coarsening (lower vs upper half of PCA states)
    states_macro = (states_micro >= 2).astype(int)
    tpm_macro = np.zeros((2, 2))
    for t in range(len(states_macro) - 1):
        tpm_macro[states_macro[t], states_macro[t + 1]] += 1
    row_m = tpm_macro.sum(axis=1, keepdims=True)
    row_m[row_m < 1] = 1
    tpm_macro /= row_m
    ce_result = compute_causal_emergence(tpm_micro, tpm_macro=tpm_macro)
    ce_score = float(ce_result.CE_macro)

    # 4. FIM (optional — expensive)
    fim_result: FIMResult | None = None
    if run_fim and fim_simulate_fn is not None and fim_theta is not None:
        try:
            fim_result = compute_fim(fim_simulate_fn, fim_theta)
        except Exception:
            pass  # FIM may fail for degenerate parameter spaces

    # 5. RMT — reuse physarum_state if provided, otherwise create fresh
    rmt_result: RMTDiagnostics | None = None
    if run_rmt:
        try:
            from mycelium_fractal_net.bio.memory_anonymization import GapJunctionDiffuser

            if physarum_state is not None:
                # Reuse pre-computed conductivity — no duplicate Physarum init
                D_h = physarum_state.D_h
                D_v = physarum_state.D_v
            else:
                from mycelium_fractal_net.bio.physarum import PhysarumEngine

                N = seq.field.shape[0]
                eng = PhysarumEngine(N)
                src = seq.field > 0
                snk = seq.field < -0.05
                phys = eng.initialize(src, snk)
                for _ in range(3):
                    phys = eng.step(phys, src, snk)
                D_h = phys.D_h
                D_v = phys.D_v

            diff = GapJunctionDiffuser()
            L = diff.build_laplacian(D_h, D_v).toarray()
            rmt_result = rmt_diagnostics(L)
        except Exception:
            pass  # RMT requires bio extras

    # 6. Unified JKO/HWI score
    unified_result: UnifiedScore | None = None
    try:
        unified_result = compute_unified_score(
            field_current=seq.history[0],
            field_reference=seq.field,
            CE=ce_score,
            beta_0=topo.beta_0,
            beta_1=topo.beta_1,
        )
    except Exception:
        pass  # unified score optional — W2 may fail for degenerate fields

    elapsed = (time.perf_counter() - t0) * 1000
    return MathFrontierReport(
        topology=topo,
        w2_trajectory_speed=w2_speed,
        causal_emergence_score=ce_score,
        fim=fim_result,
        rmt=rmt_result,
        unified=unified_result,
        compute_time_ms=elapsed,
    )
