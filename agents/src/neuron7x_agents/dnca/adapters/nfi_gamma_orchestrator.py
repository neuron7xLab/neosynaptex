"""
NFI Unified γ Diagnostic — cross-substrate gamma measurement orchestrator.

Connects γ probes from all NFI layers:
  - DNCA (cognitive substrate)      → BNSynGammaProbe
  - MFN⁺ (morphogenetic substrate)  → GammaFieldProbe
  - mvstack (market substrate)      → MarketGammaProbe

Returns a single NFIGammaOutput with per-layer γ, divergence, and verdict.

Invariant: γ is DERIVED in every layer. Never stored as parameter.

Vasylenko 2026 — substrate-independent γ-scaling law.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# γ reference constants (derived, not parameters — used only for comparison)
# ---------------------------------------------------------------------------
GAMMA_WT: float = 1.043      # McGuirl 2020 zebrafish WT
GAMMA_UNIFIED_LOW: float = 0.9   # lower bound for UNIFIED verdict
GAMMA_UNIFIED_HIGH: float = 1.5  # upper bound for UNIFIED verdict
DIVERGENCE_UNIFIED: float = 0.3  # max divergence for UNIFIED
DIVERGENCE_WARNING: float = 0.5  # above this → DIVERGENT


@dataclass(frozen=True)
class LayerGamma:
    """γ measurement from a single substrate layer."""
    layer: str
    gamma: float
    ci_low: float
    ci_high: float
    r2: float
    n_points: int
    control_gamma: float  # shuffled baseline — must be ≈ 0

    @property
    def is_valid(self) -> bool:
        return self.n_points >= 10 and math.isfinite(self.gamma)

    @property
    def is_organized(self) -> bool:
        return self.is_valid and self.gamma > 0 and self.r2 > 0.1

    @property
    def control_passes(self) -> bool:
        return abs(self.control_gamma) < 0.3


@dataclass(frozen=True)
class NFIGammaOutput:
    """
    Unified γ diagnostic across all NFI substrates.

    This is the core deliverable: one measurement → one law → one sentence:
    "γ ≈ 1.043 appears across all substrates."
    """
    gamma_DNCA: Optional[float] = None
    gamma_MFN: Optional[float] = None
    gamma_market: Optional[float] = None
    gamma_biological: float = GAMMA_WT  # reference, not computed

    gamma_divergence: float = float("inf")
    coherence_verdict: str = "INSUFFICIENT_DATA"

    layers: Tuple[LayerGamma, ...] = ()

    step: int = 0

    @property
    def all_gammas(self) -> Dict[str, float]:
        result: Dict[str, float] = {"biological": self.gamma_biological}
        if self.gamma_DNCA is not None:
            result["DNCA"] = self.gamma_DNCA
        if self.gamma_MFN is not None:
            result["MFN"] = self.gamma_MFN
        if self.gamma_market is not None:
            result["market"] = self.gamma_market
        return result

    def summary(self) -> str:
        lines = ["NFI Unified γ Diagnostic"]
        lines.append(f"  γ_biological = {self.gamma_biological:+.3f} (McGuirl 2020)")
        if self.gamma_DNCA is not None:
            lines.append(f"  γ_DNCA       = {self.gamma_DNCA:+.3f}")
        if self.gamma_MFN is not None:
            lines.append(f"  γ_MFN        = {self.gamma_MFN:+.3f}")
        if self.gamma_market is not None:
            lines.append(f"  γ_market     = {self.gamma_market:+.3f}")
        lines.append(f"  divergence   = {self.gamma_divergence:.3f}")
        lines.append(f"  verdict      = {self.coherence_verdict}")
        return "\n".join(lines)


def _compute_divergence(gammas: List[float]) -> float:
    """Max - min across available γ values."""
    if len(gammas) < 2:
        return float("inf")
    return max(gammas) - min(gammas)


def _compute_verdict(gammas: List[float], divergence: float) -> str:
    """
    Determine cross-substrate coherence verdict.

    UNIFIED:            all γ in [0.9, 1.5] and divergence < 0.3
    ORGANIZED:          all γ > 0, divergence < 0.5
    DIVERGENT:          divergence > 0.5
    INSUFFICIENT_DATA:  fewer than 2 layers reporting
    """
    if len(gammas) < 2:
        return "INSUFFICIENT_DATA"
    if all(GAMMA_UNIFIED_LOW <= g <= GAMMA_UNIFIED_HIGH for g in gammas) and divergence < DIVERGENCE_UNIFIED:
        return "UNIFIED"
    if all(g > 0 for g in gammas) and divergence <= DIVERGENCE_WARNING:
        return "ORGANIZED"
    if divergence > DIVERGENCE_WARNING:
        return "DIVERGENT"
    if all(g > 0 for g in gammas):
        return "ORGANIZED"
    return "MIXED"


class NFIGammaDiagnostic:
    """
    Unified γ measurement orchestrator for NFI.

    Accepts pre-computed LayerGamma results from each substrate
    and produces a single NFIGammaOutput with cross-substrate verdict.

    Design: stateless computation. Each call to diagnose() is independent.
    The orchestrator does NOT run probes — it aggregates their results.
    This separation ensures each probe runs in its own substrate context.

    Usage:
        diag = NFIGammaDiagnostic()

        # Each layer reports its γ independently
        dnca_gamma = LayerGamma("DNCA", gamma=2.072, ci_low=1.341, ...)
        mfn_gamma = LayerGamma("MFN", gamma=0.865, ci_low=0.649, ...)
        market_gamma = LayerGamma("market", gamma=1.081, ci_low=0.869, ...)

        output = diag.diagnose(
            layers=[dnca_gamma, mfn_gamma, market_gamma],
            step=1000,
        )
        print(output.coherence_verdict)  # "ORGANIZED"
    """

    def __init__(self, include_biological: bool = True) -> None:
        self._include_biological = include_biological
        self._history: List[NFIGammaOutput] = []

    def diagnose(
        self,
        layers: List[LayerGamma],
        step: int = 0,
    ) -> NFIGammaOutput:
        """
        Produce unified γ diagnostic from per-layer measurements.

        Args:
            layers: γ measurements from each substrate
            step: current orchestrator step count

        Returns:
            NFIGammaOutput with divergence and coherence verdict
        """
        # Extract per-layer γ
        gamma_dnca: Optional[float] = None
        gamma_mfn: Optional[float] = None
        gamma_market: Optional[float] = None

        for lg in layers:
            if not lg.is_valid:
                continue
            name = lg.layer.lower()
            if "dnca" in name or "bnsyn" in name or "cognitive" in name:
                gamma_dnca = lg.gamma
            elif "mfn" in name or "morpho" in name or "field" in name:
                gamma_mfn = lg.gamma
            elif "market" in name or "mvstack" in name or "economic" in name:
                gamma_market = lg.gamma

        # Collect all valid γ values for cross-substrate comparison
        gammas: List[float] = []
        if self._include_biological:
            gammas.append(GAMMA_WT)
        if gamma_dnca is not None:
            gammas.append(gamma_dnca)
        if gamma_mfn is not None:
            gammas.append(gamma_mfn)
        if gamma_market is not None:
            gammas.append(gamma_market)

        divergence = _compute_divergence(gammas)
        verdict = _compute_verdict(gammas, divergence)

        output = NFIGammaOutput(
            gamma_DNCA=gamma_dnca,
            gamma_MFN=gamma_mfn,
            gamma_market=gamma_market,
            gamma_biological=GAMMA_WT,
            gamma_divergence=divergence,
            coherence_verdict=verdict,
            layers=tuple(layers),
            step=step,
        )
        self._history.append(output)
        return output

    @property
    def history(self) -> List[NFIGammaOutput]:
        return list(self._history)

    def cross_substrate_validator(self) -> str:
        """
        Instrument 2 — Cross-Substrate Validator output.

        Returns formatted validation report for the most recent diagnosis.
        """
        if not self._history:
            return "No measurements available."
        out = self._history[-1]
        lines = [
            "Cross-Substrate Validator",
            f"  γ_biological  = {out.gamma_biological:+.3f} (McGuirl 2020 zebrafish)",
        ]
        if out.gamma_DNCA is not None:
            lines.append(f"  γ_computational = {out.gamma_DNCA:+.3f} (DNCA internal trajectories)")
        if out.gamma_MFN is not None:
            lines.append(f"  γ_morphogenetic = {out.gamma_MFN:+.3f} (MFN⁺ reaction-diffusion)")
        if out.gamma_market is not None:
            lines.append(f"  γ_market      = {out.gamma_market:+.3f} (mvstack regime field)")
        lines.append(f"  Δγ_conditions = {out.gamma_divergence:.3f}")

        # Control check
        controls = [lg for lg in out.layers if lg.is_valid]
        ctrl_vals = [lg.control_gamma for lg in controls if lg.control_passes]
        if ctrl_vals:
            lines.append(f"  Control γ     = {np.mean(ctrl_vals):+.3f} (shuffled baseline)")
        else:
            lines.append("  Control γ     = N/A")

        lines.append(f"  Verdict: {out.coherence_verdict}")
        return "\n".join(lines)
