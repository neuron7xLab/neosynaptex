# ADR-0009: Observation Noise Model — Gaussian Temporal, Not BOLD

## Status
Accepted

## Context
The profile `observation_noise_gaussian_temporal` applies Gaussian noise with temporal smoothing. This is not a BOLD fMRI model — true BOLD requires hemodynamic response function (HRF) convolution per Buxton et al. (1998) Balloon model. The name oversells the capability.

## Decision
Keep the profile name for backward compatibility but:
1. Document in `KNOWN_LIMITATIONS.md` that it is Gaussian temporal smoothing, not HRF-based.
2. Plan true HRF convolution for v5.0 as a separate profile.
3. Do not rename the existing profile (it's a stable API surface).

## Consequences
- Honest documentation prevents false claims.
- Existing code and tests unchanged.
- v5.0 will add `observation_noise_hrf_bold` with actual hemodynamic response.

## References
- Buxton et al. (1998) MRM 39:855-864
