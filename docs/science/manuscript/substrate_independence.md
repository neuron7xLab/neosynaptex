# Cross-Substrate Independence Quantification

This note makes independence explicit instead of narrative-only claims.

## Matrix dimensions
- code independence
- data independence
- mechanism class independence

## Computed diagnostics
- pairwise \(|\gamma_i-\gamma_j|\)
- leave-one-substrate-out (LOO) mean-\(\gamma\) stability
- aggregate \(\bar\gamma\), std

Generated artifact:
- `figures/substrate_independence.json` (from `scripts/compute_substrate_independence.py`)

Interpretation rule:
- if LOO drift is small relative to CI scales, cross-substrate regularity is not driven by one substrate.
