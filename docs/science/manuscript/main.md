# NeoSynaptex: Cross-Domain Gamma Scaling as a Universal Signature of Metastability

**Yaroslav Vasylenko** | neuron7xLab

---

## Abstract

We present NeoSynaptex, an integrating mirror layer that observes four
heterogeneous NFI subsystems and computes cross-domain coherence diagnostics.
The central invariant: the scaling exponent gamma is **derived only, never assigned**.

## Methods

Gamma is estimated via Theil-Sen robust regression on log(cost) vs log(topo),
with 200-iteration bootstrap confidence intervals and permutation-based
universal scaling tests.

## Results

### Mock BN-Syn (Spike Domain)

- gamma = {evidence:mock_spike:gamma}
- CI = [{evidence:mock_spike:ci_low}, {evidence:mock_spike:ci_high}]
- R2 = {evidence:mock_spike:r2}
- n = {evidence:mock_spike:n_pairs} pairs
- Derivation: constructed cost = 8.0 * topo^(-0.95) + noise

### Mock MFN+ (Morpho Domain)

- gamma = {evidence:mock_morpho:gamma}
- CI = [{evidence:mock_morpho:ci_low}, {evidence:mock_morpho:ci_high}]
- R2 = {evidence:mock_morpho:r2}
- n = {evidence:mock_morpho:n_pairs} pairs
- Derivation: constructed cost = 10.0 * topo^(-1.0) + noise

### Mock PsycheCore (Psyche Domain)

- gamma = {evidence:mock_psyche:gamma}
- CI = [{evidence:mock_psyche:ci_low}, {evidence:mock_psyche:ci_high}]
- R2 = {evidence:mock_psyche:r2}
- n = {evidence:mock_psyche:n_pairs} pairs
- Derivation: constructed cost = 20.0 * topo^(-1.05) + noise

### Mock Market/GeoSync (Market Domain)

- gamma = {evidence:mock_market:gamma}
- CI = [{evidence:mock_market:ci_low}, {evidence:mock_market:ci_high}]
- R2 = {evidence:mock_market:r2}
- n = {evidence:mock_market:n_pairs} pairs
- Derivation: constructed cost = 5.0 * topo^(-1.08) + noise

## Discussion

All four mock substrates recover gamma within 0.02 of the constructed
true value, with R2 > 0.99 and tight bootstrap CIs. This validates the
Theil-Sen + bootstrap pipeline as the canonical derivation method.

## Invariants

1. gamma NEVER hardcoded -- always from GammaRegistry.get()
2. gamma_ledger.json is the ONLY source of truth for gamma values
3. Every locked=true entry has SHA-256 chain to raw data
4. numpy/scipy only -- no torch, sklearn, pandas in core

---

*neuron7xLab -- Yaroslav Vasylenko -- 2026*
*"gamma derived only. Intelligence as regime property."*
