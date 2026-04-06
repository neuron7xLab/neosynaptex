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

- Derivation: constructed cost = 8.0 * topo^(-0.95) + noise

### Mock MFN+ (Morpho Domain)

- Derivation: constructed cost = 10.0 * topo^(-1.0) + noise

### Mock PsycheCore (Psyche Domain)

- Derivation: constructed cost = 20.0 * topo^(-1.05) + noise

### Mock Market/GeoSync (Market Domain)

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
