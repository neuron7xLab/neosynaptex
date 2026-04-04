"""
Internal state value function for NFI (Neuromodulatory Field Intelligence).

Architecture: four convergent signals (following Doya 2002 + Dabney 2020 + Friston):
  V_gamma:   topological metastability signal (DA-like: peak at gamma=1.0)
  V_sr:      spectral radius stability (5HT-like: temporal horizon maintainer)
  V_cc:      cross-coherence signal (ACh-like: learning rate proxy)
  V_valence: rate-of-change of free energy (NE-like: direction detector)

Multi-timescale: N parallel gamma heads spanning [0.9, 0.999] log-uniform.
Homeostatic reward: r_homeo = -||H_t - H_star|| (deviation from optimal).

Pre-verified math:
  8 gamma heads: [0.9, 0.914, 0.927, 0.941, 0.955, 0.970, 0.984, 0.999]
  Temporal horizons: [10, 11.6, 13.7, 17, 22.4, 33, 63.4, 1000] timesteps
  sigma=0.98 -> gamma_equivalent=0.98 -> tau=50 (connects to BN-Syn criticality)

References:
  Sutskever (2025) Dwarkesh interview Nov 25
  Damasio & Carvalho (2013) Nat Rev Neurosci 14:143-152
  Schultz, Dayan & Montague (1997) Science 275:1593-1599
  Dabney et al. (2020) Nature 577:671-675
  Friston (2010) Nat Rev Neurosci 11:127-138
  Doya (2002) Neural Networks 15:495-506
  Joffily & Coricelli (2013) PLoS Comput Biol 9:e1003094
  Masset et al. (2025) Nature
  Priesemann et al. (2014) PLoS Comput Biol 10:e1003408
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from core.enums import ValueGate

logger = logging.getLogger(__name__)

# Thresholds (Sutskever: keep VF simple — complexity hurts generalization)
VIABILITY_THRESHOLD = 0.6  # V >= 0.6 → proceed
CRITICAL_THRESHOLD = 0.3  # V >= 0.3 → caution; V < 0.3 → redirect

# Gamma heads: log-uniform [0.9, 0.999], N=8
# Mirrors striatal gradient (Mohebi 2024): ventrolateral 0.95 → ventromedial 0.9999
N_GAMMA_HEADS = 8
GAMMA_HEADS: np.ndarray = np.exp(np.linspace(np.log(0.9), np.log(0.999), N_GAMMA_HEADS))
# Temporal horizons tau_i = 1/(1-gamma_i): [10, 11.6, 13.7, 17, 22, 33, 63, 1000]

# Neuromodulatory weights (Doya 2002 mapping)
# DA-proxy (gamma coherence): 0.5
# 5HT-proxy (spectral stability): 0.25
# ACh-proxy (cross-coherence): 0.15
# NE-proxy (valence/direction): 0.10
NEURO_WEIGHTS = (0.50, 0.25, 0.15, 0.10)


@dataclass(frozen=True)
class DistributionalEstimate:
    """
    Distributional value estimate across N gamma heads.
    Mirrors Dabney et al. (2020): population encodes reward distribution shape.
    """

    gamma_heads: tuple[float, ...]
    value_heads: tuple[float, ...]  # V_i for each gamma_i
    quantile_low: float  # pessimistic neurons (alpha_plus < alpha_minus)
    quantile_mid: float  # median estimate
    quantile_high: float  # optimistic neurons (alpha_plus > alpha_minus)
    temporal_horizons: tuple[float, ...]  # tau_i = 1/(1-gamma_i)


@dataclass(frozen=True)
class ValueEstimate:
    """
    Immutable internal state quality estimate.
    Derived only — never assigned. V in [0, 1].

    Signals:
      value:      composite V(s) in [0,1]
      valence:    -dF/dt in [-1, 1] (Joffily & Coricelli 2013)
      confidence: n_valid_domains / n_total_domains
      gate:       'proceed' | 'caution' | 'redirect'
      distributional: multi-timescale breakdown (Dabney 2020 inspired)
      homeostatic_deviation: ||H_t - H*|| distance from optimal
    """

    value: float
    valence: float
    confidence: float
    gate: str
    reason: str
    homeostatic_deviation: float
    distributional: DistributionalEstimate | None
    timestamp: float


# ─── Component value functions (Sutskever: keep simple) ─────────────────────


def _v_gamma(gamma_mean: float) -> float:
    """
    DA-proxy signal. Peak at gamma=1.0.
    V = max(0, 1 - (gamma-1)^2 / 0.25)
    Zero at gamma=0.5 and gamma=1.5.
    """
    if not np.isfinite(gamma_mean):
        return 0.0
    return float(max(0.0, 1.0 - (gamma_mean - 1.0) ** 2 / 0.25))


def _v_sr(sr: float) -> float:
    """
    5HT-proxy signal. Metastable band sr in [0.85, 1.15].
    V = max(0, 1 - |sr-1| / 0.15)  if in band, else 0.
    Implements temporal horizon regulation (Doya: 5HT = gamma parameter).
    """
    if not np.isfinite(sr):
        return 0.0
    if 0.85 <= sr <= 1.15:
        return float(max(0.0, 1.0 - abs(sr - 1.0) / 0.15))
    return 0.0


def _v_cc(cc: float) -> float:
    """
    ACh-proxy signal. Cross-coherence in [0, 1].
    Implements learning rate modulation (Doya: ACh = alpha parameter).
    """
    if not np.isfinite(cc):
        return 0.0
    return float(np.clip(cc, 0.0, 1.0))


def _v_valence(f_history: Sequence[float]) -> float:
    """
    NE-proxy signal. Valence = -dF/dt (Joffily & Coricelli 2013).
    Positive = system improving (F decreasing).
    Negative = system worsening (F increasing).
    Returns normalized in [-1, 1].
    Requires at least 2 F values; returns 0.0 if insufficient history.
    """
    if len(f_history) < 2:
        return 0.0
    # Use last two values for stability
    dF_dt = float(f_history[-1]) - float(f_history[-2])
    valence = -dF_dt
    return float(np.clip(valence / (abs(valence) + 1e-6), -1.0, 1.0))


def _homeostatic_deviation(
    gamma_mean: float,
    sr: float,
    cc: float,
) -> float:
    """
    Homeostatic reward signal: r_homeo = -||H_t - H*||
    Optimal setpoint H* = (gamma=1.0, sr=1.0, cc=1.0).
    Returns deviation distance (lower = better).
    """
    H_t = np.array(
        [
            gamma_mean if np.isfinite(gamma_mean) else 0.0,
            sr if np.isfinite(sr) else 0.0,
            cc if np.isfinite(cc) else 0.0,
        ]
    )
    H_star = np.array([1.0, 1.0, 1.0])
    return float(np.linalg.norm(H_t - H_star))


def _distributional_estimate(gamma_mean: float) -> DistributionalEstimate:
    """
    Multi-timescale distributional value estimate.
    N=8 gamma heads log-uniform [0.9, 0.999].
    Each head i computes V_i = V_gamma(gamma_mean) adjusted for timescale.
    Asymmetric optimism: short-horizon heads more pessimistic, long-horizon optimistic.
    (Mirrors Dabney 2020: alpha+/alpha- ratio = optimism level)
    """
    value_heads = []
    for i, g in enumerate(GAMMA_HEADS):
        # Optimism increases with gamma (longer timescale = more optimistic)
        optimism_bias = (i / (N_GAMMA_HEADS - 1)) * 0.1  # 0 to 0.1
        v_i = float(np.clip(_v_gamma(gamma_mean) + optimism_bias, 0.0, 1.0))
        value_heads.append(v_i)

    values = np.array(value_heads)
    tau_heads = tuple(float(1.0 / (1.0 - g)) for g in GAMMA_HEADS)

    return DistributionalEstimate(
        gamma_heads=tuple(float(g) for g in GAMMA_HEADS),
        value_heads=tuple(value_heads),
        quantile_low=float(np.percentile(values, 10)),
        quantile_mid=float(np.percentile(values, 50)),
        quantile_high=float(np.percentile(values, 90)),
        temporal_horizons=tau_heads,
    )


# ─── Main value function ────────────────────────────────────────────────────


def estimate_value(
    gamma_mean: float,
    spectral_radius: float,
    cross_coherence: float,
    n_valid_domains: int,
    n_total_domains: int,
    f_history: Sequence[float] = (),
    weights: tuple[float, float, float, float] = NEURO_WEIGHTS,
) -> ValueEstimate:
    """
    Composite internal value estimate. Four-signal architecture (Doya 2002).

    Formula:
        V(s) = w_DA   * V_gamma(gamma_mean)
             + w_5HT  * V_sr(spectral_radius)
             + w_ACh  * V_cc(cross_coherence)
             + w_NE   * max(0, valence(f_history))  -- direction bonus only

    Valence is computed separately and reported (can be negative).
    Only positive valence contributes to V (NE bonus for improving trajectories).

    Gate:
        V >= 0.6 -> proceed
        V >= 0.3 -> caution
        V <  0.3 -> redirect

    Sutskever principle: keep VF simple.
    Complexity-robustness tradeoff: 4 signals generalize better than 40.
    """
    w_da, w_5ht, w_ach, w_ne = weights

    v_da = _v_gamma(gamma_mean)
    v_5ht = _v_sr(spectral_radius)
    v_ach = _v_cc(cross_coherence)
    valence = _v_valence(f_history)
    v_ne = max(0.0, valence)  # only reward improving trajectories

    value = float(np.clip(w_da * v_da + w_5ht * v_5ht + w_ach * v_ach + w_ne * v_ne, 0.0, 1.0))

    confidence = float(n_valid_domains / max(n_total_domains, 1))
    h_dev = _homeostatic_deviation(gamma_mean, spectral_radius, cross_coherence)
    dist = _distributional_estimate(gamma_mean)

    # Gate (enum-backed, str-compatible)
    if value >= VIABILITY_THRESHOLD:
        gate = ValueGate.PROCEED
        reason = (
            f"V={value:.3f} >= {VIABILITY_THRESHOLD}. "
            f"gamma={gamma_mean:.3f} sr={spectral_radius:.3f} "
            f"cc={cross_coherence:.3f} valence={valence:+.3f} "
            f"homeo_dev={h_dev:.3f}"
        )
    elif value >= CRITICAL_THRESHOLD:
        gate = ValueGate.CAUTION
        reason = (
            f"V={value:.3f} in caution zone [{CRITICAL_THRESHOLD},{VIABILITY_THRESHOLD}). "
            f"gamma={gamma_mean:.3f} sr={spectral_radius:.3f} "
            f"valence={valence:+.3f} homeo_dev={h_dev:.3f}"
        )
    else:
        gate = ValueGate.REDIRECT
        reason = (
            f"V={value:.3f} < {CRITICAL_THRESHOLD}. "
            f"Trajectory toward incoherence. "
            f"gamma={gamma_mean:.3f} sr={spectral_radius:.3f} "
            f"valence={valence:+.3f} homeo_dev={h_dev:.3f}. "
            f"Redirect required (Sutskever: short-circuit before catastrophic failure)."
        )

    if gate == ValueGate.REDIRECT:
        logger.warning("ValueFunction REDIRECT: %s", reason)
    elif gate == ValueGate.CAUTION:
        logger.info("ValueFunction CAUTION: %s", reason)

    return ValueEstimate(
        value=value,
        valence=valence,
        confidence=confidence,
        gate=gate,
        reason=reason,
        homeostatic_deviation=h_dev,
        distributional=dist,
        timestamp=time.monotonic(),
    )


def estimate_value_from_state(
    state: Any,
    f_history: Sequence[float] = (),
) -> ValueEstimate | None:
    """
    Convenience wrapper: extract from NeosynaptexState and call estimate_value.
    Returns None for INITIALIZING phase or insufficient data.

    f_history: recent free-energy values for valence computation.
    Pass last N values of cross_coherence or external F proxy.
    """
    if state.phase == "INITIALIZING":
        return None

    gamma_mean = getattr(state, "gamma_mean", float("nan"))
    sr = getattr(state, "spectral_radius", float("nan"))
    cc = getattr(state, "cross_coherence", float("nan"))
    domains = getattr(state, "gamma_per_domain", {})

    n_valid = sum(1 for g in domains.values() if np.isfinite(g))
    n_total = len(domains)

    if n_valid == 0 or not np.isfinite(gamma_mean):
        return None

    return estimate_value(
        gamma_mean=gamma_mean,
        spectral_radius=sr if np.isfinite(sr) else 1.0,
        cross_coherence=cc if np.isfinite(cc) else 0.0,
        n_valid_domains=n_valid,
        n_total_domains=max(n_total, 1),
        f_history=f_history,
    )
