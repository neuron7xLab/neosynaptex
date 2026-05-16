# DOPA-VALIDITY-001 — Pre-Registration

Frozen before any result was read. Supersedes nothing in
`evidence/dopa_closure/RETRACTION.md` (authoritative). This pre-registers an
*instrument*, not a theory verdict. Constants live only in
`experiments/dopa_validity_001_config.py` (SSOT); `config_hash` pins them.

## Claim under test

> An *actual* DNCA/dopamine-derived **signed** vRPE predicts verification
> benefit better than uncertainty/margin, under an admissible verifier and a
> true sign-flip negative control.

This is a claim about an *instrument's discriminative validity*, not about
DOPA-CLOSURE. No run of this scaffold can promote or kill the theory.

## What counts as actual DNCA/dopamine signal

`neuron7x_agents.dnca.neuromodulators.dopamine.DopamineOperator`, imported and
forward-run. A sklearn/TF-IDF/logistic proxy is **forbidden** and is not the
signal under any renaming.

## Signed vRPE definition

`vRPE_i = clamp(δ_i, −1, 1)` from `DopamineOperator.modulate(...)["valence"]`,
where `δ = r + γ·V(s_t) − V(s_{t-1})` *before* the Schultz asymmetric gain.
`r` (reward context) is the policy's own confidence — **ground-truth-free**, so
no label leakage. Sign is preserved.

## True sign-flip negative control

`vRPE → −vRPE`, then routed on the signed value. Implemented as
`dopa_inverted = −dopa` with `dopa = −vRPE`. The complement of `|vRPE|` is
**forbidden** (the #199 function substitution). The control is required to be
non-degenerate: it must reorder routing when signs are mixed.

## Admissible verifier criteria

Independent of the policy; deterministic; network disabled; outcome bound to an
evidence hash under a fixed boundary; and **accuracy strictly above both the
majority-class and random baselines** on the target items.

## Verified Closure definition (distinct from accuracy)

A Verified-Closure event = the verifier spent a budgeted action on an item AND
returned a definitive VERIFIED/REFUTED under the fixed boundary. VCR =
events / items. It is **not** policy label accuracy: it counts independent
verifier-confirmed closures regardless of whether the policy's own label was
right. If VCR is numerically equal to policy accuracy → metric collapse.

## Pre-registered thresholds (no post-hoc tuning)

- Step B2 truth-correlation: two-sided Spearman `p < VRPE_TRUTH_CORR_ALPHA`
  (= 0.01) **and** `ρ > 0`.
- Step D advantage: `delta ≥ DELTA_MIN` (= 0.05 of recoverable benefit).
- Step D significance: Wilcoxon signed-rank `p < ALPHA` (= 0.01), `N_SEEDS` = 12.
- Effect size: paired rank-biserial, reported regardless of sign.

Any retuning of these constants invalidates the run; they are hashed.

## Decision rules

- **INADMISSIBLE rule.** If Step A fails →
  `INADMISSIBLE_MISSING_DNCA_EXECUTABLE_SIGNAL`. If the verifier ≤ majority or
  ≤ random, **or** the signed vRPE is not truth-correlated per Step B2 →
  `INADMISSIBLE_WEAK_VERIFIER` (an uninformative routing signal is a weak
  instrument; RETRACTION precondition #3 made executable). If VCR collapses to
  accuracy → `INADMISSIBLE_METRIC_COLLAPSE`. A clean INADMISSIBLE is **success**.
- **Survival rule.** `SURVIVED_INITIAL` iff *all* hold: Steps A/B1/B2/C passed;
  `delta ≥ DELTA_MIN`; Wilcoxon `p < ALPHA`; the true sign-flip control loses
  its advantage; verifier stays above majority and random.
- **Kill rule.** If admissibility (A,B1,B2,C) passed but the survival
  conjunction fails → `KILLED`, written **only** as
  `KILL-0979B_DNCA_DOPA_ROUTING`, scoped strictly to this implementation. The
  theory remains UNTESTED. No unscoped "DOPA-CLOSURE killed" may ever be emitted.
- **No post-hoc tuning rule.** No threshold, seed, feature, or policy may be
  changed after observing any score. The `repro_hash` binds the verdict and all
  decision inputs, not merely a metric.

## Claim status

`claim_status: hypothesized` until a run reaches Step D with measured
policy scores; an INADMISSIBLE or scaffold-only run stays `hypothesized`.
