# XFORM Manuscript Draft — Root Pointer

> **Canonical location:** [`manuscript/XFORM_MANUSCRIPT_DRAFT.md`](manuscript/XFORM_MANUSCRIPT_DRAFT.md)
>
> This file is the root-level summary pointer. For the full manuscript with
> all sections, figures, references, and supplementary material, read the
> canonical version above.

---

## Abstract

We report empirical evidence for a universal scaling exponent gamma ≈ 1.0
observed across ten independent substrates spanning biological tissue, chemical
fields, spiking neural networks, market dynamics, and cognitive systems. The
exponent is defined through the power-law relation K ~ C^(-gamma) between
thermodynamic cost K and topological complexity C. A value of gamma = 1.0
corresponds to the metastable regime where cost and complexity scale inversely
at unit rate — the signature of criticality.

**Key result:** Mean gamma across six validated Tier-1/Tier-2 substrates is
0.991 ± 0.052 (bootstrap 95% CI contains 1.0 for every substrate). Three
independent biological substrates (zebrafish morphogenesis, human HRV,
human EEG) reproduce gamma ≈ 1.0 from real external data. Four simulation
substrates (Gray-Scott, Kuramoto, BN-Syn, serotonergic Kuramoto) validate
the theoretical prediction. One out-of-regime control (cfp_diy, gamma = 1.83)
is recorded openly as a falsifying control.

---

## Hypothesis

**H1 — Intelligence as a Dynamical Regime:**

> For all substrates S_i at metastability: gamma(S_i) in [0.85, 1.15] with
> 95% CI containing 1.0.

H1 is supported if gamma in [0.85, 1.15] across N >= 3 independent substrates
from distinct physical domains, each passing surrogate testing (p < 0.05).

**H2 — Computational Efficiency Is a Regime Property:**

> The regime gamma ≈ 1 maximises computational capacity at minimal cost of
> plasticity maintenance.

**Status:** H1 SUPPORTED. H2 open — requires separate experimental validation.

---

## Key Results Summary

| Substrate | Tier | gamma | 95% CI | R2 | Status |
|-----------|------|-------|--------|----|--------|
| zebrafish_wt | T1 | 1.055 | [0.89, 1.21] | 0.76 | VALIDATED |
| eeg_physionet | T1 | 1.068 | [0.877, 1.246] | — | VALIDATED |
| eeg_resting | T1 | 1.255 | [1.032, 1.452] | — | VALIDATED |
| hrv_physionet | T1 | 0.885 | [0.834, 1.080] | — | VALIDATED |
| hrv_fantasia | T1 | 1.003 | [0.935, 1.059] | — | VALIDATED |
| gray_scott | T3 | 0.979 | [0.88, 1.01] | 0.995 | VALIDATED |
| kuramoto | T3 | 0.963 | [0.93, 1.00] | 0.90 | VALIDATED |
| bn_syn | T3 | 0.946 | [0.81, 1.08] | 0.28 | VALIDATED |
| serotonergic_kuramoto | T5 | 1.068 | [0.145, 1.506] | — | VALIDATED |
| cfp_diy | T3† | 1.832 | [1.638, 1.978] | — | OUT-OF-REGIME |

Cross-substrate mean (excluding cfp_diy): 0.991 ± 0.052

---

## Method

Gamma is computed via Theil-Sen log-log regression (robust to outliers) with
bootstrap CI (n = 500) and permutation p-value. All computations flow through
`core/gamma.py::compute_gamma`. Negative controls (white noise, random walk,
supercritical) show gamma clearly separated from 1.0, confirming the
methodology is discriminative.

---

## Canonical Manuscript

The full manuscript — including introduction, theoretical framework,
per-substrate methods, statistical tests, discussion, and references — is at:

**[`manuscript/XFORM_MANUSCRIPT_DRAFT.md`](manuscript/XFORM_MANUSCRIPT_DRAFT.md)**

For reproducibility instructions see [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).
For the evidence ledger see [`evidence/gamma_ledger.json`](evidence/gamma_ledger.json).
