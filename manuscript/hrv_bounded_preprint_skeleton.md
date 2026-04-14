# A Two-Branch Honest Report on γ-Scaling and Multifractal Width in Human Heart-Rate Variability — Skeleton

> **Status.** Preprint **skeleton**. Version 0.4, filed 2026-04-14.
> All Branch A full-cohort numbers now landed with full statistical
> rigour (Welch + Mann-Whitney U, Cohen d and Cliff's δ with 95 %
> CIs, Benjamini-Hochberg FDR across the panel, Wilson / Hanley-
> McNeil CIs on classifier metrics):
> - §4.2 panel-level contrast (n=72 vs n=44): six of eight panel
>   metrics significant at BH q < 10⁻³; SDNN and Poincaré SD2 at
>   q ≈ 2 × 10⁻¹⁵; DFA α₁ at q ≈ 2 × 10⁻⁹.
> - §4.3 MFDFA `(h(q=2), Δh)` marker + blind validation (7 seeds):
>   **Branch A NOT PROMOTED** — 0/7 seeds reach the pre-registered
>   AUC ≥ 0.80 / acc ≥ 0.70 gate; 2/7 falsify. Every seed's 95 %
>   AUC CI straddles 0.50 (chance). The pilot §4.1 effect sizes are
>   partly a pipeline artefact (§4.3.1).
> - Branch B full-cohort γ (§5.3) remains reserved.
> Not yet a submission.
>
> **Intended venue.** arXiv (q-bio.NC cross-listed to stat.AP).
> Targeted as a **bounded-claim pilot report**, not a discovery paper.
>
> **Governance.** Written against `docs/CLAIM_BOUNDARY.md` §2 and
> `docs/REPLICATION_PROTOCOL.md`. Every promoted claim is traceable
> to a locked manifest in `docs/EXTERNAL_REPLICATION_INVITATION.md`
> or its successor.
>
> **Principle.** Branch A splits into a panel-level positive (§4.2:
> classical HRV metrics separate NSR from CHF at the cohort level)
> and an MFDFA-marker negative (§4.3: the 2-D `(h(q=2), Δh)` marker
> does not pass its pre-registered promotion gate at n=116). Branch
> B reports a negative cross-subject γ finding at pilot scale
> (full-cohort still pending). Each finding is reported with
> explicit non-licence; none licenses the others.

---

## Abstract

We report three results from PhysioNet cardiac HRV recordings
(n=116: NSR2DB + NSRDB + CHF2DB + CHFDB). **Branch A — panel level
(positive, within-substrate):** the classical HRV panel separates
healthy (n=72) from CHF (n=44); DFA α₁ Cohen d = +1.52, SDNN
d = +2.04, Poincaré SD2 d = +2.06 (§4.2). Direction matches
Goldberger 2002 loss-of-complexity. **Branch A — MFDFA 2-D marker
(does not promote at scale):** the pilot §4.1 reported a
`(h(q=2), Δh)` marker separating NSR from CHF at n=5 with
Cohen d = −2.56 on `h(q=2)`. At full cohort n=116 under the §3.5
blind-validation protocol the marker does **not** promote —
0/7 seeds meet the pre-registered AUC ≥ 0.80 ∧ acc ≥ 0.70 gate;
2/7 falsify (§4.3). Part of the pilot's apparent effect is a
pipeline artefact (§4.3.1); under the canonical cohort pipeline
the pilot-scale effect shrinks to |d| ≈ 0.4. **Branch B (honest
negative, cross-subject):** at the VLF band, cross-subject γ
fitted via Welch PSD + Theil-Sen regression is **not** consistent
with γ ≈ 1 at pilot scale (n=5 mean 0.50 ± 0.44). Full-cohort γ
still pending (§5.3). The branches are reported jointly to prevent
selective framing; none licenses the other. External-lab SHA-locked
replication is open (`docs/EXTERNAL_REPLICATION_INVITATION.md` §9).

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

- **Source.** Four PhysioNet cardiac cohorts, total n=116:
  - Healthy (n=72): NSR2DB (n=54) + NSRDB (n=18).
  - Pathology (n=44): CHF2DB (n=29) + CHFDB (n=15).
- **Annotation filter.** Normal beats only (symbol `== "N"`).
- **RR truncation.** Per-pipeline: 20 000 beats for the MFDFA/γ
  pipeline; full record (≈50 k–140 k beats) for the classical HRV
  panel in §4.2.
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

### 4.2 Full cohort — classical HRV panel (n=72 healthy vs n=44 CHF)

Panel-level contrast on the n=116 cohort (`results/hrv_baseline/
branch_a_panel_contrast.json`, schema v2). For each metric we report
Welch's t (two-sided, unpaired) with its Satterthwaite df, its
two-sided p-value, the Benjamini-Hochberg FDR q-value across the
8-metric panel, Cohen's d with a 95 % Hedges-Olkin analytical CI, and
Cliff's δ as a non-parametric effect-size sibling. Six of the eight
metrics remain significant at q < 0.001 after FDR correction —
SDNN and Poincaré SD2 at q ≈ 2 × 10⁻¹⁵, DFA α₁ at q ≈ 2 × 10⁻⁹.

| Metric             | Healthy (n=72)    | CHF (n=44)        | Cohen d [95 % CI]      | Cliff's δ | Welch p   | BH q       |
|--------------------|-------------------|-------------------|------------------------|-----------|-----------|------------|
| DFA α₁             | 1.244 ± 0.167     | 0.925 ± 0.265     | +1.52  [+1.10, +1.94]  | +0.67     | 1.0 × 10⁻⁹ | 2.1 × 10⁻⁹ |
| DFA α₂             | 1.043 ± 0.113     | 1.181 ± 0.196     | −0.92  [−1.31, −0.53]  | −0.59     | 7.2 × 10⁻⁵ | 1.0 × 10⁻⁴ |
| Sample entropy     | 0.761 ± 0.293     | 1.014 ± 0.380     | −0.77  [−1.16, −0.38]  | −0.39     | 3.1 × 10⁻⁴ | 4.1 × 10⁻⁴ |
| SDNN (ms)          | 136.7 ± 30.9      | 68.3 ± 37.3       | +2.04  [+1.59, +2.50]  | +0.85     | 4.9 × 10⁻¹⁶ | 2.0 × 10⁻¹⁵ |
| RMSSD (ms)         | 30.9 ± 14.9       | 21.8 ± 17.1       | +0.58  [+0.19, +0.96]  | +0.51     | 4.6 × 10⁻³ | 4.6 × 10⁻³ |
| LF/HF              | 4.17 ± 2.74       | 1.71 ± 1.06       | +1.09  [+0.69, +1.49]  | +0.67     | 6.9 × 10⁻¹⁰ | 1.9 × 10⁻⁹ |
| Poincaré SD1 (ms)  | 21.8 ± 10.5       | 15.4 ± 12.1       | +0.58  [+0.19, +0.96]  | +0.51     | 4.6 × 10⁻³ | 4.6 × 10⁻³ |
| Poincaré SD2 (ms)  | 191.9 ± 43.6      | 94.6 ± 52.8       | +2.06  [+1.60, +2.52]  | +0.85     | 3.9 × 10⁻¹⁶ | 2.0 × 10⁻¹⁵ |

*Welch p and BH q are two-sided.* Non-parametric Mann-Whitney U
p-values (not shown) are within ±0.5 log units of the Welch p's for
every metric — direction and significance agree across the
parametric/non-parametric divide, which argues against a
Gaussian-assumption artefact.

**Direction check.** DFA α₁ drops and DFA α₂ rises under CHF — the
classical Goldberger-2002 "loss-of-complexity" pattern at the panel
level. SDNN and Poincaré SD2 (both long-timescale amplitude
measures) collapse; RMSSD / SD1 (short-timescale) drop less. Sample
entropy rises in CHF, which runs *against* the loose "complexity
decreases" summary of the literature at the single-scale Richman-
Moorman definition; this is not new (e.g. Costa-Goldberger 2002
multiscale entropy re-interprets that single-scale rise), but it is
worth flagging here rather than silently smoothing it out.

> **§4.1 caveat.** The pilot numbers were computed through the
> `substrates/physionet_hrv/*_client.py` RR pipeline, which differs
> from the canonical cache pipeline in how it handles ectopic beats
> — see §4.3.1. Under the canonical pipeline the pilot-scale
> contrast shrinks from |d| = 2.56 on `h(q=2)` to |d| ≈ 0.4. The
> pilot remains in the record as historical context, not as an
> independently replicated finding.

### 4.3 Full cohort — MFDFA `(h(q=2), Δh)` marker

MFDFA applied to all 116 cached RR arrays (`results/hrv_mfdfa/
cohort_summary.json`). Welch / Cohen d on the two features, then the
§3.5 blind-validation protocol run across 7 seeds.

**Per-group MFDFA aggregates (n=116):**

| Group               | h(q=2) mean ± sd | Δh mean ± sd   |
|---------------------|------------------|----------------|
| Healthy (n=72)      | 1.112 ± 0.108    | 0.107 ± 0.086  |
| Pathology (n=44)    | 1.160 ± 0.145    | 0.185 ± 0.305  |
| Welch t             | −1.88            | −1.66          |
| Cohen d             | −0.39            | −0.39          |

**Blind-validation (§3.5 protocol), 7 seeds, 50/50 stratified split,
Wilson CI on accuracy, Hanley-McNeil CI on AUC:**

| Seed | Acc [95 % CI]          | AUC [95 % CI]          | d(proj) | Verdict       |
|------|------------------------|------------------------|---------|---------------|
| 1    | 0.586 [0.458, 0.704]   | 0.596 [0.447, 0.745]   |  0.26   | FALSIFIED     |
| 7    | 0.603 [0.475, 0.719]   | 0.609 [0.461, 0.756]   |  0.40   | INCONCLUSIVE  |
| 17   | 0.690 [0.562, 0.794]   | 0.619 [0.472, 0.765]   |  0.44   | INCONCLUSIVE  |
| 42   | 0.586 [0.458, 0.704]   | 0.640 [0.496, 0.784]   |  0.60   | INCONCLUSIVE  |
| 123  | 0.638 [0.509, 0.750]   | 0.663 [0.522, 0.803]   |  0.66   | INCONCLUSIVE  |
| 2024 | 0.569 [0.441, 0.688]   | 0.576 [0.425, 0.726]   |  0.19   | FALSIFIED     |
| 2026 | 0.638 [0.509, 0.750]   | 0.620 [0.474, 0.766]   |  0.51   | INCONCLUSIVE  |

**Verdict distribution:** 0 PROMOTED, 5 INCONCLUSIVE, 2 FALSIFIED
across 7 seeds. Median AUC 0.620, median accuracy 0.603. No seed
meets the pre-registered promotion threshold (AUC ≥ 0.80 AND
accuracy ≥ 0.70).

**Crucially**, every seed's 95 % AUC CI straddles or brushes 0.50:
the worst lower bound is 0.425 (seed 2024), the best lower bound is
0.522 (seed 123). Under rigorous interval coverage, *no* seed
produces an AUC that is statistically distinguishable from chance
at α = 0.05 with Hanley-McNeil analytical SE. This is the formal
statement behind "the marker does not pass its promotion gate": it
is not merely below a fixed threshold, it is compatible with
chance at n=58 test.

**Direction check.** The pilot §4.1 reported `h(q=2)` *decreasing*
under CHF (NSR 1.096 vs CHF 0.736; Cohen d = −2.56). At full cohort
`h(q=2)` *increases* slightly under CHF (Cohen d = −0.39 with mean
signs flipped: healthy 1.112 < pathology 1.160). The Δh direction
is preserved (wider in CHF) but at |d| = 0.39 rather than pilot
|d| = 1.85. The pilot effect was **not** replicated at scale.

**Branch A MFDFA marker: NOT PROMOTED**. Outcome is consistent with
borderline failure — sometimes INCONCLUSIVE, sometimes FALSIFIED
depending on the random split — but never promotes. Per §3.5 this
closes the Branch A promotion gate negatively: the `(h(q=2), Δh)`
fingerprint is not a pathology-discriminative marker at the cardiac
substrate and the pilot scale.

#### 4.3.1 RR-extraction pipeline note

The §4.1 pilot numbers and the §4.3 full-cohort numbers were
computed from the **same PhysioNet records** but through two
different RR-derivation pipelines that differ at ectopic beats:

- **§4.1 pilot pipeline** (`substrates/physionet_hrv/nsr2db_client.py`,
  `chf2db_client.py`). Masks annotations to `symbol == "N"`, then
  `np.diff()` across the surviving beat stream. This produces an RR
  *that spans ectopic beats* whenever the ectopic sits between two
  normal beats. Historical behaviour; used in the pilot ledger.
- **§4.3 full-cohort pipeline** (`tools/data/physionet_cohort.py`).
  Takes `np.diff(samples)` only where *both* endpoints are `"N"`.
  This is the Task Force 1996 §3.1 convention: RR is defined only
  between consecutive normal beats. This is the pipeline committed
  into `data/raw/{cohort}/{record}.rr.npy`.

Applying the full-cohort pipeline to the same 5 NSR + 5 CHF pilot
subjects changes `h(q=2)` means to 1.169 (NSR) vs 1.102 (CHF) — a
1/7 of the pilot-reported |d|. The pilot's strong separation is in
part an artefact of the across-ectopic RR spans in the pilot
pipeline. Going forward the `tools/data/physionet_cohort.py`
pipeline is the canonical one; §4.1 is retained as the historical
pilot, not as a promoted claim.

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

### 5.3 Full cohort (placeholder, n=72 healthy)

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
| 0.2     | 2026-04-14 | n=116 panel-level Branch A contrast landed (§4.2). MFDFA full-cohort marker (§4.3) + Branch B cross-subject γ (§5.3) still reserved. |
| 0.3     | 2026-04-14 | n=116 MFDFA marker + 7-seed blind-validation executed (§4.3). Branch A MFDFA **NOT PROMOTED**. Pilot pipeline discrepancy documented in §4.3.1. Branch B full-cohort γ (§5.3) still pending. |
| 0.4     | 2026-04-14 | Full statistical rigour applied: Welch + Mann-Whitney U; 95 % CIs on Cohen d, Cliff's δ, accuracy (Wilson), AUC (Hanley-McNeil); Benjamini-Hochberg FDR across the §4.2 panel. Text unchanged in claim direction — the marker negative is now also interval-level: every seed's AUC CI straddles 0.50. |
| 0.5     | TBD        | Full-cohort Branch B γ (§5.3).                              |
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
