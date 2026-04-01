"""OmegaOrdinal — transfinite hierarchy of neuromodulatory interactions.

Ordinary Omega: flat 7×7 matrix of pairwise weights.
OmegaOrdinal:   hierarchical structure where interactions carry ordinal rank.

Ranks:
  OMEGA_0 (ω)   — direct pairwise interactions, first order
  OMEGA_1 (ω+1) — mediative interactions through a third axis
  OMEGA_2 (ω+2) — global patterns and cost buffering
  OMEGA_SQ (ω²) — phase transition of the entire manifold

Rule: higher rank → stronger influence on phase transition.
A_C activates automatically when the system reaches ω² level.

Ref: Cantor (1883) transfinite ordinals
     Vasylenko (2026) GNC+ Omega dynamics
     Wolfram (2002) computational irreducibility as activation condition
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

import numpy as np

from .gnc import MODULATORS, GNCState, gnc_diagnose

__all__ = [
    "OmegaInteraction",
    "OmegaOrdinal",
    "OrdinalRank",
    "build_omega_ordinal",
    "compute_ordinal_dynamics",
]


class OrdinalRank(IntEnum):
    """Ordinal rank of a neuromodulatory interaction."""

    OMEGA_0 = 0   # ω   — direct pairwise
    OMEGA_1 = 1   # ω+1 — mediative
    OMEGA_2 = 2   # ω+2 — global
    OMEGA_SQ = 3  # ω²  — manifold phase transition

    def label(self) -> str:
        return ["ω", "ω+1", "ω+2", "ω²"][self.value]

    def weight_multiplier(self) -> float:
        """Higher rank → stronger influence."""
        return [1.0, 1.5, 2.0, 4.0][self.value]


@dataclass
class OmegaInteraction:
    """A single interaction between two axes with ordinal rank."""

    source: str
    target: str
    rank: OrdinalRank
    weight: float
    label: str = ""
    ref: str = ""

    @property
    def effective_weight(self) -> float:
        """Effective weight accounting for ordinal rank."""
        return self.weight * self.rank.weight_multiplier()


class OmegaOrdinal:
    """Transfinite hierarchical Omega matrix for GNC+.

    Replaces the flat Omega 7×7 with a structured hierarchy
    where each interaction carries an ordinal rank.

    Usage::

        omega = build_omega_ordinal()
        matrix = omega.to_matrix()
        level = omega.compute_interaction_level(state)
        if level >= OrdinalRank.OMEGA_SQ:
            # activate A_C
    """

    def __init__(self) -> None:
        self.interactions: list[OmegaInteraction] = []
        self._idx = {m: i for i, m in enumerate(MODULATORS)}

    def add(
        self,
        source: str,
        target: str,
        rank: OrdinalRank,
        weight: float,
        label: str = "",
        ref: str = "",
    ) -> None:
        self.interactions.append(
            OmegaInteraction(
                source=source,
                target=target,
                rank=rank,
                weight=weight,
                label=label,
                ref=ref,
            )
        )

    def to_matrix(self) -> np.ndarray:
        """Convert to standard 7×7 matrix with effective weights."""
        M = np.zeros((7, 7))
        for ix in self.interactions:
            i = self._idx[ix.source]
            j = self._idx[ix.target]
            M[i, j] = ix.effective_weight
        return M

    def get_by_rank(self, rank: OrdinalRank) -> list[OmegaInteraction]:
        return [ix for ix in self.interactions if ix.rank == rank]

    def compute_interaction_level(self, state: GNCState) -> OrdinalRank:
        """Determine the current ordinal level of the system.

        Logic:
        - ω²  : coherence < 0.3 and theta_imbalance > 0.2 (phase transition)
        - ω+2 : Opioid dominant or global cost buffering active
        - ω+1 : mediative interactions active (3+ axes deviated)
        - ω   : standard regime
        """
        diag = gnc_diagnose(state)
        levels = np.array([state.modulators[m] for m in MODULATORS])
        deviations = np.abs(levels - 0.5)
        n_deviated = int(np.sum(deviations > 0.2))

        # ω²: critical instability
        if diag.coherence < 0.3 and diag.theta_imbalance > 0.2:
            return OrdinalRank.OMEGA_SQ

        # ω+2: global cost buffering (Opioid dominant or 5+ axes deviated)
        opioid = state.modulators.get("Opioid", 0.5)
        if opioid > 0.7 or n_deviated >= 5:
            return OrdinalRank.OMEGA_2

        # ω+1: mediative (3-4 axes deviated)
        if n_deviated >= 3:
            return OrdinalRank.OMEGA_1

        # ω: base level
        return OrdinalRank.OMEGA_0

    def summary(self) -> str:
        lines = ["[OmegaOrdinal] Transfinite interaction hierarchy"]
        for rank in OrdinalRank:
            ixs = self.get_by_rank(rank)
            if ixs:
                lines.append(f"  {rank.label()} (×{rank.weight_multiplier()}):")
                for ix in ixs:
                    lines.append(
                        f"    {ix.source} → {ix.target}: {ix.weight:.2f} "
                        f"(eff={ix.effective_weight:.2f}) [{ix.label}]"
                    )
        return "\n".join(lines)


def build_omega_ordinal() -> OmegaOrdinal:
    """Build canonical OmegaOrdinal for GNC+.

    Based on existing GNC+ Omega matrix + ordinal hierarchy.
    """
    omega = OmegaOrdinal()

    # ω — direct pairwise interactions (first order)
    omega.add(
        "Glutamate", "GABA", OrdinalRank.OMEGA_0, -0.6,
        "excitation_inhibition_balance",
        "Dayan & Yu (2006) Neural Comput 18:1",
    )
    omega.add(
        "GABA", "Glutamate", OrdinalRank.OMEGA_0, -0.6,
        "inhibition_excitation_balance",
        "Dayan & Yu (2006)",
    )
    omega.add(
        "Dopamine", "Serotonin", OrdinalRank.OMEGA_0, -0.4,
        "reward_restraint_balance",
        "Schultz (1997) Science 275:1593",
    )
    omega.add(
        "Serotonin", "Dopamine", OrdinalRank.OMEGA_0, -0.4,
        "restraint_reward_balance",
        "Berridge & Kringelbach (2015) Neuron 86:646",
    )
    omega.add(
        "Noradrenaline", "Acetylcholine", OrdinalRank.OMEGA_0, 0.3,
        "salience_precision_balance",
        "Dayan & Yu (2006)",
    )
    omega.add(
        "Acetylcholine", "Noradrenaline", OrdinalRank.OMEGA_0, 0.3,
        "precision_salience_coupling",
        "Friston et al. (2012) Neural Comput 24:2201",
    )

    # ω+1 — mediative interactions through a third axis
    omega.add(
        "Glutamate", "Dopamine", OrdinalRank.OMEGA_1, 0.3,
        "plasticity_reward_coupling",
        "Schultz et al. (1997)",
    )
    omega.add(
        "Acetylcholine", "Glutamate", OrdinalRank.OMEGA_1, 0.2,
        "precision_plasticity_gate",
        "Friston et al. (2012)",
    )
    omega.add(
        "Serotonin", "Noradrenaline", OrdinalRank.OMEGA_1, -0.25,
        "restraint_salience_modulation",
        "Dayan & Yu (2006)",
    )
    omega.add(
        "Dopamine", "Acetylcholine", OrdinalRank.OMEGA_1, 0.2,
        "reward_precision_amplification",
        "Berridge (2015)",
    )

    # ω+2 — global patterns and cost buffering
    omega.add(
        "Opioid", "Glutamate", OrdinalRank.OMEGA_2, 0.2,
        "global_cost_buffering_plasticity",
        "Berridge & Kringelbach (2015)",
    )
    omega.add(
        "Opioid", "GABA", OrdinalRank.OMEGA_2, 0.2,
        "global_cost_buffering_stability",
        "Berridge (2015)",
    )
    omega.add(
        "Opioid", "Dopamine", OrdinalRank.OMEGA_2, 0.2,
        "resilience_reward_sustain",
        "Berridge (2015)",
    )
    omega.add(
        "Opioid", "Serotonin", OrdinalRank.OMEGA_2, 0.2,
        "resilience_restraint_buffer",
        "Berridge (2015)",
    )

    # ω² — manifold phase transitions (auto-activates A_C)
    omega.add(
        "Glutamate", "Noradrenaline", OrdinalRank.OMEGA_SQ, 0.4,
        "hyperexcitability_transition",
        "Staley (2015) Nat Neurosci 18:1437",
    )
    omega.add(
        "Dopamine", "Noradrenaline", OrdinalRank.OMEGA_SQ, 0.35,
        "reward_volatility_cascade",
        "Schultz (2016) Physiol Rev 96:1183",
    )

    return omega


def compute_ordinal_dynamics(
    state: GNCState,
    omega: OmegaOrdinal | None = None,
) -> dict[str, Any]:
    """Compute dynamics through OmegaOrdinal.

    Returns
    -------
    dict with keys:
        ordinal_level: OrdinalRank
        ordinal_label: str
        effective_matrix: np.ndarray (7×7)
        ac_required: bool (True if ω²)
        active_interactions: list of (source, target, rank_label) tuples
        phase_transition_risk: float in [0, 1]
        omega_effect_norm: float
    """
    if omega is None:
        omega = build_omega_ordinal()

    level = omega.compute_interaction_level(state)
    matrix = omega.to_matrix()

    levels_arr = np.array([state.modulators[m] for m in MODULATORS])
    omega_effect = float(np.linalg.norm(matrix @ levels_arr))

    active = [
        ix
        for ix in omega.interactions
        if abs(state.modulators.get(ix.source, 0.5) - 0.5) > 0.15
    ]

    phase_risk = float(
        np.clip(
            len([ix for ix in omega.interactions if ix.rank == OrdinalRank.OMEGA_SQ])
            * 0.3
            + (level.value / 3.0) * 0.7,
            0,
            1,
        )
    )

    return {
        "ordinal_level": level,
        "ordinal_label": level.label(),
        "effective_matrix": matrix,
        "ac_required": level == OrdinalRank.OMEGA_SQ,
        "active_interactions": [
            (ix.source, ix.target, ix.rank.label()) for ix in active
        ],
        "phase_transition_risk": phase_risk,
        "omega_effect_norm": omega_effect,
    }
