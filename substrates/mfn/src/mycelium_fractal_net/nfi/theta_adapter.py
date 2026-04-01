"""ThetaToSpecAdapter — deterministic mapping from GNC theta to SimulationSpec.

# DISCOVERY-B ANSWER (Q-B1):
#   Which SimulationSpec fields can be modulated via theta without CFL violation?
#
#   | theta param | sim field          | mapping                         | CFL safe? |
#   |-------------|--------------------|---------------------------------|-----------|
#   | alpha       | spec.alpha         | clip(theta*0.25, 0.05, 0.24)   | YES       |
#   | tau         | spike_probability  | clip(theta*0.5, 0.05, 0.5)     | YES (tau is inhibitory threshold, inverse of excitability) |
#   | beta        | turing_threshold   | clip(theta, 0.3, 0.95)         | YES       |
#
#   Constraints:
#     alpha ∈ (0.0, 0.25]  — CFL numerical stability (hard bound)
#     spike_probability ∈ [0.0, 1.0]
#     turing_threshold ∈ [0.0, 1.0]
#     theta values ∈ [0.1, 0.9] (post-GNC clipping)
#
# APPROXIMATION: linear scaling theta→spec is a first approximation.
# Real mapping requires calibration on biological data.
# TODO(nfi-v2): replace linear adapter with calibrated nonlinear mapping.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mycelium_fractal_net.types.field import SimulationSpec

__all__ = ["ThetaMapping"]


@dataclass(frozen=True)
class ThetaMapping:
    """Deterministic, reproducible mapping: theta dict → SimulationSpec fields.

    Three mapped parameters:
        theta['alpha'] → spec.alpha       (learning rate → diffusion coefficient)
        theta['tau']   → spike_probability (inhibitory threshold → excitability)
        theta['beta']  → turing_threshold  (policy stability → pattern threshold)

    All other spec fields are inherited from base_spec unchanged.
    """

    # Mapping bounds — CFL-safe ranges
    alpha_min: float = 0.05
    alpha_max: float = 0.24
    spike_min: float = 0.05
    spike_max: float = 0.50
    turing_min: float = 0.30
    turing_max: float = 0.95

    def apply(self, theta: dict[str, float], base_spec: SimulationSpec) -> SimulationSpec:
        """Return new SimulationSpec with theta-modulated fields. base_spec is unchanged.

        # APPROXIMATION: linear scaling from theta ∈ [0.1, 0.9] to sim bounds.
        """
        alpha_sim = float(np.clip(
            theta.get("alpha", 0.5) * (self.alpha_max / 0.9),
            self.alpha_min,
            self.alpha_max,
        ))
        spike_prob = float(np.clip(
            theta.get("tau", 0.5) * (self.spike_max / 0.9),
            self.spike_min,
            self.spike_max,
        ))
        turing_thr = float(np.clip(
            theta.get("beta", 0.5),
            self.turing_min,
            self.turing_max,
        ))

        return SimulationSpec(
            grid_size=base_spec.grid_size,
            steps=base_spec.steps,
            alpha=alpha_sim,
            spike_probability=spike_prob,
            turing_enabled=base_spec.turing_enabled,
            turing_threshold=turing_thr,
            quantum_jitter=base_spec.quantum_jitter,
            jitter_var=base_spec.jitter_var,
            seed=base_spec.seed,
            neuromodulation=base_spec.neuromodulation,
        )

    def inverse(self, spec: SimulationSpec) -> dict[str, float]:
        """Diagnostic: recover approximate theta from SimulationSpec.

        Only recovers mapped fields (alpha, tau, beta).
        Other theta params returned as 0.5 (neutral).
        """
        theta_alpha = float(np.clip(
            spec.alpha / (self.alpha_max / 0.9),
            0.1,
            0.9,
        ))
        theta_tau = float(np.clip(
            spec.spike_probability / (self.spike_max / 0.9),
            0.1,
            0.9,
        ))
        theta_beta = float(np.clip(
            spec.turing_threshold,
            0.1,
            0.9,
        ))

        return {
            "alpha": round(theta_alpha, 4),
            "rho": 0.5,
            "beta": round(theta_beta, 4),
            "tau": round(theta_tau, 4),
            "nu": 0.5,
            "sigma_E": 0.5,
            "sigma_U": 0.5,
            "lambda_pe": 0.5,
            "eta": 0.5,
        }
