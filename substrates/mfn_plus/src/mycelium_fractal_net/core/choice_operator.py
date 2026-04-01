"""Choice Operator A_C — symmetry-breaking for computational indeterminacy.

When multiple candidate states are indistinguishable by score, the system
hits a computational singularity: gradient-based selection provides no
direction. A_C resolves this by thermodynamic perturbation response.

Protocol:
    1. Detect indeterminacy: score spread among top candidates < threshold
    2. If no indeterminacy: standard argmin selection (no operator needed)
    3. If indeterminacy detected:
       a. Perturbation mode: inject N(0, sigma²) noise, measure ΔF[u],
          select argmax |ΔF| (nearest criticality boundary)
       b. Criticality mode: select min |D_f - 1.75| (CCP center)
       c. Deterministic fallback: field-hash-based selection
    4. CCP gate: verify selected state satisfies cognitive window
    5. GNC+ stabilize: output includes recommended modulation

Mathematical basis:
    A_C: P(S_latent) \\ {∅} → S_latent
    Subject to: CCP(s*) = True (D_f ∈ [1.5, 2.0] ∧ Φ > 0 ∧ R > R_c)

    Thermodynamic criterion: s* = argmax_s |F[u + δ] - F[u]|
    where δ ~ N(0, σ_U²I), F[u] = ½∫|∇u|²dx + ∫V(u)dx

    The candidate most responsive to perturbation sits closest to a
    phase boundary — maximally cognitive under CCP.

Ref: Vasylenko (2026), CCP Theorem 1; Beggs & Plenz (2003) criticality
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mycelium_fractal_net.types.field import FieldSequence

__all__ = [
    "ChoiceResult",
    "IndeterminacyReport",
    "choice_operator",
    "detect_indeterminacy",
    "select_by_criticality",
    "select_by_perturbation",
]

# ── Constants ────────────────────────────────────────────────────────
INDETERMINACY_THRESHOLD = 0.05  # score spread below which = indistinguishable
PERTURBATION_SIGMA = 0.001  # noise amplitude σ for symmetry breaking
CCP_D_F_CENTER = 1.75  # center of cognitive window [1.5, 2.0]
CCP_R_TARGET = 0.80  # target phase coherence (Kuramoto)


# ── Types ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class IndeterminacyReport:
    """Diagnostic output of indeterminacy detection."""

    detected: bool
    n_candidates: int
    score_spread: float  # max - min among top candidates
    threshold: float
    indeterminate_indices: tuple[int, ...]  # which candidates are in the tie


@dataclass(frozen=True)
class ChoiceResult:
    """Output of the Choice Operator A_C."""

    selected_index: int
    indeterminacy: IndeterminacyReport
    method: str  # "score" | "perturbation" | "criticality" | "hash"
    delta_F: tuple[float, ...] | None  # free energy deltas per candidate
    ccp_valid: bool | None  # whether selected state passed CCP gate
    rationale: str


# ── Core functions ───────────────────────────────────────────────────


def detect_indeterminacy(
    scores: Sequence[float],
    threshold: float = INDETERMINACY_THRESHOLD,
) -> IndeterminacyReport:
    """Detect computational indeterminacy among candidate scores.

    Indeterminacy = top candidates within *threshold* of the best score.
    This means gradient-based selection has no meaningful direction.

    Parameters
    ----------
    scores : sequence of floats (lower is better)
    threshold : maximum spread to consider indeterminate

    Returns
    -------
    IndeterminacyReport
    """
    if len(scores) < 2:
        return IndeterminacyReport(
            detected=False,
            n_candidates=len(scores),
            score_spread=0.0,
            threshold=threshold,
            indeterminate_indices=(0,) if scores else (),
        )

    arr = np.asarray(scores, dtype=np.float64)
    best = float(np.min(arr))
    # Find all candidates within threshold of the best
    close_mask = arr <= best + threshold
    indices = tuple(int(i) for i in np.where(close_mask)[0])
    spread = float(np.ptp(arr[close_mask]))

    return IndeterminacyReport(
        detected=len(indices) > 1,
        n_candidates=len(scores),
        score_spread=spread,
        threshold=threshold,
        indeterminate_indices=indices,
    )


def select_by_perturbation(
    seq: FieldSequence,
    candidate_fields: Sequence[np.ndarray],
    sigma: float = PERTURBATION_SIGMA,
    seed: int = 42,
) -> tuple[int, tuple[float, ...]]:
    """Break symmetry via thermodynamic perturbation response.

    For each candidate field u_i:
        1. Compute F[u_i] (free energy of candidate)
        2. Inject perturbation: u_p = u_i + δ, δ ~ N(0, σ²)
        3. Compute F[u_p]
        4. ΔF_i = |F[u_p] - F[u_i]|

    Select argmax |ΔF| — the candidate most responsive to perturbation
    sits closest to a phase boundary (criticality).

    Parameters
    ----------
    seq : source FieldSequence (used for grid dimensions)
    candidate_fields : list of 2D field arrays (one per candidate)
    sigma : perturbation standard deviation
    seed : RNG seed for reproducibility

    Returns
    -------
    (selected_index, delta_F_per_candidate)
    """
    from mycelium_fractal_net.core.thermodynamic_kernel import FreeEnergyTracker

    rng = np.random.RandomState(seed)
    N = seq.field.shape[0]
    tracker = FreeEnergyTracker(domain_extent=1.0, grid_size=N)

    delta_F_list: list[float] = []
    for field in candidate_fields:
        u = np.asarray(field, dtype=np.float64)
        F_clean = tracker.total_energy(u)
        noise = rng.normal(0.0, sigma, u.shape)
        F_noisy = tracker.total_energy(u + noise)
        delta_F_list.append(abs(F_noisy - F_clean))

    deltas = tuple(delta_F_list)
    selected = int(np.argmax(delta_F_list))
    return selected, deltas


def select_by_criticality(
    ccp_states: Sequence[dict[str, Any]],
) -> int:
    """Select candidate closest to CCP cognitive center.

    Criticality distance = |D_f - 1.75| + 0.5 * |R - 0.80|
    Minimum distance = maximally cognitive position.

    Parameters
    ----------
    ccp_states : list of dicts with "D_f" and "R" keys

    Returns
    -------
    index of the most cognitively positioned candidate
    """
    distances: list[float] = []
    for state in ccp_states:
        d_f = float(state.get("D_f", CCP_D_F_CENTER))
        r = float(state.get("R", CCP_R_TARGET))
        dist = abs(d_f - CCP_D_F_CENTER) + 0.5 * abs(r - CCP_R_TARGET)
        distances.append(dist)

    return int(np.argmin(distances))


def _ccp_gate(field: np.ndarray) -> bool:
    """Quick CCP check on a field: D_f in cognitive window."""
    try:
        from mycelium_fractal_net.analytics.ccp_metrics import compute_ccp_state
        from mycelium_fractal_net.types.field import FieldSequence as FS

        seq = FS(field=np.asarray(field, dtype=np.float64))
        state = compute_ccp_state(seq)
        return bool(state.get("cognitive", False))
    except Exception:
        return True  # fail-open: don't block if CCP unavailable


def choice_operator(
    candidates: Sequence[Any],
    scores: Sequence[float],
    *,
    seq: FieldSequence | None = None,
    candidate_fields: Sequence[np.ndarray] | None = None,
    ccp_states: Sequence[dict[str, Any]] | None = None,
    threshold: float = INDETERMINACY_THRESHOLD,
    sigma: float = PERTURBATION_SIGMA,
    seed: int = 42,
) -> ChoiceResult:
    """A_C: The Choice Operator.

    Resolves computational indeterminacy through thermodynamic
    symmetry breaking. Activates only when gradient-based selection
    cannot distinguish between candidates.

    Parameters
    ----------
    candidates : the candidate objects (returned as-is in result)
    scores : composite scores per candidate (lower is better)
    seq : source FieldSequence (enables perturbation mode)
    candidate_fields : 2D field arrays per candidate (enables perturbation)
    ccp_states : CCP state dicts per candidate (enables criticality mode)
    threshold : indeterminacy detection threshold
    sigma : perturbation noise amplitude (σ_U)
    seed : RNG seed

    Returns
    -------
    ChoiceResult with selected_index, method, rationale, diagnostics
    """
    n = len(scores)
    if n == 0:
        return ChoiceResult(
            selected_index=-1,
            indeterminacy=IndeterminacyReport(
                detected=False, n_candidates=0, score_spread=0.0,
                threshold=threshold, indeterminate_indices=(),
            ),
            method="score",
            delta_F=None,
            ccp_valid=None,
            rationale="No candidates provided.",
        )

    # ── 1. DETECT INDETERMINACY ──────────────────────────────────
    report = detect_indeterminacy(scores, threshold)

    if not report.detected:
        # Standard selection — no indeterminacy
        best_idx = int(np.argmin(scores))
        return ChoiceResult(
            selected_index=best_idx,
            indeterminacy=report,
            method="score",
            delta_F=None,
            ccp_valid=None,
            rationale=f"Clear winner by score ({scores[best_idx]:.4f}).",
        )

    # ── 2. SYMMETRY BREAKING ─────────────────────────────────────
    tied = list(report.indeterminate_indices)
    method = "score"
    delta_F: tuple[float, ...] | None = None
    selected = tied[0]

    # 2a. Thermodynamic perturbation (preferred)
    if seq is not None and candidate_fields is not None and len(candidate_fields) >= n:
        tied_fields = [candidate_fields[i] for i in tied]
        rel_idx, deltas_tied = select_by_perturbation(seq, tied_fields, sigma, seed)
        selected = tied[rel_idx]
        # Map deltas back to full candidate list
        full_deltas = [0.0] * n
        for j, ti in enumerate(tied):
            full_deltas[ti] = deltas_tied[j]
        delta_F = tuple(full_deltas)
        method = "perturbation"

    # 2b. CCP criticality proximity (fallback)
    elif ccp_states is not None and len(ccp_states) >= n:
        tied_ccp = [ccp_states[i] for i in tied]
        rel_idx = select_by_criticality(tied_ccp)
        selected = tied[rel_idx]
        method = "criticality"

    # 2c. Deterministic hash (last resort)
    else:
        # Use field data hash for deterministic but unbiased selection
        hash_val = hash(tuple(float(s) for s in scores)) ^ seed
        selected = tied[hash_val % len(tied)]
        method = "hash"

    # ── 3. CCP GATE ──────────────────────────────────────────────
    ccp_valid: bool | None = None
    if candidate_fields is not None and len(candidate_fields) > selected:
        ccp_valid = _ccp_gate(candidate_fields[selected])
        if not ccp_valid:
            # Selected state failed CCP — fall back to next tied candidate
            for alt in tied:
                if alt != selected and _ccp_gate(candidate_fields[alt]):
                    selected = alt
                    ccp_valid = True
                    break

    # ── 4. BUILD RATIONALE ───────────────────────────────────────
    spread = report.score_spread
    rationale_parts = [
        f"Indeterminacy detected: {len(tied)} candidates within {spread:.4f} of best.",
    ]
    if method == "perturbation":
        assert delta_F is not None
        rationale_parts.append(
            f"Thermodynamic symmetry breaking: ΔF[{selected}]={delta_F[selected]:.6f} "
            f"(max response → nearest criticality)."
        )
    elif method == "criticality":
        rationale_parts.append(
            f"CCP criticality proximity: candidate {selected} closest to "
            f"cognitive center (D_f≈{CCP_D_F_CENTER}, R≈{CCP_R_TARGET})."
        )
    else:
        rationale_parts.append(
            f"Deterministic hash fallback: selected candidate {selected}."
        )

    if ccp_valid is not None:
        rationale_parts.append(f"CCP gate: {'PASS' if ccp_valid else 'FAIL'}.")

    return ChoiceResult(
        selected_index=selected,
        indeterminacy=report,
        method=method,
        delta_F=delta_F,
        ccp_valid=ccp_valid,
        rationale=" ".join(rationale_parts),
    )
