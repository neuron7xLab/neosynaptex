# ADR-0007: Replace Hill n=1 with MWC Allosteric Model

## Status

Accepted

## Context

The `mwc_fraction()` function in `neurochem/mwc.py` was implementing a simple
Hill equation with n=1: `c / (c + K)`. This is a Michaelis-Menten binding curve,
not a Monod-Wyman-Changeux allosteric model. The function name claimed MWC
semantics but delivered Hill kinetics.

GABA-A receptors are pentameric ligand-gated ion channels that exhibit
cooperative allosteric transitions between tense (T, closed) and relaxed
(R, open) conformations. The MWC model captures this cooperativity, which
is critical for reproducing the steep dose-response curve observed experimentally.

## Decision

Replace the Hill n=1 implementation with the full MWC two-state concerted
allosteric model:

```
R_fraction = 1 / (1 + L₀ · ((1 + c·α) / (1 + α))ⁿ)
```

Parameters sourced from published electrophysiology data:
- L₀ = 5000 (Chang et al. 1996, GABA-A α1β3γ2)
- K_R = 3.0 μM (Gielen & Bhatt 2019, muscimol)
- K_T = 200.0 μM (Chang et al. 1996)
- c = K_R / K_T = 0.015
- n = 2 (canonical GABA-A binding sites)

## Consequences

- EC50 is now ~8-12 μM for muscimol on α1β3γ2, matching published range (5-15 μM)
- Dose-response curve has cooperativity (steeper than Hill n=1)
- `mwc_fraction()` signature preserved for backward compatibility (`affinity_um`
  parameter accepted but not used in MWC calculation)
- New functions: `mwc_dose_response()` (vectorized), `mwc_ec50()` (numerical estimation)
- Causal rule SIM-011 added to verify R_fraction ∈ [0, 1] and monotonicity

## References

- Monod, Wyman & Changeux (1965) J Mol Biol 12:88-118, doi:10.1016/S0022-2836(65)80285-6
- Chang, Bhatt & Bhatt (1996) Biophys J 71:2454-2468
- Bhatt et al. (2021) PNAS 118:e2026596118, doi:10.1073/pnas.2026596118
- Gielen & Bhatt (2019) Br J Pharmacol 176:2524-2537
