# Replication Protocol — Independent Validation of γ Claims

> Protocol-layer document. **Not canon. Not literature review.**
> Defines the multi-scale independent-replication protocol that any
> γ-related claim in this repository MUST meet before it is admitted
> as cross-substrate evidence. Grounded only in verified primary
> sources (see §9). Pairs with `docs/ADVERSARIAL_CONTROLS.md`: that
> document governs what counts as an admissible claim; this document
> governs how an admissible claim is independently validated.

## 1. Purpose

Specify the procedural requirements for independent replication of
γ-related claims, separated by substrate class. Replication under this
protocol is a precondition for any claim to survive heterogeneity
(see `docs/protocols/levin_bridge_protocol.md` Step 9) and for any
interpretation that generalises beyond a single dataset or model.

## 2. Scope

Applies to every γ-related observation, mechanism claim, or regime-marker
assertion produced inside or cited by this repository. Non-replicated
claims remain at the original-observation tier and MUST NOT be used to
support cross-substrate generalisations.

Three substrate classes are covered here:

- **In vivo CNS** (§4) — electrophysiological or imaging data from
  intact nervous systems.
- **Neuronal cultures** (§5) — population-activity recordings from
  in vitro neuronal preparations, typically analysed via avalanche
  statistics.
- **Simulated agents** (§6) — embodied or recurrent computational
  models, including Izhikevich-type rich-club networks and minimal
  neurorobotic systems.

Other substrate classes (reaction-diffusion, Kuramoto, LLM multi-agent)
are covered by their own preregistered protocols; this document does
not extend to them except by general principle (§3).

## 3. General Principles

- **Preregistration is required.** The analysis pipeline, the fit
  window, the estimator, the sample-size floor, and the interpretation
  boundary MUST be filed (commit SHA, `evidence/PREREG.md`) before the
  data that will decide the claim are analysed.
- **Robust fitting is required.** Theil–Sen with bootstrap CI, MLE with
  goodness-of-fit tests, or DFA with explicit scaling-range gates —
  never single-point OLS without uncertainty.
- **Explicit failure criteria are required.** Each replication MUST
  carry a written kill criterion such that a defined outcome could
  unambiguously falsify the primary claim.
- **Independent replication is preferred.** Replication by the same
  group using the same dataset is weaker than replication by an
  independent group on an independent dataset. The meta-analysis
  design in Hengen & Shew (2025) across ~140 datasets is the strongest
  available precedent; single-lab replication is weaker and MUST be
  labelled as such.
- **Counterexamples update the theory, not the footnotes.** A replication
  that returns γ ≉ 1 under the same protocol is a first-class result.
  It enters the ledger with equal status to a confirming replication
  and constrains every subsequent claim in the same substrate class.
- **P is optional and substrate-specific.** No replication protocol
  below requires a numeric `P` unless the substrate has a preregistered
  productivity contract (see `evidence/levin_bridge/hypotheses.yaml`
  contract v2). Rows with `P_status ∈ {not_defined, preregistered_pending}`
  are VALID for regime-level replication and MUST NOT be excluded on
  that basis.

## 4. Protocol: In Vivo CNS

Grounded in Hengen & Shew (2025, *Neuron*): the meta-analysis design
across ~140 datasets (2003–2024) is the operational precedent for
cross-dataset replication of γ claims in intact neural systems.

### 4.1 Sample-size floor / minimum replication expectation

- Minimum `n ≥ 3` independent datasets from independent preparations,
  subjects, or recording sessions for a within-lab replication claim.
- Cross-lab replication preferred: `n ≥ 2` independent datasets from
  at least two labs for any claim that generalises beyond a single
  preparation type.
- Historical small-N precedents (`n < 10`) MUST NOT be used as the
  primary anchor. They MAY be cited as background.

### 4.2 Data collection expectations

- Electrophysiological recordings with preregistered sampling rate
  and channel count; imaging recordings with preregistered frame rate
  and ROI count.
- Behavioural / task state recorded concurrently where the claim is
  state-dependent.
- Raw data and analysis code archived to a persistent public location
  (DOI-backed repository) before the claim is reported.

### 4.3 Preprocessing requirements

- Every step of the preprocessing pipeline is listed in the
  preregistration (see §7).
- Re-estimation under at least one alternate preprocessing pipeline
  is mandatory (see `docs/ADVERSARIAL_CONTROLS.md §5.2`). The result
  of the alternate pipeline is reported alongside the primary.
- Non-stationarity is checked explicitly (split-run stability of the
  fit; stationarity test on residuals).

### 4.4 γ estimation requirements

- Method declared in the preregistration (Theil–Sen + bootstrap / DFA /
  MLE). The same method is applied to all datasets in the replication.
- Fit window (frequency range or time-scale range) declared in the
  preregistration. Scaling range ≥ one decade required to admit the
  estimate; less than one decade is reported as "limited scaling range"
  with downgraded interpretation.
- Uncertainty estimate (bootstrap CI, permutation distribution, analytic
  SE) reported for every dataset. No point estimate without uncertainty.

### 4.5 Control requirements

All five classes from `docs/ADVERSARIAL_CONTROLS.md §4` apply:

- §4.1 surrogate controls
- §4.2 connectivity / coupling perturbation controls (where
  pharmacological or stimulation-based perturbation is available;
  otherwise declared not applicable with justification)
- §4.3 parameter sweep (for dataset-level parameters under experimenter
  control)
- §4.4 counter-model controls (linear / decoupled / non-adaptive
  baselines run under the same pipeline)
- §4.5 cross-level consistency (coarse-graining, channel shuffle,
  alternate preprocessing)

### 4.6 Statistical validation requirements

- Between-dataset consistency: the γ values across replications are
  compared with a test appropriate to the sample size (paired, mixed-
  effects, or meta-analytic as relevant). Heterogeneity (I², τ²) is
  reported.
- A replication claim of support requires all datasets to yield
  γ-CIs whose lower bounds remain consistent with the claimed regime
  marker; a single dataset that does not is recorded as counter-evidence
  and reported alongside the supportive ones, not excluded.

### 4.7 Failure criteria

The in vivo CNS replication fails if any of the following holds:

- Fewer than the §4.1 sample-size floor is reached.
- γ does not survive structure-destroying surrogates in any dataset
  (`ADVERSARIAL_CONTROLS.md §7.1`).
- γ collapses or reverses under the mandatory alternate preprocessing.
- A counter-model reproduces the γ value under the same pipeline.
- Any of the twelve reporting fields (`ADVERSARIAL_CONTROLS.md §6`) is
  missing for any dataset in the replication set.

## 5. Protocol: Neuronal Cultures

No primary culture study is included among the three verified sources
of this document. This section specifies a minimum operational protocol
for culture-based replications WITHOUT endorsing any specific primary
culture study as canonical grounding; primary culture citations MUST
be added by the substrate owner in a separate PR that verifies them
against the `docs/ADVERSARIAL_CONTROLS.md §2` admissibility rules.

### 5.1 Avalanche or population-activity route

- Record multi-unit activity or LFP / imaging across a population of
  units sufficient to construct avalanche statistics (typical floor:
  ≥ 60 simultaneously recorded units; preregister the exact floor).
- Define an event threshold in the preregistration. Re-estimate under
  at least two alternate thresholds to expose threshold dependence.

### 5.2 Fitting requirements

- Avalanche size and duration distributions fit by maximum-likelihood
  with goodness-of-fit test against the alternative distributions
  (exponential, log-normal, truncated power-law). Power-law preference
  is admitted only when the likelihood-ratio is significant and the
  KS statistic is within the bootstrap distribution of the fitted
  power-law.
- Scaling relations (crackling-noise relation, shape collapse) reported
  alongside the marginal exponents; marginal exponents alone do not
  support a criticality interpretation.

### 5.3 Control requirements

All five adversarial-control classes (`docs/ADVERSARIAL_CONTROLS.md §4`).
Specific emphasis for cultures:

- Non-adaptive baseline (plasticity pharmacologically blocked) is
  mandatory where feasible; where not feasible, declared with
  justification.
- Matched-rate Poisson surrogate at the same firing-rate profile is
  mandatory under §4.1.

### 5.4 Validation requirements

- Replication across independent cultures (`n ≥ 3` cultures from
  independent dissections or differentiations) for any within-lab
  claim.
- Cross-lab replication preferred before generalisation beyond the
  specific preparation protocol.

### 5.5 Failure criteria

- Goodness-of-fit against alternative distributions is not performed,
  or the power-law is not preferred over alternatives.
- Avalanche exponents pass the marginal fit but fail the scaling
  relation or shape-collapse check.
- Poisson / matched-rate surrogate reproduces the exponents.
- Cross-culture heterogeneity shows the effect in one culture only.

## 6. Protocol: Simulated Agents

Grounded in Aguilera et al. (2015, *PLoS ONE*) — minimal embodied
neurorobotic system where 1/f-like structure emerges only under the
joint condition of nonlinear coupling, homeostatic plasticity, and
sensorimotor feedback; and Aguilar-Velázquez & Guzmán-Vargas (2019,
*Scientific Reports*) — Izhikevich-on-rich-club topology where 1/f and
critical synchronisation depend on specific E/I balance.

### 6.1 Setting

- **Embodied or recurrent.** The simulated agent MUST have either
  closed-loop sensorimotor coupling with an environment OR explicit
  internal recurrence with integration horizon preregistered.
- **Minimum architecture disclosure.** Coupling topology, plasticity
  rule, E/I ratio, and any external drive are reported explicitly.

### 6.2 Recording requirements

- Record unit-level or population-level activity at a sampling rate
  sufficient to resolve the claimed scaling range.
- Store enough run length to satisfy the §6.4 γ estimation scaling-range
  gate.
- Seed, commit SHA, and full config are persisted alongside the data.

### 6.3 γ estimation requirements

- Identical to §4.4 (preregistered method, ≥ 1 decade, uncertainty).

### 6.4 Perturbation requirements

Mandatory, grounded in Aguilera et al. (2015):

- Remove or freeze homeostatic plasticity; re-estimate γ.
- Decouple the network or disable sensorimotor feedback; re-estimate γ.
- Replace nonlinear coupling with a linear surrogate of matched
  spectral energy; re-estimate γ.

Each perturbation is reported with its γ and CI. The primary
interpretation is admissible only if at least one perturbation
materially degrades γ (see `docs/ADVERSARIAL_CONTROLS.md §4.2`).

### 6.5 Parameter sweep requirements

Mandatory, grounded in Aguilar-Velázquez & Guzmán-Vargas (2019):

- E/I ratio sweep (where applicable to the model class).
- Coupling strength sweep.
- Network size sweep.
- Integration horizon or recurrence depth sweep.

γ is reported across the full sweep. Claims that γ ≈ 1 only inside a
narrow window MUST report that window explicitly and downgrade the
interpretation accordingly.

### 6.6 Failure criteria

- γ survives the mandatory mechanism perturbations without material
  change.
- γ ≈ 1 appears only in a narrow accidental-tuning window of the
  parameter sweep and that fact is not disclosed.
- A linear counter-model with matched spectral energy reproduces the
  γ under the same pipeline.
- Cross-seed variance across replications is so large that the γ
  point estimate is indistinguishable from the null.
- Reporting omits any of the twelve fields of
  `docs/ADVERSARIAL_CONTROLS.md §6`.

## 7. Preregistration Template

Every γ-related replication PR MUST file the following block in a
versioned location (e.g. `evidence/PREREG.md` append-only, or the
substrate's canonical hypotheses yaml), with the commit SHA at which
the preregistration was recorded.

```yaml
prereg:
  hypothesis: >-
    One sentence. What is the γ claim, in its minimum admissible form?
  data_collection_plan:
    substrate_class: <in_vivo_cns | neuronal_culture | simulated_agent>
    sample_size_floor: <integer>
    independence_structure: >-
      How are replications independent? (independent subjects, cultures,
      seeds, labs.)
    source: >-
      Where the data come from (public DOI, lab, simulator + commit SHA).
  preprocessing:
    pipeline_steps:
      - <step 1 with parameters>
      - <step 2 with parameters>
    alternate_pipeline:
      - <at least one alternate for the §5.2 cross-check>
    stationarity_check: <method and threshold>
  analysis_pipeline:
    estimator: <theil_sen | mle | dfa | other>
    fit_window: <frequency or time-scale range>
    scaling_range_gate: <minimum decades required>
    uncertainty_method: <bootstrap_n_boot | permutation | analytic_se>
  primary_metric:
    name: gamma
    claim_regime: <candidate_marker | bounded_observation | mechanism_claim>
    claim_scope: <one sentence, minimum admissible language>
  controls:
    surrogate_families: [temporal_shuffle, circular_shift, phase_randomization, matched_noise]
    perturbation_set: [<mechanism-targeted perturbations>]
    counter_models: [<feedforward | linear_oscillator | decoupled | non_adaptive>]
    cross_level_checks: [<coarse_graining | channel_shuffle | reindex | alternate_preprocessing>]
  statistics:
    primary_test: <name + two-sided alpha>
    multiple_comparisons_control: <method>
    heterogeneity_reporting: <I_squared + tau_squared, for cross-dataset>
  sample_size_justification: >-
    Power analysis or precedent-based justification for the chosen n.
  replication_plan:
    within_lab: <n>
    cross_lab: <n or not_planned_with_reason>
  interpretation_boundary: >-
    Explicit sentence stating what this replication does NOT license
    if it succeeds (e.g. "does not license generalisation beyond the
    preparation class under test; does not license any productivity
    claim unless P_status == defined").
  P_status: <defined | not_defined | preregistered_pending>
  commit_sha: <SHA at filing>
```

## 8. Decision Rules

Three separate outcomes are defined. Each replication PR MUST report
exactly one of them, with the evidence that supports the choice.

### 8.1 Support

All of the following hold:

- Sample-size floor met (§4.1 / §5.4 / §6.5 as applicable).
- Every mandatory control class (`ADVERSARIAL_CONTROLS.md §4`) passed
  under the pass criteria declared there.
- γ-CIs across replications are consistent with the preregistered claim
  regime.
- All twelve reporting fields (`ADVERSARIAL_CONTROLS.md §6`) disclosed.
- No failure criterion (`ADVERSARIAL_CONTROLS.md §7`) triggered.

Outcome: the claim is admitted at the preregistered claim-regime tier
(candidate marker / bounded observation / mechanism claim). It is NOT
automatically promoted to a stronger tier; promotion requires an
additional replication PR that explicitly tests the stronger claim.

### 8.2 Falsification

Any of the following holds:

- A failure criterion from `ADVERSARIAL_CONTROLS.md §7` is triggered.
- A counter-model reproduces the observed γ under the same pipeline.
- A mandatory perturbation (§4.2) does not materially change γ when
  the claim asserts a mechanism.
- γ collapses or reverses under an alternate preprocessing pipeline.

Outcome: the claim is rejected at the tier tested. The result is
recorded in the ledger with equal weight as a supportive replication.
Subsequent claims in the same substrate class MUST cite this
falsification.

### 8.3 Theory revision

If multiple replications produce mixed support/falsification across
substrate classes or within one substrate under parameter-sweep
inspection, the claim is revised, not retained. Revision options:

- Narrow the claim's scope to the conditions where replication
  supports it (e.g. specific E/I-balance window per Aguilar-Velázquez
  & Guzmán-Vargas 2019; specific joint mechanism per Aguilera et al.
  2015; specific behavioural-state window per Hengen & Shew 2025).
- Demote the claim tier (mechanism → bounded observation, or bounded
  observation → candidate marker).
- Retract the claim if no bounded scope survives.

Theory revisions are filed as named PRs that update the canonical
claim text (e.g. `CANONICAL_POSITION.md`, relevant hypotheses yaml)
with the replication SHAs that forced the revision. Revisions are
auditable, not rewritable.

## 9. Interpretation Boundary

- **Replication does not prove universality.** A claim replicated on
  `n` datasets is supported in the region of substrate space those
  datasets occupy, not beyond it. Hengen & Shew (2025) explicitly
  frames criticality as a meaningful set point *across the datasets
  analysed*, not as a law.
- **γ ≈ 1 is not sufficient by itself.** The scaling exponent alone
  does not establish criticality; scaling relations, shape collapse,
  and mechanism-perturbation evidence are required before a criticality
  interpretation is admissible (§5.2).
- **P cannot be assumed.** A replication succeeds at the regime level
  (H / C / γ) without a numeric P, but it MUST NOT feed any productivity
  claim unless the substrate's `P_status == "defined"` per
  `evidence/levin_bridge/hypotheses.yaml` contract v2.
- **Cross-substrate inference requires cross-substrate replication.**
  A supportive replication on in vivo CNS data does not license a
  claim about simulated agents, and vice versa. Each substrate class
  carries its own replication requirements (§4 / §5 / §6).
- **Counterexamples are evidence.** A falsifying replication is not a
  footnote; it is a first-class constraint on every subsequent claim
  in the same substrate class.

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
