"""
MetastabilityEngine — active regulation of the global order parameter r(t).

INV-5: Metastability is a target, not a result.
The MetastabilityEngine actively regulates r(t).
The system does not passively "happen" to be metastable.
MetastabilityEngine has write access to coupling strength K.

Target operating regime:
  r_std > METASTABILITY_THRESHOLD (0.10)
  COLLAPSE_THRESHOLD < r_mean < RIGIDITY_THRESHOLD

Reference: Tognoli & Kelso 2014, Neuron 81:35-48
           Hancock et al. 2025, Nature Reviews Neuroscience
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from neuron7x_agents.dnca.competition.kuramoto import KuramotoCoupling
from neuron7x_agents.dnca.core.types import (
    COLLAPSE_THRESHOLD,
    COUPLING_DEFAULT,
    COUPLING_K_MAX,
    COUPLING_K_MIN,
    METASTABILITY_THRESHOLD,
    RIGIDITY_THRESHOLD,
)


@dataclass(slots=True)
class MetastabilityReport:
    """Diagnostic output of metastability check."""
    r_mean: float
    r_std: float
    coupling_K: float
    is_rigid: bool
    is_collapsed: bool
    is_healthy: bool
    action_taken: str


class MetastabilityEngine:
    """
    Active regulator of global coherence dynamics.

    Monitors r(t) and adjusts Kuramoto coupling K to maintain
    the system in the metastable regime.
    """

    CHECK_INTERVAL = 20  # steps between checks
    COUPLING_DECREASE_RATE = 0.05
    COUPLING_INCREASE_RATE = 0.03
    NOISE_BOOST = 0.03

    def __init__(self, kuramoto: KuramotoCoupling):
        self.kuramoto = kuramoto
        self._step_count = 0
        self._last_report: Optional[MetastabilityReport] = None

    def check(self) -> Optional[MetastabilityReport]:
        """
        Periodic check of metastability. Returns report if check was performed.
        """
        self._step_count += 1
        if self._step_count % self.CHECK_INTERVAL != 0:
            return None

        r_mean = self.kuramoto.r_mean
        r_std = self.kuramoto.r_std
        K = self.kuramoto.K

        is_rigid = r_std < METASTABILITY_THRESHOLD and r_mean > RIGIDITY_THRESHOLD
        is_collapsed = r_mean < COLLAPSE_THRESHOLD
        is_healthy = not is_rigid and not is_collapsed and r_std >= METASTABILITY_THRESHOLD

        action = "none"

        if is_rigid:
            # Too rigid: reduce coupling, inject noise
            new_K = K * (1.0 - self.COUPLING_DECREASE_RATE)
            self.kuramoto.set_coupling(new_K)
            action = f"reduce_K: {K:.3f} → {new_K:.3f}"
        elif is_collapsed:
            # Too incoherent: increase coupling
            new_K = K * (1.0 + self.COUPLING_INCREASE_RATE)
            self.kuramoto.set_coupling(new_K)
            action = f"increase_K: {K:.3f} → {new_K:.3f}"

        self._last_report = MetastabilityReport(
            r_mean=r_mean,
            r_std=r_std,
            coupling_K=self.kuramoto.K,
            is_rigid=is_rigid,
            is_collapsed=is_collapsed,
            is_healthy=is_healthy,
            action_taken=action,
        )
        return self._last_report

    @property
    def last_report(self) -> Optional[MetastabilityReport]:
        return self._last_report

    def reset(self) -> None:
        self._step_count = 0
        self._last_report = None
        self.kuramoto.set_coupling(COUPLING_DEFAULT)
