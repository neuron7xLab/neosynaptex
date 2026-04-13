# Levin → Neosynaptex Integration Protocol

**Status.** Canonical. Falsification-first; no claim may be promoted to the Neosynaptex canon on the basis of this document unless the criteria in Step 9 are met and `LEVIN_BRIDGE_VERDICT.md` records the outcome with supporting evidence commits.

**Purpose.** Use Levin's framework as a **bounded biological precedent**, not as a borrowed conclusion. TAME gives a legitimate language for agency across unconventional substrates; the cognitive light cone gives a concrete concept of scale-dependent goal-directedness; Anthrobots and Xenobot transcriptomics show that collective behavior and altered functional state can emerge without a central controller or genomic rewriting. None of that proves anything about LLM agents or software systems by itself. It only justifies **one** falsifiable bridge.

## Canonical bridge hypothesis

Systems with a **wider effective integration horizon** and **stronger distributed coordination** will, when still productive and non-collapsed, exhibit **γ closer to 1.0** more often than matched systems with narrower coordination horizons.

This is the only clean Levin-linked claim Neosynaptex tests. Broader Levin literature supports studying scale, coordination, and multi-level agency, but does not itself establish any law for software or LLM systems.

## Forbidden claim

Do **not** claim that γ ≈ 1 defines intelligence, proves cognition, or validates universal agency. At this stage γ is only a **candidate cross-substrate regime marker**. Any manuscript, README, or release note that overstates this MUST be rejected at review.

---

## Step 1 — Measurable objects

For every substrate, measure four quantities:

| Symbol | Name | Definition |
|---|---|---|
| **H** | Integration horizon proxy | Effective spatiotemporal extent over which a perturbation can influence coordinated system behaviour. |
| **C** | Coordination strength | Substrate-appropriate metric: phase locking, synchrony, graph coherence, mutual predictability, or stable inter-agent coupling. |
| **γ** | Metastability signature | Existing Neosynaptex estimator from organisational cost vs topological/functional complexity (`core/gamma.py`, Theil–Sen; see `docs/science/MECHANISMS.md §1`). |
| **P** | Productivity | Task-level output metric proving the system is functionally doing something, not merely complex. |

## Step 2 — Substrates

Use only substrates already legible inside Neosynaptex:

- **BN-Syn** (or another spiking substrate)
- **MFN+** / reaction-diffusion / morphogenetic substrate
- **Kuramoto** / market-synchronisation substrate
- **LLM multi-agent system**
- *(optional)* biological datasets already in the stack (EEG, Fantasia, etc.)

Minimum standard: **≥ 4 substrate classes**, each with **3 controllable regimes**.

## Step 3 — Three regimes per substrate

For each substrate, engineer three horizon regimes:

1. **Compressed** — short memory, weak coupling, narrow communication, local-only influence.
2. **Intermediate**.
3. **Expanded** — longer memory, wider coupling radius, richer recurrence, broader message propagation.

The intervention MUST specifically change **integration horizon**, not arbitrarily rewrite the whole system. Document the exact knob per substrate in `evidence/levin_bridge/horizon_knobs.md` before any measurement run.

## Step 4 — Keep productivity anchored

Within each substrate, hold the task family fixed while changing the horizon regime. Examples:

- **BN-Syn** — same discrimination/control task.
- **MFN+** — same pattern-completion or adaptive-stabilisation task.
- **LLM agents** — same multi-step planning / repair / audit task.
- **Kuramoto** — same event-detection or regime-classification target.

Without this, γ may track task change instead of integration scale.

## Step 5 — Pre-registered predictions

| ID | Statement |
|---|---|
| **H1** | Higher H and stronger C predict γ moving toward 1.0 while P remains viable. |
| **H0** | No consistent relation survives null controls. |
| **H2** | Expanded H increases complexity but degrades function, producing drift or collapse rather than γ ≈ 1 stabilisation. |
| **Kill** | If γ approaches 1.0 equally often in shuffled, scrambled, or non-productive controls, the bridge fails. |

Machine-readable form: `evidence/levin_bridge/hypotheses.yaml`.

## Step 6 — Adversarial controls

For each substrate, generate at least four controls:

1. **Shuffle control** — destroy temporal or graph structure.
2. **Matched-noise control** — preserve variance/energy but remove organisation.
3. **Overcoupled-collapse control** — too much synchrony, low adaptability.
4. **Undercoupled-fragmentation control** — too little synchrony, no integration.

Machine-readable form: `evidence/levin_bridge/controls.yaml`.

## Step 7 — Honest horizon estimation

No hand-wavy "more context" language. Operational H per substrate:

- **BN-Syn** — effective temporal memory depth, controllable recurrence span, coupling reach.
- **MFN+** — diffusion / coupling radius, persistence window of perturbation effects.
- **Kuramoto** — synchronisation influence span, lagged coordination radius.
- **LLM agents** — maximum decision-relevant memory span, communication graph depth, number of steps over which information remains causally active.

Normalise H into a comparable rank scale across substrates. Record both raw and rank-normalised values in `evidence/levin_bridge/cross_substrate_horizon_metrics.csv`.

## Step 8 — Main analysis

For every run, record one v2 row per
`evidence/levin_bridge/cross_substrate_horizon_metrics.csv`. The CSV contract
is split (see `evidence/levin_bridge/hypotheses.yaml`):

- **Required, cross-substrate comparable:** `H_raw`, `H_rank`, `C`, `gamma`,
  `gamma_ci_lo`, `gamma_ci_hi`.
- **Optional, substrate-specific:** `P`. Always paired with an explicit
  `P_status` ∈ {`defined`, `not_defined`, `preregistered_pending`}. A row
  with `P_status != "defined"` is valid for regime diagnostics and MUST be
  excluded from every productivity-gated claim.

Primary analyses:

- Monotonic relation between H and |γ − 1|.
- Partial relation between H and γ controlling for P **where `P_status == "defined"`**.
- Relation between C and γ.
- Interaction term: `H × C → γ`.
- Robustness under perturbation and ablation.

Minimum statistics:

- Bootstrap confidence intervals (≥ 500 resamples).
- Permutation tests.
- Rank correlation (Spearman).
- Substrate-wise analysis first, pooled meta-analysis second.

## Step 9 — Cross-substrate falsification

A result is only interesting if it survives heterogeneity.

**Supportive outcome** requires **all** of:

- Same directional pattern in **most** substrate classes.
- Null controls do **not** reproduce the effect.
- Productive regimes cluster nearer γ ≈ 1 than both fragmented **and** collapsed controls.
- At least **one** substrate in which the effect was not built into the estimator.

**Failed outcome** is **any** of:

- Effect appears only in one substrate family.
- Effect disappears under matched controls.
- γ ≈ 1 tracks scale inflation but not productivity.
- γ ≈ 1 occurs equally in pathological overcoupling and successful coordination.

The "γ ≈ 1 tracks scale inflation but not productivity" criterion can only
be evaluated on substrates whose rows carry `P_status == "defined"`. For
substrates still in `not_defined` or `preregistered_pending`, that branch
is deferred until a preregistered P contract lands.

## Step 10 — Canonical interpretation rule

If the protocol **succeeds**, the strongest allowed claim is:

> Broader integration horizons and stronger distributed coordination are associated with γ values closer to 1.0 across multiple productive substrates, making γ a stronger candidate marker of metastable regime organisation.

If the protocol **fails**, the canonical statement is:

> Levin-inspired scale and coordination concepts remain biologically meaningful, but they do not currently support γ ≈ 1 as a robust cross-substrate marker in Neosynaptex.

No language stronger than the above is permitted in downstream manuscripts unless replicated independently and recorded in `evidence/levin_bridge/replications/`.

## Step 11 — Required artefacts

The protocol is not complete until the following exist and are committed:

1. `docs/protocols/levin_bridge_protocol.md` — this file.
2. `evidence/levin_bridge/hypotheses.yaml`
3. `evidence/levin_bridge/controls.yaml`
4. `evidence/levin_bridge/cross_substrate_horizon_metrics.csv`
5. `notebooks/levin_bridge/gamma_vs_horizon_analysis.ipynb` — generated at run time; not required at scaffold commit.
6. `evidence/levin_bridge/LEVIN_BRIDGE_VERDICT.md` — written only after Step 9 evaluation; not required at scaffold commit.

## Step 12 — Canonical manuscript sentence

Use this exact framing unless stronger evidence exists:

> Levin's work provides a biologically grounded framework for distributed agency and scale-dependent goal-directedness; in Neosynaptex, we operationalise this not as a conclusion about machine intelligence, but as a falsifiable cross-substrate hypothesis linking integration horizon and coordinated dynamics to metastable regime signatures.

---

## Bottom line

Translate cognitive light cone → integration horizon, manipulate it, measure γ, attack the bridge with controls, and keep only what survives.

## Reference

Levin, M. *Technological Approach to Mind Everywhere (TAME): an experimentally-grounded framework for understanding diverse bodies and minds.* arXiv:2201.10346.
