# Adversarial Controls — Protocol Constraints for γ Claims

> Protocol-layer constraints document. **Not canon. Not literature review.**
> Governs the generation, validation, and reporting of every γ-related
> claim in this repository. Grounded only in verified primary sources
> (see §2).

## 1. Purpose

Convert the verified evidence on 1/f-like scaling into an operational
adversarial-control and falsification specification. Every γ-related
experiment, PR, and manuscript method in this repository MUST satisfy
the controls in §4 and the reporting contract in §6 before any
interpretive claim is admissible.

## 2. Scope

Applies to every artefact that reports, derives, or depends on a value
of γ, a 1/f-like spectral exponent, a DFA exponent, an avalanche
exponent, or any equivalent scale-free signature. Applies regardless of
substrate: neural, neurorobotic, reaction-diffusion, Kuramoto, or any
future addition.

**Admissible grounding:** exactly three primary sources (see §10 for
full citations).

- **Hengen & Shew (2025, *Neuron*)** — meta-analysis of ~140 datasets
  (2003–2024) framing criticality as a multiscale **set point** of
  healthy brain function. Used only to support the bounded claim that
  γ ≈ 1 is a meaningful candidate regime marker *in healthy neural
  systems under suitable conditions*, not as proof of universality.
- **Aguilera et al. (2015, *PLoS ONE*)** — neurorobotic model in which
  robust 1/f-like structure arises **only** under the conjunction of
  nonlinear coupling, homeostatic plasticity, and sensorimotor feedback;
  a decoupled condition can produce a misleading 1/f spectrum without
  multifractality. Used to ground perturbation controls (§4.2) and the
  cross-level consistency requirement (§4.5).
- **Aguilar-Velázquez & Guzmán-Vargas (2019, *Scientific Reports*)** —
  Izhikevich-on-rich-club-topology simulation linking 1/f dynamics and
  critical synchronisation to specific excitatory/inhibitory balance
  regimes. Used only for the bounded claim that 1/f structure is
  observed under specific E/I-balanced network conditions, not as
  evidence of a universal criticality law.

**Inadmissible grounding.** Small-N historical precedents (`n < 10`)
may be cited as background but MUST NOT serve as primary anchors for
any repository-level γ claim. Unverified citations of any form are
forbidden — including author-year references that cannot be resolved
to a published primary source.

## 3. Core Rule

γ ≈ 1 is a **candidate regime marker**. It is never, on its own,
evidence of criticality, cognition, agency, intelligence, or any
universal law. Every γ-related claim in this repository MUST pass the
adversarial controls in §4 and the reporting contract in §6 before it
is interpreted.

A γ value with no adversarial control is a number, not evidence.

## 4. Mandatory Control Classes

All five classes are required. Any class omitted MUST be justified in
writing in the PR or manuscript method, and the claim MUST be marked as
not yet adversarially validated.

### 4.1 Randomization / surrogate controls

- **Definition.** Re-estimate γ on versions of the data in which
  temporal or graph structure has been explicitly destroyed while
  preserving specified marginals. Minimum surrogate set: temporal
  shuffle, circular shift, phase randomisation (amplitude-preserved,
  phase-scrambled), matched-noise surrogate (Gaussian with matched
  first and second moments).
- **Why it matters.** Any γ value produced by a structure-destroying
  surrogate that matches the observed γ indicates that the effect is
  driven by marginals or pipeline-imposed bias, not by the substrate's
  organisation.
- **Pass criterion.** Observed γ lies outside the two-sided 95 %
  surrogate distribution for every surrogate family used (equivalently,
  permutation p < 0.05 against each family).
- **Fail criterion.** Observed γ falls within the surrogate
  distribution for any one family. The result is artefactual until
  proven otherwise; the substrate-level interpretation is retracted.

### 4.2 Connectivity / coupling perturbation controls

- **Definition.** Re-estimate γ after mechanism-targeted perturbations
  of the system whose γ is claimed: weaken or remove coupling, remove
  or freeze homeostatic plasticity, remove or disable sensorimotor /
  feedback coupling, suppress long-range interactions. Grounded in
  Aguilera et al. (2015): the 1/f signature in the minimal neurorobotic
  model collapses under removal of any of the three joint conditions
  (nonlinear coupling, plasticity, sensorimotor feedback).
- **Why it matters.** A γ value that does not depend on the proposed
  mechanism cannot support a mechanistic interpretation of that γ.
- **Pass criterion.** Removing the claimed mechanism materially
  degrades γ (confidence intervals separated from the unperturbed
  value) or eliminates the scale-free signature.
- **Fail criterion.** γ is preserved under removal of the claimed
  mechanism. The mechanism claim is retracted; the γ value may still
  hold as a descriptive marker.

### 4.3 Parameter sweep controls

- **Definition.** Vary at least four axes of the substrate's
  parameter space while holding the task family fixed. Minimum axes:
  system size (network / grid / agent count), noise amplitude, coupling
  strength, integration horizon or recurrence depth.
- **Why it matters.** γ claims must disclose whether the effect is
  robust (survives a broad range), peaked (appears in a narrow window),
  monotonic, or fragile. Aguilar-Velázquez & Guzmán-Vargas (2019) shows
  that 1/f structure and critical synchronisation appear under specific
  E/I balance regimes, not universally across topology and coupling.
- **Pass criterion.** γ claim is classified and reported as robust,
  peaked, monotonic, or fragile, with the explicit parameter-space
  range over which it holds. Narrow tuning is reported as such;
  downgrade of the interpretation is automatic when the window is
  narrow.
- **Fail criterion.** γ ≈ 1 appears only under accidental tuning and
  the tuning is not disclosed; or the sweep is incomplete on any of the
  four minimum axes without justification.

### 4.4 Counter-model controls

- **Definition.** Re-run the same analysis pipeline on at least one
  non-critical counter-model per claim. Minimum repertoire: feedforward
  baseline (same size, no recurrence), linear oscillator surrogate
  (same spectral energy, no nonlinear coupling), decoupled network
  (same units, zero or randomised connectivity), non-adaptive baseline
  (same dynamics, plasticity frozen).
- **Why it matters.** If a non-critical or interaction-poor model
  yields the same γ under the same pipeline, the γ measures the
  pipeline, not the substrate.
- **Pass criterion.** Every counter-model tested produces a γ that is
  statistically distinguishable from the observed value, or fails the
  scaling-range / r² gates that the primary claim satisfies.
- **Fail criterion.** Any counter-model reproduces the observed γ
  under the same pipeline. The interpretation is invalidated or
  weakened accordingly.

### 4.5 Cross-level consistency checks

- **Definition.** Re-estimate γ under representational changes that
  preserve the substrate's information but alter its surface form:
  coarse-graining (re-bin time or space), channel / unit shuffling
  (destroy anatomical or graph identity while preserving marginals),
  spatial or graph reindexing, re-estimation under at least one
  alternate preprocessing pipeline. Grounded in Aguilera et al. (2015):
  the decoupled condition can produce a 1/f-like spectrum that fails
  multifractal consistency, i.e. the scale-free signature does not
  survive finer-grained analyses.
- **Why it matters.** A genuine scale-free signature should survive
  reasonable representational changes; one that does not is a pipeline
  artefact or a misclassified noise family.
- **Pass criterion.** γ remains within the reported confidence
  interval under at least two independent representational changes,
  and higher-moment checks (e.g. multifractal spectrum width, DFA
  across alternate windows) are consistent with the primary estimate.
- **Fail criterion.** γ collapses, reverses sign, or fails the higher-
  moment consistency check under any reasonable representational
  change. The bridge-level claim is weakened; if the sign or verdict
  reverses, the claim is refuted.

## 5. Alternative Explanations That Must Be Ruled Out

Each γ claim MUST explicitly address each of the following items.
"Not applicable" is a valid answer only if justified in the method
section; silence is not.

### 5.1 Linear superposition / external drive

- **What it is.** 1/f-like output from a linear system driven by
  1/f-like input, or from the mixture of many independent Lorentzian
  processes with a broad timescale distribution.
- **Why it can fake γ ≈ 1.** No criticality is required; any broad
  mixture of relaxation times produces 1/f-like behaviour.
- **Concrete test.** Run the full analysis pipeline on a linear
  counter-model driven by the same exogenous input or with a matched
  broad-τ mixture. If γ matches the primary result, the criticality
  interpretation fails.

### 5.2 Non-stationarity / preprocessing artefacts

- **What it is.** Drift, piecewise stationarity, windowing choices,
  detrending, filtering, z-scoring, spectrum-estimation settings, or
  window length — any preprocessing step that can bias the slope
  toward −1 or manufacture scaling behaviour.
- **Why it can fake γ ≈ 1.** Many standard pipelines (Welch with
  specific windows, aggressive detrending, high-pass filtering) impose
  or hide 1/f-like structure; non-stationary data fit inside a moving
  window can appear scale-free at that window.
- **Concrete test.** Re-estimate γ under at least two alternate
  preprocessing pipelines AND under stationarity checks (e.g. split-run
  stability of the fit; KPSS or ADF on the residuals). Report every γ
  produced, not only the pipeline that yields γ ≈ 1.

### 5.3 Plasticity-only explanation

- **What it is.** 1/f-like structure produced solely by the rules of a
  homeostatic or plasticity mechanism acting on otherwise trivial
  dynamics, without any coordinated or critical interaction structure.
- **Why it can fake γ ≈ 1.** Plasticity-driven drift of unit gains or
  rates alone can generate slow-timescale variance that mimics
  broadband 1/f.
- **Concrete test.** Freeze plasticity while preserving coupling and
  input statistics; re-estimate γ. If γ ≈ 1 persists, plasticity is not
  the operating cause. If γ ≈ 1 disappears, plasticity *is* necessary
  but sufficiency for a criticality interpretation is not established
  and MUST be separately tested (see §4.2, grounded in Aguilera et al.
  2015: the 1/f signature requires the joint condition of coupling,
  plasticity, AND sensorimotor feedback, not plasticity alone).

### 5.4 Wrong noise-family classification

- **What it is.** A time series classified as 1/f (pink) when it is
  actually white noise contaminated by a narrow-band confound, or
  Brownian-like (β ≈ 2) with a limited analysis window that crops to an
  intermediate slope.
- **Why it can fake γ ≈ 1.** A Brownian process analysed over a
  restricted frequency band can return a slope near −1 purely from
  window-cropping; a white-plus-oscillation process can be mis-fit as
  1/f if the oscillation is not removed.
- **Concrete test.** Fit γ over at least two non-overlapping decades
  where data permit; plot the full spectrum; run DFA and spectral
  estimation independently and compare exponents against the expected
  white / pink / Brownian bounds. Declare the noise family explicitly.
  If scaling range is less than one decade, label the claim as
  "limited scaling range" and downgrade the interpretation.

### 5.5 Hidden parameter tuning

- **What it is.** The reported γ is the outcome of an implicit search
  over hyperparameters, seeds, time windows, or fit ranges; only the
  run that produced γ ≈ 1 reaches the report.
- **Why it can fake γ ≈ 1.** Selection bias on the reporting side.
- **Concrete test.** Preregister the parameter set, seed pool, and fit
  window before running (see `docs/REPLICATION_PROTOCOL.md §7`).
  Report the full sweep distribution, not the best cell. Audit the
  primary report against the preregistration commit SHA per
  `evidence/PREREG.md` conventions.

## 6. Minimum Reporting Requirements

Every γ-related result in this repository MUST disclose **all twelve**
of the following. Omissions are treated as failure criteria (§7).

1. **Substrate** — which system (neural dataset, neurorobotic model,
   simulated substrate, etc.).
2. **Task or behavioural context** — what the system is doing during
   measurement.
3. **Preprocessing pipeline** — every step, every parameter.
4. **Estimation method** — Theil–Sen / OLS / DFA / MLE / other, with
   the exact implementation used.
5. **Scaling or fit window** — frequency range, time-scale range, or
   σ range used for the power-law fit, with the r² and the scaling
   decades spanned.
6. **Sample size or run count** — number of independent runs, trials,
   subjects, datasets.
7. **Uncertainty estimate or confidence interval** — bootstrap CI,
   permutation distribution, or analytic SE. Lack of uncertainty is a
   failure criterion (§7.4).
8. **Surrogate controls used** — which of §4.1 families, with their
   γ distributions and permutation p-values.
9. **Perturbation controls used** — which of §4.2 perturbations, with
   the γ change under each.
10. **Counter-models tested** — which of §4.4 counter-models, with their
    γ under the same pipeline.
11. **Interpretation scope** — the minimum claim language consistent
    with the evidence (candidate regime marker / bounded observation /
    mechanism claim), NOT the maximum claim language.
12. **P-status or productivity-claim status** — explicit
    `P_status ∈ {defined, not_defined, preregistered_pending}` per
    `evidence/levin_bridge/hypotheses.yaml` contract v2. Productivity
    claims are admissible ONLY for `P_status == "defined"`.

Reports that omit any of these twelve fields are provisional and MUST
NOT feed downstream claims.

## 7. Failure Criteria

The claim is invalidated or weakened if **any** of the following seven
events holds. Each event is a first-class falsification, not an
inconvenient exception.

1. **Structure-destroying shuffle persistence.** γ ≈ 1 persists after
   at least one surrogate from §4.1 — pass criterion of §4.1 violated.
2. **Null-control equivalence.** γ ≈ 1 appears equally in a null or
   non-adaptive counter-model from §4.4 under the same pipeline.
3. **Preprocessing fragility.** The effect collapses, reverses, or
   fails the scaling-range gate under a modest preprocessing change
   from §5.2.
4. **No uncertainty estimate.** A γ value is reported without bootstrap
   CI, permutation distribution, or analytic SE. Unquantified γ is not
   admissible evidence.
5. **Correlation-to-mechanism jump.** The interpretation asserts a
   mechanism from correlation alone, without the §4.2 perturbation
   controls having been run and reported.
6. **Mechanism-to-law jump.** The interpretation elevates a
   mechanistic finding on one substrate to a universal law, without
   independent replication across substrates per
   `docs/REPLICATION_PROTOCOL.md`.
7. **Trivial-alternative equivalence.** A linear-superposition,
   external-drive, or hidden-tuning alternative (§5.1, §5.5) explains
   the observation equally well. The primary interpretation is
   indistinguishable from the null.

## 8. Interpretation Boundary

Within this repository, the following statements are **not** admissible
under this protocol:

- "γ ≈ 1 proves criticality / cognition / intelligence / agency."
- "γ ≈ 1 is a universal regime marker across substrates."
- "The 1/f signature observed here is sufficient evidence of
  self-organised criticality."
- "Because the biological literature shows γ ≈ 1 in some healthy
  neural systems, γ ≈ 1 in a software / LLM / non-biological substrate
  inherits the same interpretation."
- Any statement that cites γ ≈ 1 as primary evidence for a
  productivity or capability claim when the corresponding row's
  `P_status ≠ "defined"`.
- Any statement that elevates bounded observations from Hengen & Shew
  (2025), Aguilera et al. (2015), or Aguilar-Velázquez & Guzmán-Vargas
  (2019) into universal claims beyond the conditions those papers
  actually measured.

Counterexamples (γ ≉ 1 in structurally similar systems; γ ≈ 1 in
trivial counter-models) are load-bearing results, not outliers. They
enter the ledger with equal status to supporting observations.

## 9. Closing Constraint

- Analogies are not evidence.
- 1/f is not mystical by default — broad-timescale mixtures, Brownian
  window-cropping, and preprocessing choices all produce 1/f-like
  behaviour without any criticality.
- Replication, controls, and explicit failure modes are mandatory, not
  optional.
- This document constrains **interpretation**, not just analysis. A
  correct γ value interpreted outside these bounds is a violation of
  the repository's canon discipline.

## 10. Sources (verified primary)

- **Hengen KB, Shew WL, et al.** *Is criticality a unified setpoint of
  brain function?* Neuron, 2025. PMID 40555236.
  <https://www.cell.com/neuron/fulltext/S0896-6273(25)00391-5>
- **Aguilera M, Bedia MG, Santos BA, Barandiaran XE.** *Self-Organized
  Criticality, Plasticity and Sensorimotor Coupling. Explorations with a
  Neurorobotic Model in a Behavioural Preference Task.* PLoS ONE
  10(2):e0117465, 2015.
  <https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0117465>
- **Aguilar-Velázquez D, Guzmán-Vargas L.** *Critical synchronization and
  1/f noise in inhibitory/excitatory rich-club neural networks.*
  Scientific Reports 9:1258, 2019. DOI 10.1038/s41598-018-37920-w.
  <https://www.nature.com/articles/s41598-018-37920-w>
