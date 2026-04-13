# Adversarial Controls — Protocol Constraints for γ Claims

> This is a protocol-layer constraints document. It is **not canon** and
> **not literature review**. It constrains how γ-related claims are
> generated, validated, and reported inside this repository.

## 1. Purpose

Turn the reviewed evidence on 1/f-like scaling into an operational
constraints specification. Every γ-related experiment, PR, and
manuscript method in this repository MUST satisfy the controls and
reporting rules below before any interpretive claim is admissible.

## 2. Scope

Applies to every artefact that reports, derives, or depends on a value of
γ, an exponent of a power-law fit, a 1/f-like spectrum, a Detrended
Fluctuation Analysis (DFA) exponent, an avalanche exponent, or any
equivalent scale-free signature. Applies regardless of substrate: neural,
neurorobotic, reaction-diffusion, Kuramoto, or any future addition.

Grounding that is admissible for this document:

- Hengen & Shew (2025, *Neuron*) — review-level evidence that criticality
  can act as a multiscale set point across many neural datasets, with an
  explicit meta-analysis of 140 datasets published 2003–2024.
- Aguilera et al. (2015, *PLoS ONE* 10(2):e0117465) — minimal neurorobotic
  model where robust 1/f structure emerges **only** when nonlinear
  coupling, homeostatic plasticity, and sensorimotor feedback are jointly
  present; removing any one destroys the signature.

Grounding that is **not** admissible here:

- Any claim about 1/f-like structure in trained deep networks (e.g. LSTM
  activations). No review-level citation has been verified for this
  document. The controls in Section 4 apply to any such future claim
  **regardless of citation**; the claim itself does not enter Section 2
  grounding until a primary source is verified.
- Historical small-N EEG precedents with `n < 10` used as a canonical
  anchor. They may be cited as background but MUST NOT serve as primary
  evidence for any repository-level γ claim.

## 3. Core Rule

γ ≈ 1 is a **candidate regime marker**, never standalone proof of
criticality, cognition, or intelligence. Every γ-related claim in this
repository MUST pass the adversarial controls in Section 4 and the
reporting contract in Section 6 before it is interpreted.

A γ value with no adversarial control is a number, not evidence.

## 4. Mandatory Control Classes

Every γ claim MUST report results for all five classes. Any class that
is omitted MUST be justified in writing in the PR or manuscript method,
and the claim MUST be marked as not yet adversarially validated.

### 4.1 Randomization / surrogate controls

Required surrogates (at minimum):

- Temporal shuffle of the relevant time axis.
- Circular shift of the time series.
- Phase randomization (Fourier amplitude preserved, phases scrambled).
- Matched-noise surrogate (Gaussian with matched first and second
  moments; in frequency domain, equivalent colored noise where stated).

**Rule.** If γ remains near the reported value after a
structure-destroying surrogate, the result is **artifactual until proven
otherwise**. Report the surrogate γ distribution alongside the observed γ
with a permutation p-value.

### 4.2 Model / mechanism perturbation controls

Required perturbations target the mechanism the γ claim is being
interpreted through. Examples:

- Weaken or remove coupling.
- Remove or freeze homeostatic plasticity.
- Remove sensorimotor or feedback coupling.
- Suppress long-range interactions.

**Rule.** If the proposed mechanism is removed and γ does not materially
change, the **mechanism claim fails**. The γ value may still hold as a
descriptive marker, but the mechanistic interpretation is retracted.

Aguilera et al. (2015) is the operational precedent for this class:
1/f structure in the minimal neurorobotic model collapsed under removal
of any of the three joint conditions.

### 4.3 Parameter sweep controls

Vary at least four axes (choose those relevant to the substrate):

- System size (network size, grid size, agent count).
- Noise amplitude.
- Coupling strength.
- Recurrence depth / integration horizon.

**Rule.** γ claims MUST report whether the effect is robust (survives a
broad range), peaked (appears in a narrow window), monotonic, or fragile.
If γ ≈ 1 only appears under narrow accidental tuning, that MUST be
reported explicitly and the claim downgraded from "regime marker" to
"conditional observation".

### 4.4 Counter-model controls

Required counter-models (at minimum one non-trivial counter-model per
claim):

- Feedforward baseline (same size, no recurrence).
- Linear oscillator surrogate (same spectral energy, no nonlinear
  coupling).
- Decoupled network (same units, zero or randomised connectivity).
- Non-adaptive baseline (same dynamics, plasticity frozen).

**Rule.** If a non-critical or interaction-poor counter-model produces
the same γ under the same analysis pipeline, the interpretation is
**invalidated or weakened**. The γ value then measures the pipeline, not
the substrate.

### 4.5 Cross-level consistency checks

At least two of:

- Coarse-graining sensitivity (re-bin time or space; report γ at each
  scale).
- Channel / unit shuffling (destroy anatomical or graph identity while
  preserving marginals).
- Spatial or graph reindexing.
- Re-estimation under an alternate preprocessing pipeline (different
  filter, detrending, normalization).

**Rule.** If the claimed scale-free signature **collapses under
reasonable representational changes**, the bridge claim is weakened. If
it reverses sign or verdict, the bridge claim is refuted.

## 5. Alternative Explanations That Must Be Ruled Out

Each γ claim MUST explicitly address each of the following. "Not
applicable" is a valid answer if justified; silence is not.

### 5.1 Linear superposition / external colored drive

- **What it is.** 1/f-like output from a linear system driven by
  1/f-like input, or from mixing multiple independent oscillators with a
  broad timescale distribution.
- **Why it can fake γ ≈ 1.** No criticality is required — any sum of
  Lorentzians with a broad τ distribution produces 1/f behaviour.
- **Concrete test.** Run the same analysis on a linear counter-model
  driven by the same exogenous input. If γ matches, the criticality
  interpretation fails.

### 5.2 Hidden parameter tuning

- **What it is.** The observed γ is the outcome of an implicit search
  over hyperparameters, seeds, time windows, or fit ranges.
- **Why it can fake γ ≈ 1.** Selection bias on the reporting side.
- **Concrete test.** Preregister the parameter set, the seed pool, and
  the fit window before running. Report the full sweep, not the best
  cell. Audit against the preregistration commit SHA
  (`evidence/PREREG.md`).

### 5.3 Preprocessing or normalization artifacts

- **What it is.** Detrending, filtering, windowing, z-scoring, or
  spectrum estimation choices that bias the slope toward −1.
- **Why it can fake γ ≈ 1.** Many standard pipelines impose or hide
  1/f-like structure; Welch windowing, high-pass filtering, and
  aggressive detrending are classic offenders.
- **Concrete test.** Re-estimate γ under at least two alternate
  preprocessing pipelines. Report all resulting γ values, not just the
  pipeline that produced γ ≈ 1.

### 5.4 Intrinsic oscillatory confounds

- **What it is.** Narrow-band oscillations or quasi-periodic dynamics
  that, together with measurement noise, produce an apparent power-law
  slope over a limited frequency range.
- **Why it can fake γ ≈ 1.** Peaks at the edges of the fit window bias
  the regression.
- **Concrete test.** Report the fit range explicitly. Show the full
  spectrum. Fit over at least two non-overlapping decades where
  possible; if that is not possible, report the claim as "limited
  scaling range" and downgrade the interpretation accordingly.

### 5.5 Thermodynamic or non-SOC explanations

- **What it is.** Power-law-like behaviour produced by finite-size
  effects, thermal fluctuations, diffusion-limited processes, or
  equilibrium statistical mechanics without any self-organised critical
  mechanism.
- **Why it can fake γ ≈ 1.** Non-critical systems can sit near power-law
  regimes purely from boundary or finite-size scaling.
- **Concrete test.** Vary system size and report the scaling of the
  finite-size cutoff. A genuine SOC signature shows characteristic
  size-dependence; a thermodynamic confound does not.

## 6. Minimum Reporting Requirements for Any γ Claim

Every row, figure, table, or sentence in this repository that reports or
relies on a γ value MUST disclose:

- Substrate.
- Task or behavioural context.
- Preprocessing pipeline (each step, each parameter).
- γ estimation method (Theil–Sen / least-squares / DFA / MLE / etc.).
- Fit range, frequency range, or scaling window.
- Sample size or number of independent runs.
- Uncertainty estimate (bootstrap CI, SE, permutation distribution).
- Surrogate controls run (Section 4.1) and their outcomes.
- Perturbation controls run (Section 4.2) and their outcomes.
- Counter-models tested (Section 4.4) and their γ.
- Explicit treatment of each alternative explanation in Section 5.
- A clear separation between regime claims (H / C / γ) and productivity
  or capability claims (see `evidence/levin_bridge/hypotheses.yaml`
  contract v2; productivity claims require `P_status == "defined"`).

Reports that omit any of the above are provisional and MUST NOT feed
downstream claims.

## 7. What Invalidates or Weakens a γ Claim

The claim is invalidated or weakened if **any** of the following holds:

- γ ≈ 1 persists after at least one structure-destroying surrogate from
  Section 4.1.
- γ ≈ 1 appears equally in a null or non-adaptive counter-model from
  Section 4.4 under the same pipeline.
- The effect disappears or reverses under a modest preprocessing change
  (Section 5.3).
- No uncertainty estimate is reported (Section 6).
- The claim relies on a single metric or a single seed with no
  adversarial checks.
- The interpretation jumps from correlation to mechanism, or from
  mechanism to law, without the corresponding perturbation controls
  (Section 4.2) having been run and reported.
- A trivial linear superposition, external drive, or hidden-tuning
  alternative (Section 5.1–5.2) explains the observation equally well.

Each of these is a **first-class falsification event**. Counter-evidence
is not an inconvenient exception; it is the positive result that was
asked for. Record the outcome in the verdict file alongside the claim it
refutes.

## 8. Interpretation Boundary

Within this repository:

- γ is a **candidate regime marker**. It is never, on its own,
  evidence of intelligence, cognition, agency, or universal criticality.
- Biological and neurorobotic precedents justify studying γ as a
  cross-substrate hypothesis. They do not transfer any conclusion to
  software, LLM, or non-biological substrates without independent
  adversarial validation on that substrate.
- Counterexamples (γ ≉ 1 in otherwise structurally similar systems; γ ≈
  1 in trivial counter-models) are load-bearing results, not outliers to
  be smoothed over. They enter the ledger with equal status to
  supporting observations.

## 9. Closing Constraint

- Analogies are not evidence.
- 1/f is not mystical by default; broad-timescale mixtures produce it
  without any criticality.
- Protocol, replication, controls, and explicit failure modes are
  mandatory, not optional.
- This document constrains **interpretation**, not just analysis. A
  correct number interpreted outside these bounds is a violation of the
  repository's canon discipline.

## Sources (verified)

- Hengen KB, Shew WL, et al. *Is criticality a unified setpoint of brain
  function?* Neuron, 2025. PMID 40555236. DOI via
  <https://www.cell.com/neuron/fulltext/S0896-6273(25)00391-5>.
- Aguilera M, Bedia MG, Santos BA, Barandiaran XE. *Self-Organized
  Criticality, Plasticity and Sensorimotor Coupling. Explorations with a
  Neurorobotic Model in a Behavioural Preference Task.* PLoS ONE
  10(2):e0117465, 2015.
  <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0117465>.
