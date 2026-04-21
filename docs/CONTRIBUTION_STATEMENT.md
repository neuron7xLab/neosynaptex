# Contribution

> **Role.** Canonical statement of what this work adds, expressed in
> three pillars. Every public framing of the contribution — README
> intro, manuscript §1, talk abstracts, grant narratives — reduces
> to the three statements below. No additional pillar, no reduction
> of any pillar.

This work makes three contributions:

## 1. Operational reframing

Critical onset of coherence in a coupled-oscillator system is reformulated
as a **cost--complexity scaling law** $K(C) \sim C^{-\gamma}$, with

- $K := J_c$, the critical coupling at onset,
- $C := \lambda_1(A)$, the largest eigenvalue of the adjacency matrix.

This reframing turns the question "at what coupling does coherence
emerge?" into a quantitative prediction about how cost scales with
a graph-intrinsic complexity measure. The framework is operational,
falsifiable, and graph-topology-aware; it is the entry point for
every claim and every measurement in this repository.

## 2. Rigorous anchor case

For the Kuramoto model on dense symmetric graphs, we prove
**$\gamma = 1$ analytically** (Lemma 1), building directly on the
spectral onset formula of Restrepo--Ott--Hunt (2005). The lemma states
$J_c = \kappa_0 \cdot \lambda_1(A)^{-1}$ with $\kappa_0 = 2/(\pi\,g(0))$
under assumptions (A0)--(A3); the proof is a substitution into the RoH
formula, not a rederivation.

Numerical verification on complete graphs $K_N$ with Lorentzian
frequencies $\Delta = 0.5$ at $N \in \{30, 100, 300, 1000, 3000\}$
yields $\hat\gamma = 0.9923$ with 95% CI $= [0.9811, 1.0032]$
containing the analytical value. This is the **analytical anchor**:
the one substrate where $\gamma = 1$ is a theorem, not a measurement.

## 3. Empirical cross-substrate program

We test whether the exponent $\gamma = 1$ appears beyond Kuramoto
by measuring it on biological, chemical, and cognitive substrates
(zebrafish morphogenesis, HRV PhysioNet, EEG motor imagery,
Gray--Scott reaction--diffusion, BN-Syn spiking criticality, and the
cross-domain integrator), each under its own prereg, unit-of-analysis,
and surrogate-null gauntlet. The results support an **empirical
cross-substrate convergence conjecture** (Claim C-004 of
`docs/CLAIM_BOUNDARY.md`), which is **not proved analytically in
this paper**. Cross-substrate claims live at the Empirical layer
(C-003), with a single open conjecture at the Conjectural layer
(C-004); they do not license a universal theorem.

---

## What this paper does *not* claim

- The contribution is **not** the existence of the Kuramoto threshold
  formula. That formula is due to Kuramoto (1975) and Restrepo--Ott--Hunt
  (2005); we cite rather than rederive.
- The contribution is **not** a proof of universality. Only the
  Kuramoto dense-graph case is proved; all other substrate observations
  are empirical.
- The contribution is **not** a thermodynamic derivation. $K := J_c$ is
  an onset threshold, not a dissipation quantity.

The contribution is the three-pillar triad above: **operational
framework, one rigorous anchor, and an empirical program**.

---

## Cross-references

This document is linked from:

- `README.md` (intro / Contribution section)
- `manuscript/arxiv_submission.tex` §1 *Introduction* (Contribution paragraph)
- `docs/CLAIM_BOUNDARY.md` (preface, as the public-facing framing of
  the claim boundary's three layers)
- `docs/REVIEWER_ATTACK_SURFACE.md` (row 1 Answer column rests on
  pillar 2; row 3 rests on pillar 3)
- `scripts/canon_closure_check.py` check 3

---

**claim_status:** measured (about the contribution statement itself)
**effective:** 2026-04-21
