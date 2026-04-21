# Reviewer attack surface · canon closure v1.0

> **Role.** Internal artefact, not for publication. Enumerates every
> reviewer attack on the γ-invariant claim stack (Claims C-001..C-004 of
> `docs/CLAIM_BOUNDARY.md`) and the precise answer with resolvable
> evidence pointer. This document is the single source of defensive
> coherence during review cycles.
>
> **Rule.** Every Evidence pointer below resolves to an existing
> section of the manuscript, an existing claim row in
> `CLAIM_BOUNDARY.md`, or an existing section of the operational
> lemma record. Vague pointers ("manuscript", "README") are forbidden.
>
> **Rule.** Answer column carries minimum two sentences per row.

## Attack table

| # | Attack | Answer | Evidence |
|---|--------|--------|----------|
| 1 | This is only a reformulation of Restrepo--Ott--Hunt (2005). | Correct: Lemma 1 is obtained by substituting the operational definitions $K := J_c$ and $C := \lambda_1(A_N)$ into the RoH spectral-onset formula; we cite their proof rather than reproduce it. The novel contribution is the operational reframing of critical onset as a cost--complexity scaling law, the explicit identification of $\gamma = 1$ as the analytical anchor, and a numerical verification with explicit assumption auditing. | `manuscript/arxiv_submission.tex` §2.3 *Proof*; `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §3; `docs/CLAIM_BOUNDARY.md` · Claim C-001. |
| 2 | Thermodynamic cost was replaced by critical coupling; the framework is not actually thermodynamic. | Correct: the operational definition $K := J_c$ is stated verbatim in §2.1.2 and is the definition used everywhere downstream. No appeal to stochastic thermodynamics, dissipation inequalities, or nonequilibrium entropy production is made in Lemma 1; $K$ is an onset threshold, not a heat-flow quantity. | `manuscript/arxiv_submission.tex` §2.1.2 *Definition of cost*; `docs/CLAIM_BOUNDARY.md` · Claim C-001 *Scope*; `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §1. |
| 3 | Universality is not proved analytically. | Correct: universality is a **conjecture** in this work (`CLAIM_BOUNDARY.md` C-004, layer = Conjectural), not a theorem. The only analytical result is Lemma 1 on Kuramoto dense graphs (C-001, layer = Proved); every outward-facing artefact now carries the verbatim bridging sentence stating this scope boundary. | `docs/CLAIM_BOUNDARY.md` · Claim C-004 layer=Conjectural; `manuscript/arxiv_submission.tex` §2.6 (bridging sentence at end of §2). |
| 4 | Other substrates remain empirical and cannot be claimed as evidence for a universal law. | Correct: per-substrate γ values (zebrafish, HRV, EEG, Gray--Scott, BN-Syn, Kuramoto, etc.) are *measurements* tagged at Claim layer C-003 (Empirical) in the boundary document and enumerated in `evidence/gamma_ledger.json`. They carry substrate-specific prereg, unit-of-analysis, and surrogate-null requirements under `MEASUREMENT_METHOD_HIERARCHY.md`, and they do not license a cross-substrate theorem. | `docs/CLAIM_BOUNDARY.md` · Claim C-003 layer=Empirical; `evidence/gamma_ledger.json`; `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`. |
| 5 | The choice $C := \lambda_1(A)$ is restrictive and disallows reasonable alternatives (average degree, effective resistance, participation ratio). | Intentional: $\lambda_1(A)$ is the spectral scale that controls Kuramoto onset in the Restrepo--Ott--Hunt derivation, and is the *only* complexity measure under which the onset formula factorises as $J_c = \kappa_0\,C^{-1}$. On the complete graph $K_N$ this reduces to $N-1$; on other topologies it is the correct spectral quantity, not the average degree. Alternative $C$ definitions would require a different Lemma. | `manuscript/arxiv_submission.tex` §2.1.3 *Definition of complexity*; `manuscript/arxiv_submission.tex` §2.4 *Special case $\Delta = 0.5$*; `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §2 (assumption A2). |
| 6 | The numerical verification tests only the complete graph, where assumptions (A1)--(A3) are trivially satisfied. | Correct: the published verification anchors the complete-graph case only, and this is stated as Scope in `CLAIM_BOUNDARY.md` Claim C-002. Non-trivial spectral topologies (Erdős--Rényi, expanders, small-world) are explicitly catalogued as open problems in the operational lemma record and are not claimed. | `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §7.2 *Non-complete graphs (open problem)*; `manuscript/arxiv_submission.tex` §2.5 *Numerical verification*; `docs/CLAIM_BOUNDARY.md` · Claim C-002 Scope. |
| 7 | The verification uses the Kuramoto 1975 mean-field self-consistency, not the full RoH spectral derivation; the two do not coincide off the complete graph. | On $K_N$ they do coincide: $\lambda_1(A_{K_N}) = N-1$, and the mean-field self-consistency equation is the $N \to \infty$ limit of the RoH spectral condition. The verification script simulates the mean-field form and reports the unnormalized $K_\mathrm{sum}^{(c)} = K_\mathrm{mf}^{(c)}/(N-1)$ in the log--log fit; the bridge between conventions is documented in §2.6, and the more general non-complete-graph test is listed as open work. | `manuscript/arxiv_submission.tex` §2.5 *Numerical verification*; `manuscript/arxiv_submission.tex` §2.6 *Remark on normalization conventions*; `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §4 *Normalization-convention analysis*, §7.2. |
| 8 | The asymptotic-only fit (N ≥ 100) gives $\hat\gamma = 0.9875$ with CI that misses 1.0 by $5 \times 10^{-4}$; the primary full-fit result is cherry-picked. | The asymptotic downward bias is a finite-size artefact of the mean-field self-consistency estimator $K(1-r^2)$, documented and reproduced across three independent methodology variants (threshold crossing, wide $K$-grid, narrow mid-supercritical grid). The operator directive of 2026-04-21 elected the full fit as the primary anchor precisely because including $N = 30$ widens the $\log \lambda_1$ range and neutralises the bias, yielding $\hat\gamma = 0.9923$ with CI $= [0.9811, 1.0032]$ that contains 1.0; both fits are recorded in `evidence/lemma_1_numerical.json`. | `evidence/lemma_1_numerical.json#primary_fit`; `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §7.1 *Pre-asymptotic bias in the mean-field self-consistency estimator*. |

## Evidence-pointer resolution audit

Every pointer above is verified to resolve as of 2026-04-21:

- `manuscript/arxiv_submission.tex` §2.1.2, §2.1.3, §2.3, §2.4, §2.5, §2.6 — present (commit `9d5b6f96`).
- `docs/CLAIM_BOUNDARY.md` §CLAIM ROWS C-001..C-004 — present (commit `65be27a9`).
- `docs/LEMMA_1_KURAMOTO_GAMMA_UNITY.md` §1, §2, §3, §4, §7.1, §7.2 — present (commit `9d5b6f96`).
- `evidence/lemma_1_numerical.json#primary_fit` — present; `anchor_value_for_abstract = 0.9923`.
- `evidence/gamma_ledger.json` — present; `lemma_1_kuramoto_dense` entry at `entries.lemma_1_kuramoto_dense`.
- `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml` — present.

If any pointer above fails to resolve in a future revision, the
canonical enforcement script `scripts/canon_closure_check.py` must
either be updated or the row repaired; silent drift is forbidden.

## Scope lock

No new attack row is added without an accompanying Evidence pointer
that resolves. The list is not closed — new attacks discovered during
review must be appended with full two-sentence answer + resolvable
Evidence — but no row may exit this document in a state with a broken
or vague pointer.

---

**claim_status:** measured (about the defensive surface itself)
**effective:** 2026-04-21
**referenced by:** `docs/CONTRIBUTION_STATEMENT.md` (pillar 2),
`scripts/canon_closure_check.py` (check 2), review-cycle playbook.
