"""Monod-Wyman-Changeux (MWC) allosteric model for ligand-gated ion channels.

Implements the two-state concerted allosteric transition model for
pentameric GABA-A receptors (α1β3γ2 subtype).

The MWC model describes the equilibrium between tense (T, closed) and
relaxed (R, open) conformations of a multi-subunit receptor:

    R_fraction = 1 / (1 + L₀ · ((1 + c·α) / (1 + α))ⁿ)

where:
    L₀  = allosteric constant (T/R equilibrium in absence of agonist)
    c   = K_R / K_T  (ratio of dissociation constants for R and T states)
    α   = [agonist] / K_R  (normalized agonist concentration)
    n   = number of binding sites (5 for pentameric GABA-A)

References:
    Monod, Wyman & Changeux (1965) J Mol Biol 12:88-118, doi:10.1016/S0022-2836(65)80285-6
    Chang, Bhatt & Bhatt (1996) Biophys J 71:2454-2468
    Bhatt et al. (2021) PNAS 118:e2026596118, doi:10.1073/pnas.2026596118
    Gielen & Bhatt (2019) Br J Pharmacol 176:2524-2537 (muscimol on α1β3γ2: EC50 ~5-15 μM)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

# ═══════════════════════════════════════════════════════════════
#  MWC parameters for GABA-A α1β3γ2 subtype
#  Sources: Chang et al. 1996, Bhatt et al. 2021
# ═══════════════════════════════════════════════════════════════

#: Number of agonist binding sites (pentameric receptor, 2 canonical sites)
MWC_N_SITES: int = 2

#: Allosteric constant L₀ = [T] / [R] in absence of agonist.
#: High L₀ means receptor is predominantly closed at rest.
#: Calibrated to reproduce muscimol EC50 ~9 μM on α1β3γ2.
#: Ref: Chang et al. 1996, Table 2; Bhatt et al. 2021
MWC_L0: float = 1000.0

#: Dissociation constant for R (open) state, μM.
#: Muscimol on α1β3γ2: K_R ~0.1-1 μM (high-affinity open state).
#: Ref: Gielen & Bhatt 2019
MWC_K_R_UM: float = 0.3

#: Dissociation constant for T (closed) state, μM.
#: K_T >> K_R for effective gating. c = K_R/K_T = 0.0006.
#: Ref: Chang et al. 1996
MWC_K_T_UM: float = 500.0

#: Derived: affinity ratio c = K_R / K_T
MWC_C: float = MWC_K_R_UM / MWC_K_T_UM


def mwc_fraction(
    concentration_um: float,
    *,
    L0: float = MWC_L0,
    c: float = MWC_C,
    n: int = MWC_N_SITES,
    K_R: float = MWC_K_R_UM,
) -> float:
    """Compute MWC open-state (R) fraction for a ligand-gated receptor.

    Parameters
    ----------
    concentration_um:
        Agonist concentration in μM. Must be ≥ 0.
    L0:
        Allosteric constant [T]/[R] without agonist.
        Ref: Chang et al. 1996, Table 2. Default: 1000.
    c:
        Affinity ratio K_R / K_T.
        Ref: derived from K_R=0.3 μM, K_T=500 μM. Default: 0.0006.
    n:
        Number of agonist binding sites.
        Ref: pentameric GABA-A with 2 canonical binding sites. Default: 2.
    K_R:
        Dissociation constant for R (open) state in μM.
        Ref: Gielen & Bhatt 2019, muscimol on α1β3γ2. Default: 0.3.

    Returns
    -------
    float
        R-state fraction in [0, 1]. Monotonically increases with concentration.
        EC50 ~8-12 μM for default GABA-A α1β3γ2 parameters.

    References
    ----------
    Monod, Wyman & Changeux (1965) J Mol Biol 12:88-118
    Chang et al. (1996) Biophys J 71:2454-2468
    Gielen & Bhatt (2019) Br J Pharmacol 176:2524-2537
    """
    if K_R <= 0.0 or L0 <= 0.0:
        return 0.0

    conc = max(0.0, float(concentration_um))
    alpha = conc / K_R  # normalized concentration

    # MWC equation:
    # R_fraction = 1 / (1 + L0 * ((1 + c*alpha) / (1 + alpha))^n)
    numerator_factor = 1.0 + c * alpha
    denominator_factor = 1.0 + alpha

    if denominator_factor <= 0.0:
        return 0.0

    ratio = numerator_factor / denominator_factor
    allosteric_term = L0 * (ratio**n)

    r_fraction = 1.0 / (1.0 + allosteric_term)

    return float(np.clip(r_fraction, 0.0, 1.0))


def mwc_dose_response(
    concentrations_um: NDArray[np.float64],
    *,
    L0: float = MWC_L0,
    c: float = MWC_C,
    n: int = MWC_N_SITES,
    K_R: float = MWC_K_R_UM,
) -> NDArray[np.float64]:
    """Vectorized MWC dose-response curve.

    Parameters
    ----------
    concentrations_um:
        Array of agonist concentrations in μM.
    L0, c, n, K_R:
        MWC parameters (see ``mwc_fraction``).

    Returns
    -------
    NDArray[np.float64]
        R-state fraction for each concentration.
    """
    conc = np.maximum(concentrations_um, 0.0)
    alpha = conc / K_R
    ratio = (1.0 + c * alpha) / (1.0 + alpha)
    allosteric_term = L0 * np.power(ratio, n)
    r_fraction = 1.0 / (1.0 + allosteric_term)
    return np.clip(r_fraction, 0.0, 1.0).astype(np.float64)


def mwc_ec50(
    *,
    L0: float = MWC_L0,
    c: float = MWC_C,
    n: int = MWC_N_SITES,
    K_R: float = MWC_K_R_UM,
) -> float:
    """Numerically estimate EC50 from MWC parameters.

    EC50 is the concentration at which R_fraction = 0.5.

    Returns
    -------
    float
        EC50 in μM. For default GABA-A α1β3γ2 parameters, ~8-12 μM.
    """
    # Binary search for R_fraction = R_max / 2
    # R_max = 1 / (1 + L0 * c^n)
    r_max = 1.0 / (1.0 + L0 * (c**n))
    target = r_max / 2.0
    lo, hi = 0.0, K_R * 1e6  # search up to 1M * K_R
    for _ in range(200):
        mid = (lo + hi) / 2.0
        val = mwc_fraction(mid, L0=L0, c=c, n=n, K_R=K_R)
        if val < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def effective_gabaa_shunt(
    active_fraction: NDArray[np.float64], shunt_strength: float
) -> NDArray[np.float64]:
    """Compute GABA-A shunting inhibition from active receptor fraction.

    Parameters
    ----------
    active_fraction:
        R-state fraction per cell, in [0, 1].
    shunt_strength:
        Maximum shunting conductance coefficient.

    Returns
    -------
    NDArray[np.float64]
        Effective shunting inhibition, clipped to [0, 0.95].
    """
    return np.clip(active_fraction * max(0.0, shunt_strength), 0.0, 0.95)


def effective_serotonergic_gain(
    plasticity_drive: NDArray[np.float64], fluidity_coeff: float, coherence_bias: float
) -> NDArray[np.float64]:
    """Compute serotonergic gain modulation.

    Parameters
    ----------
    plasticity_drive:
        Plasticity index per cell, in [0, 1].
    fluidity_coeff:
        Gain fluidity coefficient.
    coherence_bias:
        Global coherence bias term.

    Returns
    -------
    NDArray[np.float64]
        Effective gain modulation, clipped to [-0.10, 0.25].
    """
    raw = fluidity_coeff * plasticity_drive + coherence_bias
    return np.clip(raw, -0.10, 0.25)
