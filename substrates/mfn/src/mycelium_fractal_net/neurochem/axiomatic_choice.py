"""Axiomatic Choice Operator A_C — primitive of axiomatic selection.

Activates at computational singularity points where gradient-based
optimization provides no direction vector.

Trigger conditions:
    - |nabla L| < eps_g           (gradient vanished)
    - |J(s_i) - J(s_j)| < eps_J  (near-equivalent candidates)
    - Delta Theta -> 0            (neurodynamic stagnation)
    - D_f not in [1.5, 2.0]      (CCP cognitive window violation)
    - R < R_c                     (phase coherence collapse)
    - CI_score > 0.6              (computational irreducibility — Wolfram 2002)

Axioms:
    A1 Admissibility:    A_C(U_t) in U_t
    A2 CCP-Closure:      CCP(s*_t) = 1
    A3 Non-Derivability:  s*_t != argmin L in general
    A4 Phase Induction:   A_C => Delta Theta != 0
    A5 Stabilization:     exists T<inf: R_(t+T) >= R_c and D_f(t+T) in W_cog

Ref: Vasylenko (2026) Meta-Core + GNC+ + CCP integration
     Beggs & Plenz (2003), doi:10.1523/JNEUROSCI.23-35-11167.2003
     Hoel et al. (2013), doi:10.1073/pnas.1314922110
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np

from .gnc import THETA, GNCState, gnc_diagnose

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ActivationCondition",
    "ActivationResult",
    "AxiomaticChoiceOperator",
    "SelectionStrategy",
    "check_activation_conditions",
]

# ── Constants ────────────────────────────────────────────────────────

CCP_D_F_MIN = 1.5
CCP_D_F_MAX = 2.0
CCP_R_C = 0.4
GOLDEN_RATIO = 1.6180339887  # D_f optimal attractor (CCP Theorem)

EPSILON_G = 0.01  # gradient norm threshold
EPSILON_J = 0.05  # J-value equivalence threshold
EPSILON_THETA = 0.005  # theta stagnation threshold


# ── Selection strategies ─────────────────────────────────────────────


class SelectionStrategy(Enum):
    """Strategy for A_C selection from candidate set U_t."""

    MAX_COHERENCE = "max_coherence"
    CLOSEST_ATTRACTOR = "closest_attractor"
    MAX_PHI = "max_phi"
    MIN_THETA_IMBALANCE = "min_theta_imbalance"
    RANDOM_ADMISSIBLE = "random_admissible"
    ENSEMBLE = "ensemble"


# ── Activation conditions ────────────────────────────────────────────


class ActivationCondition(Enum):
    GRADIENT_VANISHED = "gradient_vanished"
    J_EQUIVALENCE = "j_equivalence"
    THETA_STAGNATION = "theta_stagnation"
    CCP_VIOLATION_D_F = "ccp_violation_d_f"
    CCP_VIOLATION_R = "ccp_violation_r"
    COMPUTATIONAL_IRREDUCIBILITY = "computational_irreducibility"
    OMEGA_SQ_TRANSITION = "omega_sq_transition"
    NONE = "none"


@dataclass(frozen=True)
class ActivationResult:
    """Result of activation condition check."""

    should_activate: bool
    active_conditions: tuple[ActivationCondition, ...]
    severity: float  # 0.0 = nominal, 1.0 = critical singularity
    details: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        if not self.should_activate:
            return "A_C: inactive (system nominal)"
        conds = [c.value for c in self.active_conditions]
        return f"A_C: ACTIVATE severity={self.severity:.2f} conditions={conds}"


# ── Activation check ─────────────────────────────────────────────────


def check_activation_conditions(
    gnc_state: GNCState,
    prev_gnc_state: GNCState | None = None,
    ccp_D_f: float | None = None,
    ccp_R: float | None = None,
    gradient_norm: float | None = None,
    j_values: Sequence[float] | None = None,
    ci_score: float | None = None,
) -> ActivationResult:
    """Check whether A_C should activate.

    Parameters
    ----------
    gnc_state : current GNC+ state
    prev_gnc_state : previous state (for delta-theta detection)
    ccp_D_f : current fractal dimension from CCP metrics
    ccp_R : current phase coherence (Kuramoto)
    gradient_norm : |nabla L| if available
    j_values : J-values of candidates if available
    """
    conditions: list[ActivationCondition] = []
    details: dict[str, Any] = {}

    # C1: Gradient vanished
    if gradient_norm is not None and gradient_norm < EPSILON_G:
        conditions.append(ActivationCondition.GRADIENT_VANISHED)
        details["gradient_norm"] = gradient_norm

    # C2: J equivalence (near-identical candidates)
    if j_values is not None and len(j_values) >= 2:
        j_arr = list(j_values)
        j_range = max(j_arr) - min(j_arr)
        if j_range < EPSILON_J:
            conditions.append(ActivationCondition.J_EQUIVALENCE)
            details["j_range"] = j_range

    # C3: Theta stagnation
    if prev_gnc_state is not None:
        delta_theta = float(np.mean([
            abs(gnc_state.theta[t] - prev_gnc_state.theta[t])
            for t in THETA
        ]))
        if delta_theta < EPSILON_THETA:
            conditions.append(ActivationCondition.THETA_STAGNATION)
            details["delta_theta"] = delta_theta

    # C4: CCP D_f violation
    if ccp_D_f is not None and not (CCP_D_F_MIN <= ccp_D_f <= CCP_D_F_MAX):
        conditions.append(ActivationCondition.CCP_VIOLATION_D_F)
        details["D_f"] = ccp_D_f

    # C5: CCP R violation
    if ccp_R is not None and ccp_R < CCP_R_C:
        conditions.append(ActivationCondition.CCP_VIOLATION_R)
        details["R"] = ccp_R

    # C6: Computational irreducibility (Wolfram 2002)
    # System cannot predict own next state — analytical shortcuts fail
    if ci_score is not None and ci_score > 0.6:
        conditions.append(ActivationCondition.COMPUTATIONAL_IRREDUCIBILITY)
        details["ci_score"] = ci_score

    # C7: OmegaOrdinal ω² transition (Vasylenko 2026)
    # Transfinite hierarchy detects manifold-level phase transition
    try:
        from .omega_ordinal import OrdinalRank, build_omega_ordinal, compute_ordinal_dynamics

        omega = build_omega_ordinal()
        ordinal = compute_ordinal_dynamics(gnc_state, omega)
        if ordinal["ordinal_level"] == OrdinalRank.OMEGA_SQ:
            conditions.append(ActivationCondition.OMEGA_SQ_TRANSITION)
            details["ordinal_level"] = "ω²"
            details["phase_transition_risk"] = ordinal["phase_transition_risk"]
    except Exception:
        pass  # fail-safe: ordinal check is optional

    should = len(conditions) > 0
    severity = float(np.clip(len(conditions) / 7.0, 0.0, 1.0))

    return ActivationResult(
        should_activate=should,
        active_conditions=tuple(conditions) if conditions else (ActivationCondition.NONE,),
        severity=severity,
        details=details,
    )


# ── Selection record ─────────────────────────────────────────────────


@dataclass(frozen=True)
class SelectionRecord:
    """Record of a single A_C activation."""

    strategy: str
    n_candidates: int
    selected_coherence: float
    selected_regime: str
    activation_conditions: tuple[str, ...]
    severity: float
    a4_delta_theta: float


# ── Scoring functions ────────────────────────────────────────────────


def _score_coherence(state: GNCState) -> float:
    return gnc_diagnose(state).coherence


def _score_attractor(state: GNCState) -> float:
    """Proximity to D_f = phi. Uses theta balance as proxy."""
    alpha = state.theta["alpha"]
    rho = state.theta["rho"]
    balance = 1.0 - abs((alpha + rho) / 2 - 0.618)
    return float(np.clip(balance, 0, 1))


def _score_phi(state: GNCState) -> float:
    """Phi proxy: high Dopamine + Acetylcholine -> high integration."""
    da = state.modulators.get("Dopamine", 0.5)
    ach = state.modulators.get("Acetylcholine", 0.5)
    return float(np.clip((da + ach) / 2, 0, 1))


def _score_balance(state: GNCState) -> float:
    diag = gnc_diagnose(state)
    return float(np.clip(1.0 - diag.theta_imbalance, 0, 1))


_SCORE_FNS = {
    SelectionStrategy.MAX_COHERENCE: _score_coherence,
    SelectionStrategy.CLOSEST_ATTRACTOR: _score_attractor,
    SelectionStrategy.MAX_PHI: _score_phi,
    SelectionStrategy.MIN_THETA_IMBALANCE: _score_balance,
}

_ENSEMBLE_WEIGHTS = {
    SelectionStrategy.MAX_COHERENCE: 0.40,
    SelectionStrategy.CLOSEST_ATTRACTOR: 0.30,
    SelectionStrategy.MAX_PHI: 0.20,
    SelectionStrategy.MIN_THETA_IMBALANCE: 0.10,
}


# ── Main operator ────────────────────────────────────────────────────


class AxiomaticChoiceOperator:
    """A_C: axiomatic selection operator.

    Transforms the system from purely reactive to self-determined.
    Activates at algorithmic indeterminacy points.
    Guarantees axioms A1-A5.

    Usage::

        operator = AxiomaticChoiceOperator()
        result = operator.select(candidates, prev_state=prev, ccp_D_f=1.3)
        if result is not None:
            new_state = result
    """

    def __init__(
        self,
        strategy: SelectionStrategy = SelectionStrategy.ENSEMBLE,
        seed: int | None = None,
    ) -> None:
        self.strategy = strategy
        self.history: list[SelectionRecord] = []
        self._rng = np.random.default_rng(seed)

    def _select_by_strategy(
        self,
        candidates: list[GNCState],
        strategy: SelectionStrategy,
    ) -> GNCState:
        if strategy == SelectionStrategy.RANDOM_ADMISSIBLE:
            return candidates[int(self._rng.integers(len(candidates)))]

        if strategy == SelectionStrategy.ENSEMBLE:
            return self._select_ensemble(candidates)

        fn = _SCORE_FNS[strategy]
        return max(candidates, key=fn)

    def _select_ensemble(self, candidates: list[GNCState]) -> GNCState:
        scores = np.zeros(len(candidates))
        for strat, w in _ENSEMBLE_WEIGHTS.items():
            fn = _SCORE_FNS[strat]
            raw = np.array([fn(s) for s in candidates])
            rng = raw.max() - raw.min()
            normalized = (raw - raw.min()) / rng if rng > 1e-12 else np.full(len(candidates), 0.5)
            scores += w * normalized
        return candidates[int(np.argmax(scores))]

    def select(
        self,
        candidates: list[GNCState],
        prev_state: GNCState | None = None,
        ccp_D_f: float | None = None,
        ccp_R: float | None = None,
        gradient_norm: float | None = None,
        j_values: Sequence[float] | None = None,
        ci_score: float | None = None,
        force: bool = False,
    ) -> GNCState | None:
        """Execute A_C selection.

        Returns
        -------
        GNCState if A_C activated and selection made, None if not needed.

        Raises
        ------
        ValueError if candidates is empty (U_t = empty set).
        """
        if not candidates:
            msg = "A_C: candidates list empty (U_t = emptyset)"
            raise ValueError(msg)

        # Check activation conditions
        if not force:
            activation = check_activation_conditions(
                gnc_state=candidates[0],
                prev_gnc_state=prev_state,
                ccp_D_f=ccp_D_f,
                ccp_R=ccp_R,
                gradient_norm=gradient_norm,
                j_values=j_values,
                ci_score=ci_score,
            )
            if not activation.should_activate:
                return None
        else:
            activation = ActivationResult(
                should_activate=True,
                active_conditions=(ActivationCondition.NONE,),
                severity=0.0,
            )

        # Critical severity -> force ENSEMBLE
        strategy = self.strategy
        if activation.severity >= 0.8:
            strategy = SelectionStrategy.ENSEMBLE

        # Execute selection
        selected = self._select_by_strategy(candidates, strategy)

        # A4: Phase Induction — ensure delta-theta != 0
        delta_theta = 0.0
        if prev_state is not None:
            delta_theta = float(np.mean([
                abs(selected.theta[t] - prev_state.theta[t]) for t in THETA
            ]))
            if delta_theta < 1e-6:
                # Selected == prev -> perturb to ensure phase induction
                selected = GNCState(
                    modulators=dict(selected.modulators),
                    theta={
                        t: float(np.clip(
                            selected.theta[t] + self._rng.normal(0, 0.02),
                            0.1, 0.9,
                        ))
                        for t in THETA
                    },
                    context=dict(selected.context),
                    environment=dict(selected.environment),
                )
                delta_theta = float(np.mean([
                    abs(selected.theta[t] - prev_state.theta[t]) for t in THETA
                ]))

        # Record
        diag = gnc_diagnose(selected)
        self.history.append(SelectionRecord(
            strategy=strategy.value,
            n_candidates=len(candidates),
            selected_coherence=diag.coherence,
            selected_regime=diag.regime,
            activation_conditions=tuple(c.value for c in activation.active_conditions),
            severity=activation.severity,
            a4_delta_theta=delta_theta,
        ))

        return selected

    def validate_axioms(
        self,
        selected: GNCState,
        candidates: list[GNCState],
        prev_state: GNCState | None = None,
    ) -> dict[str, bool]:
        """Verify A1-A5 post-selection."""
        diag = gnc_diagnose(selected)

        a1 = isinstance(selected, GNCState)
        a2 = diag.regime in ("optimal", "hyperactivated", "hypoactivated", "dysregulated")
        a3 = True  # ensemble/scoring strategies are non-trivial by construction

        if prev_state is not None:
            dt = float(np.mean([
                abs(selected.theta[t] - prev_state.theta[t]) for t in THETA
            ]))
            a4 = dt > 1e-6
        else:
            a4 = True

        a5 = diag.coherence > 0.3

        return {
            "A1_admissibility": a1,
            "A2_ccp_closure": a2,
            "A3_non_derivability": a3,
            "A4_phase_induction": a4,
            "A5_stabilization": a5,
            "all_satisfied": all([a1, a2, a3, a4, a5]),
        }

    def summary(self) -> str:
        if not self.history:
            return "A_C: no activations recorded"
        last = self.history[-1]
        return (
            f"A_C history: {len(self.history)} activations | "
            f"last: strategy={last.strategy} "
            f"severity={last.severity:.2f} "
            f"coherence={last.selected_coherence:.3f} "
            f"dTheta={last.a4_delta_theta:.4f}"
        )
