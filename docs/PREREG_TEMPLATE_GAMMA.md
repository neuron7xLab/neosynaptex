# γ-Measurement Preregistration Template — v1.0

> **Authority.** γ-program Phase III §Step 13.
> **Base.** Royal Society Open Science preregistration template for
> cognitive model application (DOI `10.1098/rsos.210155`), extended
> with NeoSynaptex γ-specific fields.
> **Status.** Canonical. Every γ-measurement on every substrate in
> the evidential lane MUST file a prereg derived from this template.
> **Pair.** `docs/CLAIM_BOUNDARY.md`,
> `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`,
> `docs/MEASUREMENT_METHOD_HIERARCHY.md`,
> `docs/NULL_MODEL_HIERARCHY.md`.

## Usage

Copy this file to `evidence/replications/<substrate>/prereg.yaml`,
populate every field, and file the prereg on OSF. The entry in
`evidence/replications/registry.yaml` must cite the OSF DOI and
the commit SHA at which this prereg was frozen. A single byte
change after OSF filing invalidates the prereg — any drift
requires a new version.

---

```yaml
# Prereg — NeoSynaptex γ-measurement — {substrate_id}

prereg_version: 1
prereg_filed_date: YYYY-MM-DD
osf_doi: 10.17605/OSF.IO/...
commit_sha_at_filing: <40-hex>
substrate_id: <entry id in docs/SUBSTRATE_MEASUREMENT_TABLE.yaml>

# -------------------------------------------------------------------
# Section 1 — Hypothesis and claim
# -------------------------------------------------------------------

hypothesis:
  primary: >-
    One sentence. What γ value (or range) is predicted, in what
    substrate, under what preregistered conditions?
  claim_regime: one_of [candidate_marker, bounded_observation, mechanism_claim]
  claim_scope: >-
    One sentence, minimum-admissible form. Per CLAIM_BOUNDARY.md §3.
  relation_to_cross_substrate_claim: >-
    Does this prereg contribute to the CLAIM_BOUNDARY.md §3.2
    cross-substrate convergence claim? If yes, which of the six
    §5.1 gates does this prereg close?

# -------------------------------------------------------------------
# Section 2 — Data
# -------------------------------------------------------------------

data:
  source_type: one_of [public_bundle, private_bundle, synthetic]
  source_url: <URL or Zenodo/DANDI/OpenNeuro DOI>
  source_sha256: <hash of the frozen data bundle or download-time hash>
  unit_of_analysis: >-
    e.g. session / subject / trial / epoch / cell / spike / order-event /
    developmental stage / gene-stage pair
  independence_structure: >-
    How are units independent? (independent subjects, cells, seeds,
    stages, traders, order-books.)
  sample_size: <integer>
  sample_size_justification: >-
    Power analysis or precedent-based justification. Cite
    the paper that motivated the n.
  inclusion_criteria:
    - <criterion 1>
    - <criterion 2>
  exclusion_criteria:
    - <criterion 1>
    - <criterion 2>
  known_biases:
    - <bias 1>
    - <bias 2>

# -------------------------------------------------------------------
# Section 3 — Preprocessing
# -------------------------------------------------------------------

preprocessing:
  pipeline_steps:
    - <step 1 with parameters>
    - <step 2 with parameters>
  alternate_pipeline:
    - <at least one alternate preprocessing for §5.2 cross-check>
  stationarity_check: <method and threshold; e.g. ADF p<0.05>
  artefact_rejection: <method, thresholds>
  windowing: <window length, overlap, number of windows>

# -------------------------------------------------------------------
# Section 4 — Measurement method
# -------------------------------------------------------------------
# All methods MUST be drawn from docs/MEASUREMENT_METHOD_HIERARCHY.md
# and be declared as either primary, secondary, or reporting_only.

measurement:
  primary_aperiodic:
    tool: one_of [specparam, irasa]
    version: <semver>
    fit_range_hz: [<f_lo>, <f_hi>]
    excluded_bands_hz: [[<lo>, <hi>], ...]  # e.g. alpha band
    peak_handling: one_of [knee, fixed, auto]
  cross_check_aperiodic:
    tool: the_one_not_used_as_primary
    disagreement_threshold: 0.1   # |specparam - irasa| > 0.1 → manual review
  avalanche_fit:
    enabled: <true|false>
    framework: CSN_2009
    x_min_method: KS_minimising
    goodness_of_fit_ks_p_threshold: 0.1
    likelihood_ratio_alternatives:
      - lognormal
      - exponential
      - stretched_exponential
      - truncated_power_law
  robust_regression:
    enabled: <true|false>
    method: theil_sen
    bootstrap_n: 500
    ci_level: 0.95
  secondary_crosscheck:
    dfa_enabled: <true|false>
    mfdfa_enabled: <true|false>
  uncertainty:
    bootstrap_n: 2000
    block_bootstrap: circular_mbb
    seed: 42

# -------------------------------------------------------------------
# Section 5 — Null models
# -------------------------------------------------------------------
# All five required families per docs/NULL_MODEL_HIERARCHY.md §2.
# Latent-variable surrogate is the primary threat model. Skipping any
# family without a §2.3-style applicability justification is a §XIII
# failure.

null_models:
  shuffled:
    enabled: true
    n_surrogates: 1000
  iaaft:
    enabled: true
    n_surrogates: 1000
    implementation: mlcs/iaaft
  ornstein_uhlenbeck:
    enabled: true  # or AR(1)-matched for non-neural substrates
    n_surrogates: 1000
    tau_ms: <matched to empirical autocorrelation decay>
    sigma: <matched to empirical variance>
  poisson:
    enabled: <true|false>  # true if substrate is point-process
    n_surrogates: 1000
    rate_matching: one_of [homogeneous, inhomogeneous_slow_envelope]
  latent_variable:
    enabled: true   # primary threat model — always required
    n_surrogates: 1000
    model: one_of [hmm, gaussian_process_state_space, linear_dynamical_system]
    latent_dim: <integer>
    reference_code: https://github.com/ajsederberg/avalanche

  significance_threshold:
    z_score_cutoff: 3.0
    ci_level: 0.95

# -------------------------------------------------------------------
# Section 6 — Statistical analysis
# -------------------------------------------------------------------

statistics:
  primary_test: <name, e.g. "z-score of γ_real vs null-family means">
  alpha_two_sided: 0.01
  multiple_comparisons_control: one_of [bonferroni, holm, none_justified]
  heterogeneity_reporting: I_squared_and_tau_squared
  sample_size_at_analysis_time: <confirm matches section 2>

# -------------------------------------------------------------------
# Section 7 — Primary predictions
# -------------------------------------------------------------------

predictions:
  H1_primary: >-
    What γ value / range is expected under the substrate's
    hypothesized critical regime?
  H0_null: >-
    Under the null, γ distribution is <shape>.
  H2_alternative: >-
    If the latent-variable or topology-controlled null reproduces γ,
    what is the fallback interpretation?
  exit_on_falsification: >-
    If any null family passes per §6 of NULL_MODEL_HIERARCHY.md,
    what downgrade is mandated?

# -------------------------------------------------------------------
# Section 8 — Controls
# -------------------------------------------------------------------

controls:
  surrogate_families: [shuffled, iaaft, ou, poisson, latent_variable]
  perturbation_set:
    - <substrate-specific perturbation 1>
    - <substrate-specific perturbation 2>
  counter_models:
    - <feedforward / linear_oscillator / decoupled / non_adaptive>
  cross_level_checks:
    - coarse_graining
    - channel_shuffle
    - alternate_preprocessing
  topology_control:
    required: <true|false>  # true per Zeraati 2024 critique for graph substrates
    method: <e.g. degree-preserving edge permutation>

# -------------------------------------------------------------------
# Section 9 — Replication plan
# -------------------------------------------------------------------

replication_plan:
  within_lab: <integer n>
  cross_lab: one_of [<integer n>, not_planned_with_reason]
  external_rerun_committed: <true|false>
  external_rerun_target_labs:
    - <lab or contact>

# -------------------------------------------------------------------
# Section 10 — Interpretation boundary (MANDATORY)
# -------------------------------------------------------------------
# Per CLAIM_BOUNDARY.md §2 and §4. Without this section the prereg
# is incomplete and the claim cannot rise above `hypothesized`.

interpretation_boundary: >-
  Explicit sentence stating what this measurement does NOT license
  even if it succeeds. MUST be concrete. Examples:
  "Does not license a claim about cognition, intelligence, or
  consciousness."
  "Does not license generalisation beyond the preparation class
  under test."
  "Does not license any productivity or task-performance claim
  unless P_status == defined per evidence/levin_bridge/hypotheses.yaml."
  "Does not license cross-substrate inference without equivalent
  measurements on ≥2 other substrate classes per
  CLAIM_BOUNDARY.md §3.2."

# -------------------------------------------------------------------
# Section 11 — P_status (Levin-bridge compatibility)
# -------------------------------------------------------------------

p_status: one_of [defined, not_defined, preregistered_pending]
p_rationale: >-
  If not_defined, cite evidence/levin_bridge/hypotheses.yaml pattern.
  If defined, specify the substrate-native productivity metric.

# -------------------------------------------------------------------
# Section 12 — Theory revision rules
# -------------------------------------------------------------------

revision_rules:
  narrowing_to_bounded_regime: >-
    Under what data pattern do we narrow the γ≈1.0 claim to a
    bounded-regime law? (Per γ-program Phase IX §Step 34.)
  falsification: >-
    Under what data pattern do we downgrade claim_status to
    falsified per CLAIM_BOUNDARY.md §5.3 and
    NULL_MODEL_HIERARCHY.md §6?
  theory_retention: >-
    Under what data pattern does the claim stand unchanged?

# -------------------------------------------------------------------
# Section 13 — Provenance
# -------------------------------------------------------------------

provenance:
  adapter_code_sha: <40-hex or UNSTAMPED:...>
  data_sha256: <frozen at prereg filing>
  pipeline_runner: <tools/... path>
  analysis_notebook: <path or Zenodo DOI if generated>
  results_table: <path>
  author: <ORCID>
  author_affiliation: <institution>
  coauthors:
    - <ORCID>
  filing_commit_message: >-
    One sentence stating what this prereg locks down.

# -------------------------------------------------------------------
# Section 14 — Exit criteria
# -------------------------------------------------------------------

exit_criteria:
  success_conditions:
    - γ_real survives all five null families at |z|≥3.
    - Bootstrap CI95 of γ_real is outside every surrogate CI95.
    - Method-disagreement (specparam vs irasa) |Δ|<0.1.
    - Secondary cross-check (DFA) consistent within reported bounds.
    - External rerun reproduces γ within preregistered ε.
  failure_conditions:
    - Any null family passes → claim_status → falsified.
    - Method disagreement |Δ|≥0.1 → manual review → potential downgrade.
    - External rerun fails to reproduce → downgrade per
      CLAIM_BOUNDARY.md §5.3.
  theory_revision_conditions:
    - Two simultaneous null-family passes on unrelated substrates →
      narrow to bounded-regime law (γ-program §Step 34).
    - Topology-dependent exponents observed across substrates →
      narrow claim_scope to topology-matched pairs.
```

---

## Prereg filing checklist

Before uploading this prereg to OSF:

- [ ] Every `<...>` placeholder is replaced with a concrete value.
- [ ] No `TODO`, `TBD`, `???` tokens remain.
- [ ] All five null families are `enabled: true` unless a §2.3 applicability rationale is supplied.
- [ ] `interpretation_boundary` is non-empty and names a concrete claim the measurement does NOT license.
- [ ] `commit_sha_at_filing` matches the actual repository HEAD SHA.
- [ ] `data_sha256` matches the downloaded or archived data bundle.
- [ ] The substrate's entry in `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml` is consistent with this prereg's K/C/signal/method fields.

Inconsistency between the prereg and the substrate table is a
constitution §IV.A failure mode and must be resolved before filing.

## Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial template. 14 required sections; latent-variable surrogate required; interpretation_boundary mandatory. |

---

**claim_status:** measured (about the template itself; individual prereg filings derived from this template inherit this status only after OSF posting).
**effective:** 2026-04-14
