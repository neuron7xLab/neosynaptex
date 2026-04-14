# A Two-Branch Honest Report on γ-Scaling and Multifractal Width in Human Heart-Rate Variability — Skeleton

> **Status.** Preprint **skeleton**. Version 0.1, scaffold filed
> 2026-04-14. Contains section structure, the bounded-claim framing,
> the blind-validation protocol, and placeholders for numbers that
> will land as the n=116 cohort data arrives. Not yet a submission.
>
> **Intended venue.** arXiv (q-bio.NC cross-listed to stat.AP).
> Targeted as a **bounded-claim pilot report**, not a discovery paper.
>
> **Governance.** Written against `docs/CLAIM_BOUNDARY.md` §2 and
> `docs/REPLICATION_PROTOCOL.md`. Every promoted claim is traceable
> to a locked manifest in `docs/EXTERNAL_REPLICATION_INVITATION.md`
> or its successor.
>
> **Principle.** Branch A reports a positive within-substrate finding
> with an explicit non-licence. Branch B reports a negative cross-
> subject finding that falsifies a universal-γ framing at the cardiac
> substrate. Neither branch licenses the other. Both are reported
> with equal weight.

---

## Abstract (placeholder — locked once n=116 data lands)

We report two results from PhysioNet cardiac HRV recordings.
**Branch A (positive, within-substrate):** a 2-dimensional
fingerprint combining the classical Hurst exponent `h(q=2)` and
the multifractal width `Δh` separates healthy NSR from CHF
pathology at pilot scale (n=5 vs n=5, Welch t = −4.05 / Cohen d =
−2.56 on `h(q=2)`; t = +2.92 / d = +1.85 on `Δh`). The direction
is consistent with the Goldberger 2002 HRV-loses-complexity
literature. **Branch B (honest negative, cross-subject):** at the
VLF band, cross-subject γ fitted via Welch PSD + Theil-Sen
regression is **not** consistent with γ ≈ 1 (n=5 mean 0.50 ± 0.44,
range [0.07, 1.09]). A universal cross-substrate γ framing is not
supported by the cardiac substrate at the pilot scale. The two
branches are reported jointly to prevent selective framing;
neither licenses the other. Full-cohort reanalysis (n=54 NSR +
n=62 CHF = n=116) and one external-lab SHA-locked replication
gate promotion of either claim.

---

## 1. Introduction

- **Context.** HRV has a 30-year literature on spectral scaling
  and multifractal analysis (Peng, Ivanov, Goldberger, Havlin).
- **Problem.** Cross-paper γ comparisons are noisy; null-model
  hierarchies are rarely matched; within-subject vs cross-subject
  claims are frequently conflated.
- **Our contribution.**
  1. A sharp separation of *within-substrate* contrast (Branch A)
     from *cross-subject universal γ* (Branch B), reported with
     equal weight.
  2. A SHA-locked reproducibility manifest covering all records,
     pipeline parameters, and surrogate procedures.
  3. A blind-validation protocol for promoting Branch A to a
     per-subject marker beyond the pilot scale.
- **What we are not claiming.**
  - No clinical / diagnostic claim.
  - No cross-substrate universal γ ≈ 1.
  - No generalisation to AF, MI, valvular, or non-cardiac pathology.

## 2. Data

- **Source.** PhysioNet NSR2DB (healthy, n=54) and CHF2DB
  (congestive heart failure, n=62). Full-cohort target n=116.
- **Annotation filter.** Normal beats only (symbol `== "N"`).
- **RR truncation.** First 20 000 RR intervals per subject.
- **Reproducibility.** Every subject's RR array is SHA-256 pinned
  in `docs/EXTERNAL_REPLICATION_INVITATION.md` §4. The SHA is the
  byte-level invariant; any external pipeline whose SHAs match is
  working on byte-identical input to ours.

## 3. Methods

### 3.1 γ-fit

- Cubic-spline interpolation of the RR series onto a uniform 4 Hz
  grid.
- Welch PSD: `nperseg = 1024`, `detrend = "constant"`.
- Slope on the VLF band `[0.003, 0.04] Hz` via Theil–Sen (robust)
  regression with bootstrap 95% CI.
- Not an MLE fit to a probability distribution (Clauset et al. 2009
  is inapplicable here); this is a scaling-relation regression on
  paired observables.

### 3.2 MFDFA

- Kantelhardt 2002 generalized detrended fluctuation analysis
  applied to the raw RR series (not the uniform-resampled signal).
- `q ∈ [-3, 3]` step `0.5`, `s ∈ [16, rr_truncated / 4]`, 20 scales,
  order-1 polynomial detrending.
- Classical Hurst `h(q=2)` and multifractal width `Δh = max(h) − min(h)`
  reported per subject.

### 3.3 Null-model hierarchy

The n=1 pilot already tested shuffled, IAAFT, and AR(1) nulls (see
`evidence/replications/physionet_nsr2db/prereg.yaml`). IAAFT was not
separable — expected, because γ at the VLF band is a linear spectral
signature that IAAFT preserves by construction. The primary null for
this preprint is the **beat-interval null**: shuffle the RR sequence
itself *before* uniform resampling. This destroys beat-to-beat order
while preserving the marginal RR distribution; unlike IAAFT, it does
not preserve the linear spectrum (the cumulative beat-time grid
changes). Separation under the beat-interval null at `z > 3` is a
necessary condition for Branch B's γ result to be attributed to
temporally-ordered beat structure rather than marginal-distribution
artefact.

### 3.4 Two-cohort contrast (Branch A)

- 2D feature `(h(q=2), Δh)` per subject.
- Welch's t-test and Cohen's d on each dimension, healthy (NSR) vs
  pathology (CHF).
- No regularisation, no feature engineering beyond the 2D point.

### 3.5 Blind-validation protocol (Branch A, pre-promotion)

Promotion of Branch A beyond pilot scale requires a blind split:

1. A custodian (not the estimator author) randomly partitions the
   full n=116 cohort into a **train set** (half of NSR + half of
   CHF, labels revealed) and a **test set** (the other half, labels
   **held**).
2. We lock the `(h(q=2), Δh)` threshold (or classifier) on the
   train set; commit SHA and the lock file are pushed.
3. The custodian runs the locked classifier on the test set and
   reports per-subject predicted label.
4. The custodian reveals test-set ground truth only **after** the
   predicted labels are committed.
5. Out-of-sample Cohen d, AUC, and per-class accuracy are reported
   against the locked classifier.

A failure of the blind step falsifies the marker at n > pilot.
A success promotes Branch A to `measured_within_substrate_blinded`.

## 4. Results — Branch A (positive, within-substrate)

### 4.1 Pilot (n=5 NSR vs n=5 CHF, already in the ledger)

- `h(q=2)`: NSR mean 1.096 ± 0.090, CHF mean 0.736 ± 0.177;
  Welch t = −4.05, Cohen d = −2.56.
- `Δh`: NSR mean 0.185 ± 0.092, CHF mean 0.656 ± 0.348;
  Welch t = +2.92, Cohen d = +1.85.
- Cluster separation consistent with Goldberger 2002
  HRV-loses-complexity direction.

### 4.2 Full cohort (placeholder, n=54 NSR + n=62 CHF)

- Results filed after the n=116 run lands. Tables and figures
  reserved.
- Blind-validation result reserved.

### 4.3 Interpretation boundary for Branch A

- The marker passes a pilot contrast and (pending) a blind
  validation. It does **not** become a diagnostic tool.
- The marker is **within-cardiac**; it does not license any
  cross-substrate claim.
- Mechanism (why `h(q=2)` drops and `Δh` widens under CHF) is
  outside scope.

## 5. Results — Branch B (honest negative, cross-subject γ)

### 5.1 Pilot (n=5 NSR)

- Per-subject γ: `[1.0855, 0.0724, 0.418, 0.367, 0.566]`.
- Mean 0.502, SD 0.444, range [0.072, 1.086].
- Beat-interval null separates on 4/5 subjects at `z > 3` (γ **does**
  require beat-temporal order within each subject).
- Subject nsr001 is an outlier.

### 5.2 Interpretation boundary for Branch B

- The cardiac substrate does **not** carry γ ≈ 1 at the pilot
  cross-subject level.
- The "per-subject cardiac γ" is a subject-dependent quantity, not a
  population invariant.
- This result **does not** rule out a per-subject calibrated γ as a
  state marker; it rules out an uncalibrated γ as a population
  invariant.
- The result is a **theory-revising** replication (per
  `docs/REPLICATION_PROTOCOL.md` §3) against the universal-γ
  framing.

### 5.3 Full cohort (placeholder, n=54 NSR)

- Per-subject γ distribution, reserved.
- Stratification by age / sex (as available in PhysioNet metadata),
  reserved.
- Within-subject temporal stability of γ (test/retest), reserved.

## 6. Joint discussion

- Branch A and Branch B are *both* true of the same cardiac
  substrate. Reporting only Branch A would be a selection effect;
  reporting only Branch B would miss the positive finding.
- The correct epistemic move is to report both with explicit
  boundaries, which is what this preprint does.
- The combination constrains future claims:
  - Any paper that claims "γ ≈ 1 is a universal cardiac invariant"
    must reconcile with Branch B.
  - Any paper that claims "HRV multifractal analysis does not
    discriminate pathology at pilot scale" must reconcile with
    Branch A.

## 7. Related work

Peng et al. 1995; Ivanov et al. 1999; Goldberger et al. 2002;
Havlin et al. 1999; Kantelhardt et al. 2002; Hengen & Shew 2025.
Full citations to land with v1.0.

## 8. Data and code availability

- Code, adapters, run scripts: github.com/neuron7xLab/neosynaptex
  (commit SHA to be stamped at submission).
- Per-subject RR-series SHA manifest: `docs/EXTERNAL_REPLICATION_INVITATION.md`.
- PhysioNet data: `https://physionet.org/content/nsr2db/1.0.0/` and
  `https://physionet.org/content/chf2db/1.0.0/`.
- External replication invitation is open — see §8 of
  `docs/EXTERNAL_REPLICATION_INVITATION.md`.

## 9. Limitations

- Both cohorts are historical archival recordings; no behavioural
  state annotation.
- RR truncation at 20 000 beats is a scale-compression choice; scale
  dependence on truncation length has not been systematically tested.
- Cohort sizes 54 + 62 are modest compared to Hengen & Shew 2025's
  cross-lab meta-analysis precedent.
- No external-lab replication has yet been filed; claim-status for
  both branches remains at `measured_but_bounded` until at least one
  confirming external report lands (see
  `docs/EXTERNAL_REPLICATION_INVITATION.md` §9).

## 10. Pre-registration / version history

| Version | Date       | State                                                       |
|---------|------------|-------------------------------------------------------------|
| 0.1     | 2026-04-14 | Skeleton filed. Section structure + pilot numbers + blind-validation protocol. Full-cohort numbers reserved. |
| 0.2     | TBD        | Full n=116 results landed. Blind-validation executed.       |
| 1.0     | TBD        | External-replication gate passed; preprint submitted.       |

## 11. Authors and contributions

To be finalised at v1.0. Author list, ORCID IDs, CRediT taxonomy
assignments.

## 12. Acknowledgements

PhysioNet is supported by the NIH (NIBIB and NIGMS); source
citations and grant numbers land at v1.0.

---

**Appendix A — full parameter lock.** See
`docs/EXTERNAL_REPLICATION_INVITATION.md` §5 (identical parameters
are not duplicated here; the invitation is the canonical source).

**Appendix B — null-model hierarchy audit.** See
`docs/NULL_MODEL_HIERARCHY.md`.

**Appendix C — claim-status promotion rules.** See
`docs/CLAIM_BOUNDARY.md` §2 and `docs/REPLICATION_PROTOCOL.md` §3.
